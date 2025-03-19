from typing import Dict, Any, Optional
from src.notifiers.notification_service import NotificationService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class StatusNotifier:
    """
    Handles notifications about SEC operational status changes.
    """
    
    def __init__(self, notification_service: NotificationService):
        """
        Initialize the status notifier.
        
        Args:
            notification_service: NotificationService instance to use for sending notifications
        """
        self.notification_service = notification_service
    
    def notify_sec_open(self, status: Dict[str, Any]):
        """
        Send notification that the SEC is now open.
        
        Args:
            status: Dict with status information
        """
        logger.info("Sending notification: SEC is now open")
        
        # Create message for various channels
        message = f"🟢 The SEC is now OPEN\n\n"
        message += f"Hours: 9:00 AM to 5:30 PM Eastern Time\n"
        message += f"SECurityTr8Ker is now actively monitoring for new cybersecurity disclosures."
        
        # Send to all channels that support simple text messages
        for channel in self.notification_service.channels.values():
            try:
                if hasattr(channel, 'send_text_message'):
                    channel.send_text_message(message)
            except Exception as e:
                logger.error(f"Error sending SEC open notification to {channel.name}: {e}")
    
    def notify_sec_closed(self, status: Dict[str, Any]):
        """
        Send notification that the SEC is now closed.
        
        Args:
            status: Dict with status information
        """
        logger.info("Sending notification: SEC is now closed")
        
        # Format the next opening time
        next_open_str = "next business day at 9:00 AM ET"
        if "next_open" in status:
            try:
                # This assumes next_open is an ISO format datetime string
                next_open = status["message"]
            except Exception:
                # Fallback if parsing fails
                next_open = next_open_str
        else:
            next_open = next_open_str
            
        # Create message for various channels
        message = f"🔴 The SEC is now CLOSED\n\n"
        message += f"{next_open}\n"
        message += f"SECurityTr8Ker is pausing monitoring until the SEC reopens."
        
        # Send to all channels that support simple text messages
        for channel in self.notification_service.channels.values():
            try:
                if hasattr(channel, 'send_text_message'):
                    channel.send_text_message(message)
            except Exception as e:
                logger.error(f"Error sending SEC closed notification to {channel.name}: {e}")
                
    def send_current_status(self, status: Dict[str, Any]):
        """
        Send notification with current SEC status.
        
        Args:
            status: Dict with status information
        """
        is_open = status.get("is_open", False)
        
        if is_open:
            self.notify_sec_open(status)
        else:
            self.notify_sec_closed(status) 