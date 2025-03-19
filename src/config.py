import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if not os.path.exists(env_path):
    logger.error(f".env file not found at {env_path}")
else:
    load_dotenv(env_path)
    logger.info(".env file loaded successfully")

# SEC API Configuration
RSS_URL = 'https://www.sec.gov/Archives/edgar/usgaap.rss.xml'
# SEC rate limiting - more conservative defaults to avoid 429 errors
# The SEC website recommends no more than 10 requests per second
REQUEST_INTERVAL = float(os.getenv('SEC_REQUEST_INTERVAL', '1.0'))  # Default 1 second between requests
MAX_CONCURRENT_REQUESTS = int(os.getenv('SEC_MAX_CONCURRENT_REQUESTS', '5'))  # Max concurrent requests
MAX_RETRIES = int(os.getenv('SEC_MAX_RETRIES', '3'))  # Max retries for failed requests

# Use USER_AGENT from .env if provided, otherwise use default
USER_AGENT = os.getenv('USER_AGENT', "SECurityTr8Ker/1.0 (your-email@example.com)")
if USER_AGENT == "SECurityTr8Ker/1.0 (your-email@example.com)":
    logger.warning("Using default User-Agent. Please set your email in .env file for better SEC API access.")

# Twitter Configuration
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

# Teams Configuration
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Slack Configuration
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# File Storage
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISCLOSURES_FILE = os.path.join(BASE_DIR, "disclosures.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Log configuration
LOG_FILE_PATH = os.path.join(LOG_DIR, 'debug.log')

# Search Terms for cybersecurity incidents
SEARCH_TERMS = {
    'item_105': [
        "Material Cybersecurity Incidents",
        "Item 1.05",
        "ITEM 1.05",
        "MATERIAL CYBERSECURITY INCIDENTS"
    ],
    'cybersecurity': [
        "unauthorized access",
        "unauthorized activity",
        "cybersecurity incident",
        "cyber-attack",
        "cyberattack",
        "threat actor",
        "security incident",
        "ransomware attack",
        "cyber incident",
        "unauthorized third party",
        "unauthorized occurrences within its computer network"
    ]
}

# Notification Configurations - these will be None if not configured

if TEAMS_WEBHOOK_URL:
    logger.info("Teams webhook URL found in environment")
else:
    logger.warning("Teams webhook URL not found in environment")

if TELEGRAM_BOT_TOKEN:
    logger.info("Telegram bot token found in environment")
else:
    logger.warning("Telegram bot token not found in environment")

if TELEGRAM_CHAT_ID:
    logger.info("Telegram chat ID found in environment")
else:
    logger.warning("Telegram chat ID not found in environment")

if TWITTER_API_KEY:
    logger.info("Twitter API key found in environment")
else:
    logger.warning("Twitter API key not found in environment")

if TWITTER_API_SECRET:
    logger.info("Twitter API secret found in environment")
else:
    logger.warning("Twitter API secret not found in environment")

if TWITTER_ACCESS_TOKEN:
    logger.info("Twitter access token found in environment")
else:
    logger.warning("Twitter access token not found in environment")

if TWITTER_ACCESS_TOKEN_SECRET:
    logger.info("Twitter access token secret found in environment")
else:
    logger.warning("Twitter access token secret not found in environment")

if SLACK_WEBHOOK_URL:
    logger.info("Slack webhook URL found in environment")
else:
    logger.warning("Slack webhook URL not found in environment")

# Load notification configurations
def load_env_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config = {}
    
    # Teams configuration
    if TEAMS_WEBHOOK_URL:
        config['teams'] = {
            'webhook_url': TEAMS_WEBHOOK_URL
        }
    
    # Telegram configuration
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        config['telegram'] = {
            'bot_token': TELEGRAM_BOT_TOKEN,
            'chat_id': TELEGRAM_CHAT_ID
        }
    
    # Twitter configuration
    if all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        config['twitter'] = {
            'consumer_key': TWITTER_API_KEY,
            'consumer_secret': TWITTER_API_SECRET,
            'access_token': TWITTER_ACCESS_TOKEN,
            'access_token_secret': TWITTER_ACCESS_TOKEN_SECRET
        }
    
    # Slack configuration
    if SLACK_WEBHOOK_URL:
        config['slack'] = {
            'webhook_url': SLACK_WEBHOOK_URL
        }
    
    return config

# Load notification configurations
NOTIFICATION_CONFIG = load_env_config()
