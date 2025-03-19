import requests
from typing import Optional, Dict, Any
from src.models.filing import Filing
from src.notifiers.notification_service import NotificationChannel
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TelegramNotifier(NotificationChannel):
    """
    Notification channel for Telegram using the Telegram Bot API.
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token (default: from config)
            chat_id: Telegram chat ID (default: from config)
        """
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return "telegram"
        
    def is_configured(self) -> bool:
        """Check if Telegram credentials are configured."""
        return bool(self.bot_token and self.chat_id and self.api_url)
    
    def send_text_message(self, message: str) -> bool:
        """
        Send a simple text message to Telegram.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Telegram bot token or chat ID not configured")
            return False
            
        try:
            # Send to Telegram
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=payload)
            
            # Check response
            if response.status_code == 200:
                logger.info(f"Successfully sent Telegram text message")
                return True
            else:
                logger.error(f"Failed to send Telegram text message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram text message: {e}")
            return False
        
    def notify(self, filing: Filing) -> bool:
        """
        Send a Telegram notification for a filing.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Telegram bot token or chat ID not configured")
            return False
            
        try:
            # Create notification message
            message = self._create_message(filing)
            
            # Send to Telegram
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=payload)
            
            # Check response
            if response.status_code == 200:
                logger.info(f"Successfully sent Telegram notification for {filing.company_name}")
                return True
            else:
                logger.error(f"Failed to send Telegram notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def _create_message(self, filing: Filing) -> str:
        """
        Create Telegram message text.
        
        Args:
            filing: Filing object
            
        Returns:
            Formatted message text
        """
        # Create ticker part if available
        ticker_part = f", Ticker: [${filing.ticker_symbol}](https://www.google.com/search?q=%24{filing.ticker_symbol}+ticker)" if filing.ticker_symbol else ""
        
        # Create the base message
        message = f"*Cybersecurity Incident Disclosure*\n\n"
        message += f"Published on: {filing.filing_date}\n"
        message += f"Company: `{filing.company_name}`\n"
        message += f"CIK: [{filing.cik}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={filing.cik}){ticker_part}\n"
        message += f"Form Type: {filing.form_type}\n\n"
        message += f"[View SEC Filing]({filing.filing_url})"
        
        # Add matching terms if available
        if filing.matching_terms:
            terms = ", ".join(filing.matching_terms)
            message += f"\n\n*Matching Terms:* {terms}"
            
        # Add context if available (limited to first one due to Telegram message limits)
        if filing.contexts and filing.contexts[0]:
            # Limit context to 500 chars to avoid hitting Telegram message limits
            context = filing.contexts[0][:500]
            # Escape any markdown in the context
            context = context.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            message += f"\n\n*Context:*\n```\n{context}\n```"
            
        return message 