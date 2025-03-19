import tweepy
from tweepy import errors as tweepy_errors
import pytz
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.models.filing import Filing
from src.notifiers.notification_service import NotificationChannel
from src.config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_BEARER_TOKEN, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TwitterNotifier(NotificationChannel):
    """
    Notification channel for Twitter (X) using the Twitter API.
    """
    
    def __init__(self, 
                api_key: Optional[str] = None,
                api_secret: Optional[str] = None,
                bearer_token: Optional[str] = None,
                access_token: Optional[str] = None,
                access_token_secret: Optional[str] = None):
        """
        Initialize Twitter notifier.
        
        Args:
            api_key: Twitter API key (default: from config)
            api_secret: Twitter API secret (default: from config)
            bearer_token: Twitter bearer token (default: from config)
            access_token: Twitter access token (default: from config)
            access_token_secret: Twitter access token secret (default: from config)
        """
        self.api_key = api_key or TWITTER_API_KEY
        self.api_secret = api_secret or TWITTER_API_SECRET
        self.bearer_token = bearer_token or TWITTER_BEARER_TOKEN
        self.access_token = access_token or TWITTER_ACCESS_TOKEN
        self.access_token_secret = access_token_secret or TWITTER_ACCESS_TOKEN_SECRET
        
        # Initialize API clients
        self.client = None
        self.api = None
        self._initialize_clients()
        
        # Bio update throttling
        self.last_bio_update = None
        self.min_bio_update_interval = 15  # minutes
    
    def _initialize_clients(self):
        """Initialize Twitter API clients."""
        if not self.is_configured():
            logger.warning("Twitter credentials not fully configured")
            return
            
        try:
            # Initialize Tweepy Client for posting tweets (API v2)
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True  # Auto-wait when rate limited
            )
            
            # Initialize Tweepy API v1.1 for updating profile bio
            # Profile updates require v1.1 API
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Test API connection
            try:
                user = self.api.verify_credentials()
                logger.info(f"Twitter API initialized successfully for user @{user.screen_name}")
            except Exception as e:
                logger.error(f"Twitter API credentials verification failed: {e}")
                # Continue initialization despite verification failure
            
            logger.info("Twitter API clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API clients: {e}")
            self.client = None
            self.api = None
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return "twitter"
        
    def is_configured(self) -> bool:
        """Check if Twitter credentials are configured."""
        return all([
            self.api_key,
            self.api_secret,
            self.bearer_token,
            self.access_token,
            self.access_token_secret
        ])
    
    def send_text_message(self, message: str) -> bool:
        """
        Send a simple text message to Twitter.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.is_configured() or not self.client:
            logger.warning("Twitter client not configured or initialized")
            return False
            
        try:
            # Twitter has a 280 character limit
            if len(message) > 280:
                # Truncate and add ellipsis
                message = message[:277] + "..."
                
            # Post tweet
            response = self.client.create_tweet(text=message)
            
            if response.data:
                tweet_id = response.data.get('id')
                logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                return True
            else:
                logger.error(f"Failed to post tweet. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
        
    def notify(self, filing: Filing) -> bool:
        """
        Send a Twitter notification for a filing.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured() or not self.client:
            logger.warning("Twitter client not configured or initialized")
            return False
            
        try:
            # Create tweet text
            tweet_text = self._create_tweet(filing)
            
            # Post tweet
            response = self.client.create_tweet(text=tweet_text)
            
            if response.data:
                tweet_id = response.data.get('id')
                logger.info(f"Successfully posted tweet for {filing.company_name} with ID: {tweet_id}")
                return True
            else:
                logger.error(f"Failed to post tweet for {filing.company_name}. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting tweet for {filing.company_name}: {e}")
            return False
    
    def update_profile_bio(self, last_check_time=None, additional_info=None):
        """
        Update Twitter profile bio with last check time.
        
        Args:
            last_check_time: Time of last check (default: current time)
            additional_info: Additional information to include in bio (e.g., SEC status)
        
        Returns:
            bool: True if bio was updated successfully, False otherwise
        """
        if not self.api:
            logger.warning("Twitter API not initialized")
            return False
            
        try:
            # Get current time if not provided
            current_time = datetime.utcnow()
            if last_check_time is None:
                last_check_time = current_time
                
            # Check if this is a status change message (bypass throttle for these)
            is_status_change = False
            if additional_info and ("SEC is OPEN" in additional_info or "SEC is CLOSED" in additional_info):
                # For status changes, we always want to update the bio
                is_status_change = True
                logger.info("SEC status change detected - bypassing update throttle")
                
            # Check if we should throttle updates for non-status changes
            if not is_status_change and self.last_bio_update:
                time_since_last_update = (current_time - self.last_bio_update).total_seconds() / 60.0
                if time_since_last_update < self.min_bio_update_interval:
                    logger.info(f"Skipping Twitter bio update - last update was {time_since_last_update:.1f} minutes ago (minimum interval: {self.min_bio_update_interval} minutes)")
                    return True  # Return True to avoid triggering error messages
                
            # Format time in Eastern timezone
            eastern = pytz.timezone('US/Eastern')
            last_check_time_et = last_check_time.astimezone(eastern) if hasattr(last_check_time, 'astimezone') else eastern.localize(last_check_time)
            time_str = last_check_time_et.strftime('%Y-%m-%d %H:%M ET')
            
            # Extract SEC status if available
            status_text = "UNKNOWN"
            is_sec_open = True  # Default to open
            if additional_info:
                if "SEC is OPEN" in additional_info:
                    status_text = "OPEN"
                    is_sec_open = True
                elif "SEC is CLOSED" in additional_info:
                    status_text = "CLOSED"
                    is_sec_open = False
            
            # Calculate next review time if SEC is closed
            if not is_sec_open:
                # Calculate next business day at 9:00 AM
                next_review_time = last_check_time_et
                
                # Start with next day at 9:00 AM
                next_day = (next_review_time + timedelta(days=1)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                )
                
                # If it's already after 9 AM, use today at 9 AM
                if next_review_time.hour < 9 and next_review_time.weekday() < 5:  # Weekday before 9 AM
                    next_day = next_review_time.replace(hour=9, minute=0, second=0, microsecond=0)
                    
                # If it's weekend, find next Monday
                while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                    next_day += timedelta(days=1)
                
                next_time_str = next_day.strftime('%Y-%m-%d %H:%M ET')
                time_display = f"Next review: {next_time_str}"
            else:
                time_display = f"Last review: {time_str}"
            
            # Create bio text with SEC status and appropriate timestamp
            bio_message = (
                f"I monitor the SEC's RSS feed for 8-K filings disclosing cybersecurity incidents.\n\n"
                f"SEC is {status_text} - {time_display}"
            )
            
            # Ensure it doesn't exceed Twitter's 160-character limit
            if len(bio_message) > 160:
                # Shorten the base message if needed
                base_message = "SEC 8-K cybersecurity incident monitor."
                bio_message = (
                    f"{base_message}\n\n"
                    f"SEC is {status_text} - {time_display}"
                )
                
                # If still too long, truncate
                if len(bio_message) > 160:
                    bio_message = bio_message[:157] + "..."
            
            # Log attempt with timestamp and character count
            logger.info(f"Updating Twitter bio with {time_display} ({len(bio_message)} chars)")
            
            # First verify current bio
            try:
                current_user = self.api.verify_credentials()
                current_bio = current_user.description
                logger.info(f"Current Twitter bio ({len(current_bio)} chars): {current_bio}")
            except Exception as e:
                logger.error(f"Failed to get current Twitter bio: {e}")
                
            # Update profile with proper error handling
            response = self.api.update_profile(description=bio_message)
            
            # Validate that update was successful
            if response and hasattr(response, 'description') and response.description == bio_message:
                logger.info(f"Twitter bio updated successfully to: {response.description}")
                # Record successful update time
                self.last_bio_update = current_time
                return True
            else:
                logger.error(f"Twitter bio may not have updated correctly: {response}")
                return False
                
        except tweepy_errors.TweepyException as te:
            logger.error(f"Twitter API error updating bio: {te}")
            # Add more detailed error info
            if hasattr(te, 'api_codes'):
                logger.error(f"Twitter API error codes: {te.api_codes}")
            if hasattr(te, 'response') and hasattr(te.response, 'text'):
                logger.error(f"Twitter API response: {te.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error updating Twitter bio: {e}")
            return False
    
    def _create_tweet(self, filing: Filing) -> str:
        """
        Create tweet text for a filing.
        
        Args:
            filing: Filing object
            
        Returns:
            Formatted tweet text
        """
        # Create ticker display if available
        ticker_part = f" ${filing.ticker_symbol}" if filing.ticker_symbol else ""
        
        # Base tweet format
        base_tweet = (
            f"{filing.filing_date}\n"
            f"A cybersecurity incident has been disclosed by {filing.company_name}{ticker_part} "
            f"(CIK: {filing.cik})\n\n"
            f"View SEC Filing: {filing.filing_url}"
        )
        
        # Check if base tweet is within character limit
        if len(base_tweet) <= 280:
            return base_tweet
            
        # If too long, truncate company name
        if len(filing.company_name) > 30:
            company_display = filing.company_name[:27] + "..."
        else:
            company_display = filing.company_name
            
        # Alternative shorter format
        shorter_tweet = (
            f"{filing.filing_date}\n"
            f"Cybersecurity incident disclosed by {company_display}{ticker_part} "
            f"(CIK: {filing.cik})\n\n"
            f"{filing.filing_url}"
        )
        
        # If still too long, remove date
        if len(shorter_tweet) > 280:
            shortest_tweet = (
                f"Cybersecurity incident disclosed by {company_display}{ticker_part} "
                f"(CIK: {filing.cik})\n\n"
                f"{filing.filing_url}"
            )
            return shortest_tweet
            
        return shorter_tweet 