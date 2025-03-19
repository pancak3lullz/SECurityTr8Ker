import time
import pytz
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SECScheduler:
    """
    Scheduler for managing application operations according to SEC business hours.
    
    The SEC typically operates Monday through Friday, 9:00 AM to 5:30 PM Eastern Time.
    This scheduler ensures the application only runs during these hours and
    handles notifications for SEC opening and closing.
    """
    
    # SEC business hours in Eastern Time
    TIMEZONE = pytz.timezone('US/Eastern')
    OPEN_HOUR = 9  # 9:00 AM ET
    CLOSE_HOUR = 17  # 5:30 PM ET (using 17 for cleaner hour checks)
    CLOSE_MINUTE = 30  # 30 minutes past CLOSE_HOUR
    
    # Days of the week (0 = Monday, 6 = Sunday)
    BUSINESS_DAYS = [0, 1, 2, 3, 4]  # Monday through Friday
    
    # Check interval in seconds for determining if it's business hours
    CHECK_INTERVAL = 600  # 10 minutes
    
    def __init__(self, 
                 operation_callback: Callable,
                 open_notification_callback: Optional[Callable] = None,
                 close_notification_callback: Optional[Callable] = None,
                 bio_update_callback: Optional[Callable] = None):
        """
        Initialize the scheduler.
        
        Args:
            operation_callback: Function to call during business hours
            open_notification_callback: Function to call when SEC opens
            close_notification_callback: Function to call when SEC closes
            bio_update_callback: Function to call to update Twitter bio
        """
        self.operation_callback = operation_callback
        self.open_notification_callback = open_notification_callback
        self.close_notification_callback = close_notification_callback
        self.bio_update_callback = bio_update_callback
        
        self.running = False
        self.was_business_hours = False  # Track previous state for open/close transitions
        
    def start(self):
        """Start the scheduling loop."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        logger.info("SEC scheduler starting")
        
        # Initial check
        self.was_business_hours = self.is_business_hours()
        
        try:
            self._scheduling_loop()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down scheduler...")
        except Exception as e:
            logger.error(f"Error in scheduling loop: {e}")
        finally:
            self.running = False
            logger.info("SEC scheduler shutdown complete")
            
    def stop(self):
        """Stop the scheduling loop."""
        self.running = False
        logger.info("SEC scheduler shutting down...")
        
    def is_business_hours(self) -> bool:
        """
        Check if the current time is within SEC business hours.
        
        Returns:
            bool: True if within business hours, False otherwise
        """
        now = datetime.now(self.TIMEZONE)
        
        # Check if it's a business day (Monday-Friday)
        if now.weekday() not in self.BUSINESS_DAYS:
            return False
            
        # Check if it's within business hours
        if now.hour < self.OPEN_HOUR:
            return False
            
        if now.hour > self.CLOSE_HOUR or (now.hour == self.CLOSE_HOUR and now.minute >= self.CLOSE_MINUTE):
            return False
            
        return True
    
    def get_next_business_hours(self) -> Dict[str, Any]:
        """
        Calculate when the next SEC business hours start.
        
        Returns:
            Dict with opening details
        """
        now = datetime.now(self.TIMEZONE)
        
        # If it's already business hours, return None
        if self.is_business_hours():
            return {
                "is_open": True,
                "message": "SEC is currently open",
                "now": now.isoformat()
            }
            
        # Start with today at opening time
        next_open = now.replace(hour=self.OPEN_HOUR, minute=0, second=0, microsecond=0)
        
        # If we're past closing time today, move to next day
        if now.hour >= self.CLOSE_HOUR:
            next_open = next_open + timedelta(days=1)
            
        # Keep adding days until we hit a business day
        while next_open.weekday() not in self.BUSINESS_DAYS:
            next_open = next_open + timedelta(days=1)
            
        seconds_until = (next_open - now).total_seconds()
        hours_until = seconds_until / 3600
        
        return {
            "is_open": False,
            "next_open": next_open.isoformat(),
            "seconds_until": seconds_until,
            "hours_until": hours_until,
            "message": f"SEC is closed. Opens in {hours_until:.1f} hours on {next_open.strftime('%A, %B %d at %I:%M %p %Z')}",
            "now": now.isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of SEC business hours.
        
        Returns:
            Dict with status details
        """
        now = datetime.now(self.TIMEZONE)
        is_business_hours = self.is_business_hours()
        
        if is_business_hours:
            close_time = now.replace(hour=self.CLOSE_HOUR, minute=self.CLOSE_MINUTE, second=0, microsecond=0)
            seconds_remaining = (close_time - now).total_seconds()
            hours_remaining = seconds_remaining / 3600
            
            return {
                "is_open": True,
                "close_time": close_time.isoformat(),
                "seconds_remaining": seconds_remaining,
                "hours_remaining": hours_remaining,
                "message": f"SEC is open. Closes in {hours_remaining:.1f} hours at {close_time.strftime('%I:%M %p %Z')}",
                "now": now.isoformat()
            }
        else:
            return self.get_next_business_hours()
    
    def _scheduling_loop(self):
        """Main scheduling loop."""
        while self.running:
            try:
                # Check if it's business hours
                is_business_hours = self.is_business_hours()
                
                # Detect transitions for notifications
                if is_business_hours and not self.was_business_hours:
                    # Transition: Closed -> Open
                    logger.info("SEC is now open")
                    
                    # Update Twitter bio immediately on status change
                    if self.bio_update_callback:
                        try:
                            now = datetime.now()
                            sec_status = "SEC is OPEN. "
                            self.bio_update_callback(now, additional_info=sec_status)
                        except Exception as e:
                            logger.error(f"Error updating Twitter bio on SEC open: {e}")
                            
                elif not is_business_hours and self.was_business_hours:
                    # Transition: Open -> Closed
                    logger.info("SEC is now closed")
                    
                    # Update Twitter bio immediately on status change
                    if self.bio_update_callback:
                        try:
                            now = datetime.now()
                            sec_status = "SEC is CLOSED. "
                            self.bio_update_callback(now, additional_info=sec_status)
                        except Exception as e:
                            logger.error(f"Error updating Twitter bio on SEC close: {e}")
                
                # Update state
                self.was_business_hours = is_business_hours
                
                # Run operation if it's business hours
                if is_business_hours:
                    try:
                        logger.debug("Running scheduled operation during business hours")
                        self.operation_callback()
                        
                        # We'll let the application handle Twitter bio updates after batch processing
                                
                    except Exception as e:
                        logger.error(f"Error in scheduled operation: {e}")
                else:
                    # If outside business hours, log status and do a periodic bio update
                    status = self.get_next_business_hours()
                    logger.info(status["message"])
                    
                    # Periodically update the Twitter bio even during closed hours
                    # to ensure accurate next review time
                    if self.bio_update_callback:
                        try:
                            now = datetime.now()
                            sec_status = "SEC is CLOSED. "
                            self.bio_update_callback(now, additional_info=sec_status)
                        except Exception as e:
                            logger.error(f"Error updating Twitter bio during closed hours: {e}")
                    
                    # Sleep for 30 minutes if outside business hours
                    # This reduces unnecessary log spam
                    time.sleep(1800)  # 30 minutes in seconds
                
                # Sleep until next check
                time.sleep(self.CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}")
                time.sleep(self.CHECK_INTERVAL) 