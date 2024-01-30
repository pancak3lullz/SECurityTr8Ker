import os
import requests
import time
import xmltodict
import logging
import colorlog
import json
from datetime import datetime
import re

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

def check_cybersecurity_disclosure(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully fetched data for CIK: {cik_number}", extra={"log_color": "green"})
            if "filings" in data and "recent" in data["filings"] and "accessionNumber" in data["filings"]["recent"]:
                accession_numbers = data["filings"]["recent"]["accessionNumber"]
                if accession_numbers:
                    first_accession_number = accession_numbers[0]
                    cleaned_accession_number = first_accession_number.replace('-', '')
                    index_headers_url = f"https://www.sec.gov/Archives/edgar/data/{cik_number}/{cleaned_accession_number}/{first_accession_number}-index-headers.html"

                    for item in data["filings"]["recent"]["items"]:
                        if "1.05" in item.split(','):
                            index_headers_response = requests.get(index_headers_url, headers=headers)
                            if index_headers_response.status_code == 200:
                                # Using regex to find the .htm file in the <TEXT> section
                                match = re.search(r'Document \d+ - file: ([^<]+\.htm)', index_headers_response.text, re.IGNORECASE)
                                if match:
                                    htm_filename = match.group(1)
                                    htm_file_link = f"https://www.sec.gov/Archives/edgar/data/{cik_number}/{cleaned_accession_number}/{htm_filename}"
                                    logger.error(f"Cybersecurity disclosure (1.05) found for {company_name} (CIK: {cik_number}). More details: {htm_file_link}", extra={"log_color": "red"})
                                    return True
                            logger.error(f"Cybersecurity disclosure (1.05) found for {company_name} (CIK: {cik_number}). Unable to find .htm file. More details: {index_headers_url}", extra={"log_color": "red"})
                            return True
        return False
    except Exception as e:
        logger.critical(f"Error checking disclosure: {e}", extra={"log_color": "red"})
        return False

def main():
    logger.info("Script started. Monitoring SEC RSS feed for cybersecurity disclosures...")
    rss_url = "https://www.sec.gov/Archives/edgar/usgaap.rss.xml"
    while True:
        filings = fetch_filings_from_rss(rss_url)
        for cik_number, company_name in filings:
            success = check_cybersecurity_disclosure(cik_number, company_name)
            if success:
                logger.info(f"Disclosure check successful for {company_name} (CIK: {cik_number}).", extra={"log_color": "green"})
            else:
                logger.info(f"No cybersecurity (1.05) disclosures found for {company_name} (CIK: {cik_number}).", extra={"log_color": "green"})
        print("Waiting for 10 minutes before the next check...")
        logger.info("Waiting for 10 minutes before the next check...")
        time.sleep(600)

if __name__ == "__main__":
    main()
