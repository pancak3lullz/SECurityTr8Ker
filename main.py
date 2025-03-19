#!/usr/bin/env python3
"""
SECurityTr8Ker - SEC RSS Feed Monitor for Cybersecurity Disclosures

This application monitors the U.S. Securities and Exchange Commission's (SEC) 
RSS feed for new 8-K filings that contain material cybersecurity incident 
disclosures. When a disclosure is found, notifications are sent through 
configured channels (Slack, Teams, Telegram, Twitter).
"""

import os
import argparse
import signal
import sys
from src.utils.logger import get_logger
from src.core.application import SECurityTr8Ker
from src.config import DISCLOSURES_FILE

logger = get_logger(__name__)

# Global application instance
app = None

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM signals."""
    logger.info("Shutdown signal received")
    if app:
        app.stop()
    sys.exit(0)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SECurityTr8Ker - SEC RSS Feed Monitor for Cybersecurity Disclosures"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=600,
        help="Interval between checks in seconds (default: 600)"
    )
    parser.add_argument(
        "--storage-file", 
        type=str, 
        default=DISCLOSURES_FILE,
        help=f"Path to storage file (default: {DISCLOSURES_FILE})"
    )
    parser.add_argument(
        "--cache-dir", 
        type=str, 
        default="./cache",
        help="Directory for caching API responses (default: ./cache)"
    )
    parser.add_argument(
        "--24-7", 
        action="store_true",
        dest="continuous",
        help="Run continuously 24/7 instead of only during SEC business hours"
    )
    parser.add_argument(
        "--business-hours",
        action="store_true",
        dest="business_hours_only", 
        default=True,
        help="Only run during SEC business hours (M-F, 9:00 AM - 5:30 PM ET) (default)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Handle conflicting arguments
    if args.continuous:
        args.business_hours_only = False
        
    return args

def main():
    """Main entry point."""
    global app
    
    # Parse command line arguments
    args = parse_args()
    
    # Set log level based on debug flag
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print banner
    logger.info("=" * 80)
    logger.info(" SECurityTr8Ker - SEC RSS Feed Monitor for Cybersecurity Disclosures")
    logger.info("=" * 80)
    
    # Create and start application
    app = SECurityTr8Ker(
        storage_file=args.storage_file,
        check_interval=args.interval,
        cache_dir=args.cache_dir,
        business_hours_only=args.business_hours_only
    )
    
    # Log operating mode
    if args.business_hours_only:
        logger.info("Operating in business hours mode (M-F, 9:00 AM - 5:30 PM ET)")
    else:
        logger.info("Operating in continuous mode (24/7)")
    
    try:
        app.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        if app:
            app.stop()

if __name__ == "__main__":
    main()
