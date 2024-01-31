import os
import requests
import time
import xmltodict
import logging
import colorlog
import json
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup

# Ensure the 'logs' directory exists
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Log file path in 'logs' directory
log_file_path = os.path.join(logs_dir, 'script_log.log')

# Custom color scheme for log levels
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}

# Setting up colored logging for terminal
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors=LOG_COLORS))
handler.setLevel(logging.ERROR) # Set terminal handler level to INFO

logger = colorlog.getLogger()
logger.setLevel(logging.DEBUG) # Set logger level to DEBUG
logger.addHandler(handler)

# Setting up logging to file with updated path
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

def fetch_filings_from_rss(url):
    filings = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            feed = xmltodict.parse(response.content)
            for item in feed['rss']['channel']['item']:
                form_type = item.get('edgar:xbrlFiling', {}).get('edgar:formType')
                cik_number = item.get('edgar:xbrlFiling', {}).get('edgar:cikNumber')
                if form_type and cik_number and (form_type in ['8-K', '6-K']):
                    filings.append((cik_number, item.get('title', '').split(' (')[0]))
            logger.info("Fetched and parsed RSS feed successfully.", extra={"log_color": "green"})
    except Exception as e:
        logger.critical(f"Error fetching filings: {e}", extra={"log_color": "red"})
    return filings

def fetch_directories(cik_number):
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_number}/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch directories for CIK {cik_number}")

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.find_all('tr')
    recent_cutoff = datetime.now() - timedelta(days=30)
    directories = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) == 3:
            dir_name = cols[0].text.strip('/')
            dir_date_str = cols[2].text.strip()
            try:
                dir_date = datetime.strptime(dir_date_str, '%Y-%m-%d %H:%M:%S')
                if dir_date >= recent_cutoff:
                    directories.append(dir_name)
            except ValueError:
                continue

    return directories

def find_cybersecurity_htm_link(cik_number):
    directories = fetch_directories(cik_number)
    headers = {'User-Agent': 'Mozilla/5.0'}

    for directory in directories:
        dir_url = f"https://www.sec.gov/Archives/edgar/data/{cik_number}/{directory}/"
        response = requests.get(dir_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            htm_links = [link.get('href') for link in soup.find_all('a') if link.get('href').endswith('.htm')]

            for htm_link in htm_links:
                htm_url = f"https://www.sec.gov{htm_link}"
                htm_response = requests.get(htm_url, headers=headers)
                if htm_response.status_code == 200:
                    if "Material Cybersecurity Incidents" in htm_response.text:
                        return htm_url
    return None

def check_cybersecurity_disclosure(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            ticker_symbol = data.get('tickers', [])[0] if data.get('tickers') else None
            display_name = f"{company_name} (${ticker_symbol})" if ticker_symbol else company_name
            logger.info(f"Successfully fetched data for CIK: {cik_number} ({display_name})", extra={"log_color": "green"})

            for item in data.get("filings", {}).get("recent", {}).get("items", []):
                if "1.05" in item.split(','):
                    # Find the correct .htm link for the disclosure
                    cybersecurity_htm_link = find_cybersecurity_htm_link(cik_number)
                    if cybersecurity_htm_link:
                        logger.error(f"Cybersecurity disclosure (1.05) found for {display_name} (CIK: {cik_number}). More details: {cybersecurity_htm_link}", extra={"log_color": "red"})
                        return True, ticker_symbol
                    else:
                        logger.warning(f"No specific cybersecurity disclosure found for {display_name} (CIK: {cik_number}).", extra={"log_color": "yellow"})
            return False, ticker_symbol
        else:
            logger.error(f"Error fetching ticker symbol for CIK: {cik_number}", extra={"log_color": "red"})
            return False, None
    except Exception as e:
        logger.critical(f"Error checking disclosure: {e}", extra={"log_color": "red"})
        return False, None

def main():
    print("Script started. Monitoring SEC RSS feed for cybersecurity disclosures...")
    logger.info("Script started. Monitoring SEC RSS feed for cybersecurity disclosures...")
    rss_url = "https://www.sec.gov/Archives/edgar/usgaap.rss.xml"
    while True:
        filings = fetch_filings_from_rss(rss_url)
        for cik_number, company_name in filings:
            success, ticker_symbol = check_cybersecurity_disclosure(cik_number, company_name)  # Capture ticker_symbol here
            display_name = f"{company_name} (${ticker_symbol})" if ticker_symbol else company_name
            if success:
                logger.info(f"Disclosure check successful for {display_name} (CIK: {cik_number}).", extra={"log_color": "green"})
            else:
                logger.info(f"No cybersecurity (1.05) disclosures found for {display_name} (CIK: {cik_number}).", extra={"log_color": "green"})
        print("Waiting for 10 minutes before the next check...")
        logger.info("Waiting for 10 minutes before the next check...")
        time.sleep(600)

if __name__ == "__main__":
    main()
