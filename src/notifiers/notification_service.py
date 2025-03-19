import importlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from src.models.filing import Filing
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    def notify(self, filing: Filing) -> bool:
        """
        Send a notification for a filing.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def send_text_message(self, message: str) -> bool:
        """
        Send a simple text message.
        
        This is used for status notifications and other simple messages
        that don't involve a filing.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if this notification channel is properly configured.
        
        Returns:
            bool: True if configured, False otherwise
        """
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of this notification channel.
        
        Returns:
            str: Name of the channel
        """
        pass


class NotificationService:
    """
    Service for managing and sending notifications through multiple channels.
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self.channels: Dict[str, NotificationChannel] = {}
        
    def register_channel(self, channel: NotificationChannel):
        """
        Register a notification channel.
        
        Args:
            channel: NotificationChannel instance to register
        """
        if channel.is_configured():
            self.channels[channel.name] = channel
            logger.info(f"Registered notification channel: {channel.name}")
        else:
            logger.warning(f"Skipping unconfigured notification channel: {channel.name}")
            
    def unregister_channel(self, channel_name: str):
        """
        Unregister a notification channel.
        
        Args:
            channel_name: Name of channel to unregister
        """
        if channel_name in self.channels:
            del self.channels[channel_name]
            logger.info(f"Unregistered notification channel: {channel_name}")
            
    def notify_all(self, filing: Filing) -> Dict[str, bool]:
        """
        Send notification through all registered channels.
        
        Args:
            filing: Filing object to notify about
            
        Returns:
            Dict mapping channel names to success status
        """
        results = {}
        
        for name, channel in self.channels.items():
            try:
                logger.info(f"Sending notification via {name}: {filing.company_name}")
                success = channel.notify(filing)
                results[name] = success
                
                if success:
                    logger.info(f"Successfully sent notification via {name}")
                else:
                    logger.error(f"Failed to send notification via {name}")
                    
            except Exception as e:
                logger.error(f"Error sending notification via {name}: {e}")
                results[name] = False
                
        return results
    
    def send_text_message_to_all(self, message: str) -> Dict[str, bool]:
        """
        Send a text message through all registered channels.
        
        Args:
            message: Text message to send
            
        Returns:
            Dict mapping channel names to success status
        """
        results = {}
        
        for name, channel in self.channels.items():
            try:
                logger.info(f"Sending text message via {name}")
                success = channel.send_text_message(message)
                results[name] = success
                
                if success:
                    logger.info(f"Successfully sent text message via {name}")
                else:
                    logger.error(f"Failed to send text message via {name}")
                    
            except Exception as e:
                logger.error(f"Error sending text message via {name}: {e}")
                results[name] = False
                
        return results
        
    @property
    def active_channels(self) -> List[str]:
        """Get list of active notification channel names."""
        return list(self.channels.keys())


# Factory function to create and configure the notification service
def create_notification_service() -> NotificationService:
    """
    Create and configure a notification service with all available channels.
    
    Returns:
        Configured NotificationService instance
    """
    service = NotificationService()
    
    # Try to import and register each channel
    channels = [
        ('slack', 'SlackNotifier'),
        ('teams', 'TeamsNotifier'),
        ('telegram', 'TelegramNotifier'),
        ('twitter', 'TwitterNotifier')
    ]
    
    for module_name, class_name in channels:
        try:
            # Dynamically import the module
            module = importlib.import_module(f"src.notifiers.{module_name}_notifier")
            
            # Get the notifier class
            notifier_class = getattr(module, class_name)
            
            # Create an instance and register it
            notifier = notifier_class()
            
            if notifier.is_configured():
                service.register_channel(notifier)
                
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not load notification channel {module_name}: {e}")
            
    # Log active channels
    if service.active_channels:
        logger.info(f"Active notification channels: {', '.join(service.active_channels)}")
    else:
        logger.warning("No notification channels available")
        
    return service 