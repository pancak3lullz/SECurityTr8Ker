import requests
import json
import traceback
from typing import Optional, Dict, Any
from src.models.filing import Filing
from src.notifiers.notification_service import NotificationChannel
from src.config import TEAMS_WEBHOOK_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TeamsNotifier(NotificationChannel):
    """
    Notification channel for Microsoft Teams using incoming webhooks.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Teams notifier.
        
        Args:
            webhook_url: Teams webhook URL (default: from config)
        """
        self.webhook_url = webhook_url or TEAMS_WEBHOOK_URL
        logger.info(f"Teams notifier initialized with webhook URL: {'configured' if self.webhook_url else 'not configured'}")
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return "teams"
        
    def is_configured(self) -> bool:
        """Check if Teams webhook URL is configured."""
        return bool(self.webhook_url)
    
    def send_text_message(self, message: str) -> bool:
        """
        Send a simple text message to Teams.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Teams webhook URL not configured")
            return False
            
        try:
            # Create card similar to the one from teams_poster.py that's known to work
            card_content = {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Message from SECurityTr8Ker",
                        "weight": "Bolder",
                        "size": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": message,
                        "wrap": True
                    }
                ]
            }
            
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": card_content
                    }
                ]
            }
            
            # Send to Teams - using exact same headers and request structure as teams_poster.py
            headers = {'Content-Type': 'application/json'}
            logger.debug(f"Sending message to Teams webhook")
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            
            # Detailed response logging
            logger.debug(f"Teams API response status: {response.status_code}")
            logger.debug(f"Teams API response headers: {response.headers}")
            logger.debug(f"Teams API response body: {response.text[:200]}...")
            
            # Check response
            if response.status_code in {200, 202}:  # Teams webhooks can return either 200 or 202
                logger.info(f"Successfully sent Teams text message")
                return True
            else:
                error_text = response.text if response.text else f"Status code: {response.status_code}"
                logger.error(f"Failed to send Teams text message: {error_text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending Teams message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Teams message: {e}")
            logger.error(traceback.format_exc())
            return False
        
    def notify(self, filing: Filing) -> bool:
        """
        Send a Teams notification for a filing.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Teams webhook URL not configured")
            return False
            
        try:
            # Create the same format that was working in teams_poster.py
            ticker_part = f"(Ticker: [${filing.ticker_symbol}](https://www.google.com/search?q=%24{filing.ticker_symbol}+ticker))" if filing.ticker_symbol else ""
            
            card_content = {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Cybersecurity Incident Disclosure",
                        "weight": "Bolder",
                        "size": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"{filing.filing_date}\\n\\nA cybersecurity incident has been disclosed by **{filing.company_name}** (CIK: [{filing.cik}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={filing.cik})) {ticker_part}.",
                        "wrap": True
                    },
                    {
                        "type": "ActionSet",
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "View SEC Filing",
                                "url": filing.filing_url
                            }
                        ]
                    }
                ]
            }

            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": card_content
                    }
                ]
            }
            
            # Use the exact same approach as teams_poster.py
            headers = {'Content-Type': 'application/json'}
            logger.debug(f"Sending notification for {filing.company_name} to Teams webhook")
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            
            # Detailed response logging
            logger.debug(f"Teams API notification response status: {response.status_code}")
            logger.debug(f"Teams API notification response headers: {response.headers}")
            logger.debug(f"Teams API notification response body: {response.text[:200]}...")
            
            # Check response
            if response.status_code in {200, 202}:  # Teams webhooks can return either 200 or 202
                logger.info(f"Successfully sent Teams notification for {filing.company_name}")
                return True
            else:
                error_text = response.text if response.text else f"Status code: {response.status_code}"
                logger.error(f"Failed to send Teams notification: {error_text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending Teams notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Teams notification: {e}")
            logger.error(traceback.format_exc())
            return False 
