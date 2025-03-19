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
        # Create ticker display with link if available
        ticker_display = ""
        if filing.ticker_symbol:
            ticker_url = f"https://www.google.com/finance/quote/{filing.ticker_symbol}"
            ticker_display = f" (Ticker: <{ticker_url}|${filing.ticker_symbol}>)"
            
        # Format context if available
        context_blocks = []
        if filing.contexts:
            context_text = "...\n".join(filing.contexts[:3])  # Limit to first 3 contexts
            if context_text:
                context_blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Context:*\n```{context_text[:1000]}```"  # Limit length
                        }
                    }
                ]
                
        # Create message blocks
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
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Company:*\n{filing.company_name}{ticker_display}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*CIK:*\n{filing.cik}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Published on:*\n{filing.filing_date}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Form Type:*\n{filing.form_type}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*View SEC Filing:*\n<{filing.filing_url}|SEC.gov Link>"
                }
            }
        ]
        
        # Add context blocks if available
        if context_blocks:
            blocks.extend(context_blocks)
            
        # Add matching terms if available
        if filing.matching_terms:
            terms_text = ", ".join(filing.matching_terms)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Matching Terms:*\n{terms_text}"
                }
            })
            
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Reported by SECurityTr8Ker"
                }
            ]
        })
        
        return {
            "blocks": blocks,
            # Fallback text for notifications
            "text": f"Cybersecurity Incident Disclosure: {filing.company_name} ({filing.form_type}) - {filing.filing_date}"
        } 