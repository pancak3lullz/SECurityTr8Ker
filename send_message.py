#!/usr/bin/env python3
"""
SECurityTr8Ker Message Sender

A command-line tool for sending out-of-band messages through SECurityTr8Ker's 
notification channels.

This script can be used to send plain text messages to all configured notification
channels (Slack, Teams, Telegram, Twitter) without disrupting the main application.
"""

import os
import sys
import argparse
from typing import List, Optional, Dict, Any
from src.notifiers.notification_service import create_notification_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Send out-of-band messages through SECurityTr8Ker notification channels"
    )
    parser.add_argument(
        "message",
        type=str,
        help="The message to send through notification channels"
    )
    parser.add_argument(
        "--channels",
        type=str,
        help="Comma-separated list of specific channels to message (default: all configured channels)"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="[SECurityTr8Ker]",
        help="Prefix to add to the message (default: [SECurityTr8Ker])"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()

def send_message(
    message: str, 
    channels: Optional[List[str]] = None,
    prefix: str = "[SECurityTr8Ker]"
) -> Dict[str, bool]:
    """
    Send a message through specified channels.
    
    Args:
        message: Message to send
        channels: List of specific channel names to use (None for all)
        prefix: Prefix to add to the message
        
    Returns:
        Dictionary mapping channel names to success status
    """
    # Create notification service with all available channels
    notification_service = create_notification_service()
    
    if not notification_service.active_channels:
        logger.error("No notification channels are configured")
        return {}
    
    # Format message with prefix
    formatted_message = f"{prefix} {message}"
    
    # Send to specific channels if requested
    if channels:
        results = {}
        for channel_name in channels:
            if channel_name in notification_service.channels:
                channel = notification_service.channels[channel_name]
                try:
                    logger.info(f"Sending message to {channel_name}")
                    success = channel.send_text_message(formatted_message)
                    results[channel_name] = success
                    
                    if success:
                        logger.info(f"Successfully sent message to {channel_name}")
                    else:
                        logger.error(f"Failed to send message to {channel_name}")
                except Exception as e:
                    logger.error(f"Error sending message to {channel_name}: {e}")
                    results[channel_name] = False
            else:
                logger.warning(f"Channel '{channel_name}' is not configured or active")
                results[channel_name] = False
        return results
    else:
        # Send to all channels
        return notification_service.send_text_message_to_all(formatted_message)

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Set log level based on debug flag
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Convert channels string to list if provided
    channels = None
    if args.channels:
        channels = [c.strip() for c in args.channels.split(",")]
    
    # Send the message
    logger.info(f"Sending message to channels: {channels if channels else 'all'}")
    results = send_message(args.message, channels, args.prefix)
    
    # Display results
    if results:
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Message sent to {success_count}/{len(results)} channels")
        
        for channel, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{channel}: {status}")
        
        # Exit with non-zero code if any channel failed
        if success_count < len(results):
            sys.exit(1)
    else:
        logger.error("No messages were sent")
        sys.exit(1)

if __name__ == "__main__":
    main() 