import requests
import json
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
            # Create simple message card
            card_content = {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                "body": [
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
            
            # Send to Teams
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code in {200, 202}:  # Teams webhooks can return either 200 or 202
                logger.info(f"Successfully sent Teams text message")
                return True
            else:
                error_text = response.text if response.text else f"Status code: {response.status_code}"
                logger.error(f"Failed to send Teams text message: {error_text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Teams text message: {e}")
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
            # Create message payload
            payload = self._create_payload(filing)
            
            # Send to Teams
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code in {200, 202}:  # Teams webhooks can return either 200 or 202
                logger.info(f"Successfully sent Teams notification for {filing.company_name}")
                return True
            else:
                error_text = response.text if response.text else f"Status code: {response.status_code}"
                logger.error(f"Failed to send Teams notification: {error_text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Teams notification: {e}")
            return False
    
    def _create_payload(self, filing: Filing) -> Dict[str, Any]:
        """
        Create Teams message payload with adaptive card.
        
        Args:
            filing: Filing object
            
        Returns:
            Teams message payload dict
        """
        # Create ticker display with link if available
        ticker_part = ""
        if filing.ticker_symbol:
            ticker_url = f"https://www.google.com/finance/quote/{filing.ticker_symbol}"
            ticker_part = f"(Ticker: [{filing.ticker_symbol}]({ticker_url}))"
        
        # Create context text if available
        context_section = []
        if filing.contexts and filing.contexts[0]:
            # Use just the first context to keep the card simple
            context = filing.contexts[0][:500]  # Limit to 500 chars
            context_section = [
                {
                    "type": "TextBlock",
                    "text": "**Context:**",
                    "wrap": True,
                    "weight": "Bolder" 
                },
                {
                    "type": "TextBlock",
                    "text": context,
                    "wrap": True
                }
            ]
            
        # Create matching terms section if available
        terms_section = []
        if filing.matching_terms:
            terms_text = ", ".join(filing.matching_terms)
            terms_section = [
                {
                    "type": "TextBlock",
                    "text": "**Matching Terms:**",
                    "wrap": True,
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": terms_text,
                    "wrap": True
                }
            ]
            
        # Create card content
        card_content = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.2",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Cybersecurity Incident Disclosure",
                    "weight": "Bolder",
                    "size": "Large"
                },
                {
                    "type": "TextBlock",
                    "text": f"**Published on:** {filing.filing_date}",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": f"**Company:** {filing.company_name} {ticker_part}",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": f"**CIK:** [{filing.cik}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={filing.cik})",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": f"**Form Type:** {filing.form_type}",
                    "wrap": True
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View SEC Filing",
                    "url": filing.filing_url
                }
            ]
        }
        
        # Add context and terms sections if available
        if context_section:
            card_content["body"].extend(context_section)
            
        if terms_section:
            card_content["body"].extend(terms_section)
            
        # Add to payload
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
        
        return payload 