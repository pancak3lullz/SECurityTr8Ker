from src.utils import fetch_filings_from_rss, check_new_filings
from src.logger import logger
from src.config import (
    TEAMS_WEBHOOK_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    SLACK_WEBHOOK_URL
)
from datetime import datetime
import time
import importlib

# Try to import and configure notification modules
notification_modules = {}

# Check Teams module
if TEAMS_WEBHOOK_URL:
    try:
        from src.teams_poster import post_to_teams
        notification_modules['teams'] = post_to_teams
        logger.info("Teams notification module loaded and configured successfully")
    except ImportError:
        logger.info("Teams notification module not available (module import failed)")
else:
    logger.info("Teams notification module not configured in .env")

# Check Telegram module
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    try:
        from src.telegram_poster import send_telegram_message
        notification_modules['telegram'] = send_telegram_message
        logger.info("Telegram notification module loaded and configured successfully")
    except ImportError:
        logger.info("Telegram notification module not available (module import failed)")
else:
    logger.info("Telegram notification module not configured in .env")

# Check Twitter module
if all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
    try:
        from src.twitter_poster import tweet, update_twitter_bio
        notification_modules['twitter'] = tweet
        notification_modules['twitter_bio'] = update_twitter_bio
        logger.info("Twitter notification module loaded and configured successfully")
    except ImportError as e:
        logger.error(f"Failed to initialize Twitter module: {e}")
else:
    logger.info("Twitter notification module not configured in .env")

# Check Slack module
if SLACK_WEBHOOK_URL:
    try:
        from src.slack_poster import post_to_slack
        notification_modules['slack'] = post_to_slack
        logger.info("Slack notification module loaded and configured successfully")
    except ImportError as e:
        logger.error(f"Failed to initialize Slack module: {e}")
else:
    logger.info("Slack notification module not configured in .env")

# Log active modules
if notification_modules:
    logger.info(f"Active notification modules: {', '.join(notification_modules.keys())}")
else:
    logger.warning("No notification modules available")

def notify_disclosure(disclosure):
    """Send notifications through available notification modules."""
    company_name = disclosure['company_name']
    cik_number = disclosure['cik']
    ticker_symbol = disclosure.get('ticker', '')
    document_link = disclosure['filing_url']
    pubDate = disclosure['filing_date']

    # Always log to console
    logger.info(f"New cybersecurity disclosure found:")
    logger.info(f"Company: {company_name} (CIK: {cik_number}, Ticker: {ticker_symbol})")
    logger.info(f"Published: {pubDate}")
    logger.info(f"Document: {document_link}")

    # Try each notification module
    if 'teams' in notification_modules:
        try:
            logger.info(f"Posting to Teams: {company_name}")
            if notification_modules['teams'](company_name, cik_number, ticker_symbol, document_link, pubDate):
                logger.info("Posted to Teams successfully")
            else:
                logger.error("Failed to post to Teams")
        except Exception as e:
            logger.error(f"Error posting to Teams: {e}")

    if 'telegram' in notification_modules:
        try:
            logger.info(f"Posting to Telegram: {company_name}")
            if notification_modules['telegram'](company_name, cik_number, ticker_symbol, document_link, pubDate):
                logger.info("Posted to Telegram successfully")
            else:
                logger.error("Failed to post to Telegram")
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")

    if 'twitter' in notification_modules:
        try:
            logger.info(f"Posting to Twitter: {company_name}")
            if notification_modules['twitter'](company_name, cik_number, ticker_symbol, document_link, pubDate):
                logger.info("Posted to Twitter successfully")
            else:
                logger.error("Failed to post to Twitter")
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")

    if 'slack' in notification_modules:
        try:
            logger.info(f"Posting to Slack: {company_name}")
            if notification_modules['slack'](company_name, cik_number, ticker_symbol, document_link, pubDate):
                logger.info("Posted to Slack successfully")
            else:
                logger.error("Failed to post to Slack")
        except Exception as e:
            logger.error(f"Error posting to Slack: {e}")

def monitor_sec_feed():
    """Monitor the SEC RSS feed for new 8-K filings."""
    while True:
        try:
            logger.info("Starting new check cycle...")
            logger.info("Fetching SEC RSS feed for 8-K filings...")
            
            # Fetch and process filings
            filings = fetch_filings_from_rss()
            if not filings:
                logger.warning("No filings found in RSS feed")
                continue
                
            logger.info(f"Found {len(filings)} filings to inspect")
            logger.info("Inspecting documents for cybersecurity disclosures...")
            
            # Check for new disclosures
            new_disclosures = check_new_filings(filings)
            
            # Update Twitter bio with last check time
            if 'twitter_bio' in notification_modules:
                notification_modules['twitter_bio'](datetime.utcnow())
            
            # Process any new disclosures
            if new_disclosures:
                logger.info(f"Found {len(new_disclosures)} new cybersecurity disclosure(s)")
                for disclosure in new_disclosures:
                    notify_disclosure(disclosure)
            else:
                logger.info("No new cybersecurity disclosures found in this batch")
                
            logger.info("Check cycle completed. Waiting 10 minutes before next check...")
            time.sleep(600)  # Wait 10 minutes before next check
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            logger.info("Waiting 10 minutes before retry...")
            time.sleep(600)  # Wait 10 minutes before retry

if __name__ == "__main__":
    logger.info("SECurityTr8Ker starting up...")
    monitor_sec_feed()
