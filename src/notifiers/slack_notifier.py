import json
import requests
from typing import Optional, Dict, Any
from src.models.filing import Filing
from src.notifiers.notification_service import NotificationChannel
from src.config import SLACK_WEBHOOK_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SlackNotifier(NotificationChannel):
    """
    Notification channel for Slack using incoming webhooks.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL (default: from config)
        """
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return "slack"
        
    def is_configured(self) -> bool:
        """Check if Slack webhook URL is configured."""
        return bool(self.webhook_url)
    
    def send_text_message(self, message: str) -> bool:
        """
        Send a simple text message to Slack.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Slack webhook URL not configured")
            return False
            
        try:
            # Create simple payload with text
            payload = {
                "text": message,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    }
                ]
            }
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code == 200 and response.text == 'ok':
                logger.info(f"Successfully sent Slack text message")
                return True
            else:
                logger.error(f"Failed to send Slack text message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack text message: {e}")
            return False
        
    def notify(self, filing: Filing) -> bool:
        """
        Send a Slack notification for a filing.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Slack webhook URL not configured")
            return False
            
        try:
            # Create message payload
            payload = self._create_payload(filing)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code == 200 and response.text == 'ok':
                logger.info(f"Successfully sent Slack notification for {filing.company_name}")
                return True
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def _create_payload(self, filing: Filing) -> Dict[str, Any]:
        """
        Create Slack message payload.
        
        Args:
            filing: Filing object
            
        Returns:
            Slack message payload dict
        """
        # Create ticker part if available
        ticker_part = f"${filing.ticker_symbol}" if filing.ticker_symbol else ""
        
        # Create blocks for a simple message format
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Cybersecurity Incident Disclosure"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Published on: {filing.filing_date}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Company: {filing.company_name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"CIK: <https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={filing.cik}|{filing.cik}> (Ticker: <https://www.google.com/search?q=%24{filing.ticker_symbol}+ticker|{ticker_part}>)"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View SEC Filing"
                        },
                        "url": filing.filing_url
                    }
                ]
            }
        ]
        
        return {
            "blocks": blocks,
            # Fallback text for notifications
            "text": f"A cybersecurity incident has been disclosed by {filing.company_name} (CIK: {filing.cik}, Ticker: {ticker_part})"
        } 