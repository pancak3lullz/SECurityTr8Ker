import os
import requests
import xmltodict
import logging
import colorlog
from bs4 import BeautifulSoup
import time
from datetime import datetime

# Define request interval, log file path, and logs directory
REQUEST_INTERVAL = 0.3
logs_dir = 'local_SECurityTr8Ker-v2'
log_file_path = os.path.join(logs_dir, 'debug.log')

# Ensure the logs directory exists
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Initialize the root logger to capture DEBUG level logs
logger = colorlog.getLogger()
logger.setLevel(logging.DEBUG)  # Capture everything at DEBUG level and above

# Setting up colored logging for terminal
terminal_handler = colorlog.StreamHandler()
terminal_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }))
terminal_handler.setLevel(logging.INFO)  # Terminal to show INFO and above
logger.addHandler(terminal_handler)

# Setting up logging to file to capture DEBUG and above
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)  # File to capture everything at DEBUG level
logger.addHandler(file_handler)

def get_ticker_symbol(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Pancake Stacks Inc./1.0 (pancak3lullz@gmail.com)'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            data = response.json()
            ticker_symbol = data.get('tickers', [])[0] if data.get('tickers') else None
            return ticker_symbol
        else:
            logger.error(f"Error fetching ticker symbol for CIK: {cik_number}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving ticker symbol: {e}")
        return None

def inspect_document_for_cybersecurity(link):
    headers = {'User-Agent': 'Pancake Stacks Inc./1.0 (pancak3lullz@gmail.com)'}
    try:
        response = requests.get(link, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return "Material Cybersecurity Incidents" in soup.text
    except Exception as e:
        logger.error(f"Failed to inspect document at {link}: {e}")
    return False

def fetch_filings_from_rss(url):
    headers = {'User-Agent': 'Pancake Stacks Inc./1.0 (pancak3lullz@gmail.com)'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            feed = xmltodict.parse(response.content)
            for item in feed['rss']['channel']['item']:
                xbrlFiling = item['edgar:xbrlFiling']
                form_type = xbrlFiling['edgar:formType']
                pubDate = item['pubDate']
                if form_type in ['8-K', '8-K/A', '6-K']:
                    company_name = xbrlFiling['edgar:companyName']
                    cik_number = xbrlFiling['edgar:cikNumber']
                    document_links = [xbrlFile['@edgar:url'] for xbrlFile in xbrlFiling['edgar:xbrlFiles']['edgar:xbrlFile'] if xbrlFile['@edgar:type'] in ['8-K', '8-K/A', '6-K']]
                    
                    for document_link in document_links:
                        if inspect_document_for_cybersecurity(document_link):
                            ticker_symbol = get_ticker_symbol(cik_number, company_name)
                            logger.info(f"Material Cybersecurity Incident found: {company_name} (Ticker:${ticker_symbol}) (CIK:{cik_number}) - {document_link} - Published on {pubDate}")
                            break  # Assuming we only need to log once per filing
            logger.info("Fetched and parsed RSS feed successfully.", extra={"log_color": "green"})
    except Exception as e:
        logger.critical("Error fetching filings: {}".format(e), extra={"log_color": "red"})

def monitor_sec_feed():
    rss_url = 'https://www.sec.gov/Archives/edgar/usgaap.rss.xml'
    while True:
        logger.info("Checking SEC RSS feed for 8-K and 6-K filings...")
        fetch_filings_from_rss(rss_url)
        logger.info("Sleeping for 10 minutes before next check...")
        time.sleep(600)  # Sleep for 10 minutes

if __name__ == "__main__":
    monitor_sec_feed()
