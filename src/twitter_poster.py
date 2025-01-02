import tweepy
import pytz
from datetime import datetime
from src.config import TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_BEARER_TOKEN, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
from src.utils import fetch_filings_from_rss, process_disclosures
from src.logger import logger

# Initialize Tweepy API for updating bio
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# Initialize Tweepy Client for posting tweets
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
)

def update_twitter_bio(last_checked_time_utc):
    eastern = pytz.timezone('US/Eastern')
    last_checked_time_et = last_checked_time_utc.astimezone(eastern)
    bio_message = f"I monitor the SEC's RSS feed for 8-K filings disclosing cybersecurity incidents.\n\nLast review: {last_checked_time_et.strftime('%Y-%m-%d %H:%M:%S')} ET."
    try:
        api.update_profile(description=bio_message)
        logger.info("Twitter bio updated.")
    except Exception as e:
        logger.critical(f"Failed to update Twitter bio: {e}")

def tweet(company_name, cik_number, ticker_symbol, document_link, pubDate):
    ticker_part = f" ${ticker_symbol}" if ticker_symbol else ""
    base_message = f"{pubDate}\nA cybersecurity incident has been disclosed by {company_name}{ticker_part} (CIK: {cik_number})\n\nView SEC Filing: {document_link}"
    
    if len(base_message) <= 280:
        tweet_message = base_message
    else:
        tweet_message = f"{pubDate}\nA cybersecurity incident has been disclosed by{ticker_part} (CIK: {cik_number})\n\nView SEC Filing: {document_link}"

    try:
        response = client.create_tweet(text=tweet_message)
        logger.info(f"Tweet posted successfully: {response}")
        return True
    except Exception as e:
        logger.critical(f"Failed to post tweet: {e}")
        return False

def process_twitter_disclosures(filings):
    process_disclosures(filings, tweet)

if __name__ == "__main__":
    filings = fetch_filings_from_rss()
    process_twitter_disclosures(filings)
    update_twitter_bio(datetime.utcnow())
