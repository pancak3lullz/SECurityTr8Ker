import os
import re
import requests
import time
import xmltodict
from bs4 import BeautifulSoup
from datetime import datetime
import json
from src.config import REQUEST_INTERVAL, RSS_URL, DISCLOSURES_FILE, USER_AGENT, SEARCH_TERMS
from src.logger import logger
from typing import Dict, Any, List, Tuple

def load_disclosures():
    if os.path.exists(DISCLOSURES_FILE):
        try:
            with open(DISCLOSURES_FILE, 'r') as file:
                disclosures = json.load(file)
                # Ensure disclosures is a list
                if isinstance(disclosures, dict):
                    return list(disclosures.values())
                return disclosures
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"{DISCLOSURES_FILE} is empty or corrupted. Initializing empty disclosures list.")
    return []

def save_disclosures(disclosures):
    with open(DISCLOSURES_FILE, 'w') as file:
        json.dump(disclosures, file, indent=4)
    logger.info(f"Disclosures saved to {DISCLOSURES_FILE}")

def get_ticker_symbol(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': USER_AGENT}
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

def inspect_document(url: str, search_terms: List[str]) -> Tuple[bool, Dict[str, str]]:
    """
    Inspect a document for search terms.
    Returns a tuple of (bool, dict) where the bool indicates if any terms were found
    and the dict contains the matching terms and context.
    """
    headers = {'User-Agent': USER_AGENT}
    try:
        logger.debug(f"Fetching document from {url}")
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            document_text = soup.get_text(separator=' ').lower()

            # Remove any lingering XML tags, HTML tags, and new lines, but maintain spaces
            document_text = re.sub(r'(<[^>]+>)|(&#\d{1,4};)', ' ', document_text)
            document_text = re.sub(r'\s+', ' ', document_text).strip()

            # Exclude "Forward-Looking Statements" section
            document_text = re.sub(r'forward-looking statements.*?(?=(item\s+\d+\.\d+|$))', '', document_text, flags=re.IGNORECASE | re.DOTALL)

            # First, check for the terms related to Item 1.05 in the whole document
            item_105_terms = search_terms[:4]  # Only check the first four terms (related to Item 1.05)
            for term in item_105_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', document_text, re.IGNORECASE):
                    return True, {'matching_terms': [term], 'context': 'Item 1.05'}

            # Regex to match "Item 8.01" section and extract its content
            item_801_pattern = r'(item 8\.01)[^\n]*?(?=item\s*\d+\.\d+|$)'
            item_801_match = re.search(item_801_pattern, document_text, re.IGNORECASE | re.DOTALL)

            if item_801_match:
                item_801_text = item_801_match.group()

                # Search for cybersecurity-related terms within the "Item 8.01" section
                for term in search_terms[4:]:
                    if re.search(r'\b' + re.escape(term) + r'\b', item_801_text, re.IGNORECASE):
                        return True, {'matching_terms': [term], 'context': 'Item 8.01'}

    except Exception as e:
        logger.error(f"Error inspecting document: {e}")

    return False, None

def process_filing(filing: Dict[str, Any], search_terms: List[str]) -> Tuple[bool, List[str], str]:
    """Process a single filing and return if it matches search terms.
    Returns (matched, matching_terms, context)"""
    try:
        logger.debug(f"Processing filing for {filing['company_name']} ({filing['form_type']})")
        
        # Inspect the filing
        found, result = inspect_document(filing['filing_href'], search_terms)
        
        if found and result:
            return True, result['matching_terms'], result['context']
        
        return False, [], ""
            
    except Exception as e:
        logger.error(f"Error processing filing: {e}")
        return False, [], ""

def fetch_filings_from_rss():
    headers = {'User-Agent': USER_AGENT}
    try:
        logger.debug(f"Requesting RSS feed from {RSS_URL}")
        response = requests.get(RSS_URL, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        
        if response.status_code == 200:
            logger.debug("RSS feed fetched successfully, parsing content...")
            feed = xmltodict.parse(response.content)
            
            # Get items from feed structure
            items = []
            if 'rss' in feed and 'channel' in feed['rss']:
                items = feed['rss']['channel'].get('item', [])
                if not isinstance(items, list):
                    items = [items]
                
                logger.debug(f"Found {len(items)} items in feed")
                logger.debug(f"Sample item structure: {list(items[0].keys()) if items else 'No items'}")
                
                # Process and clean up items
                processed_items = []
                for item in items:
                    try:
                        # Extract filing info from xbrlFiling
                        xbrl_filing = item.get('edgar:xbrlFiling', {})
                        
                        form_type = xbrl_filing.get('edgar:formType', '')
                        company_name = xbrl_filing.get('edgar:companyName', '')
                        cik = xbrl_filing.get('edgar:cikNumber', '')
                        
                        # Get the document URL from xbrlFiles
                        filing_href = ''
                        if 'edgar:xbrlFiles' in xbrl_filing:
                            xbrl_files = xbrl_filing['edgar:xbrlFiles'].get('edgar:xbrlFile', [])
                            if not isinstance(xbrl_files, list):
                                xbrl_files = [xbrl_files]
                            
                            # Look for HTML file
                            for xbrl_file in xbrl_files:
                                if xbrl_file.get('@edgar:url', '').endswith(('.htm', '.html')):
                                    filing_href = xbrl_file.get('@edgar:url', '')
                                    break
                        
                        if not all([form_type, company_name, cik, filing_href]):
                            logger.debug(f"Skipping incomplete item: {item}")
                            continue
                        
                        processed_item = {
                            'form_type': form_type,
                            'company_name': company_name,
                            'cik': cik,
                            'filing_href': filing_href,
                            'pubDate': item.get('pubDate', '')
                        }
                        
                        logger.debug(f"Processed item: {processed_item}")
                        processed_items.append(processed_item)
                    except Exception as e:
                        logger.error(f"Error processing feed item: {e}")
                        continue
                
                logger.debug(f"Successfully processed {len(processed_items)} items")
                return processed_items
            else:
                logger.error("Unexpected feed structure")
                logger.debug(f"Feed structure: {feed.keys()}")
                if 'rss' in feed:
                    logger.debug(f"Feed content keys: {feed['rss'].keys()}")
        else:
            logger.error(f"Error fetching RSS feed: HTTP {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response content: {response.content[:500]}")
    except Exception as e:
        logger.critical(f"Error fetching filings: {e}")
        if 'response' in locals():
            logger.debug(f"Response content: {response.content[:500]}")
    return []

def check_new_filings(filings):
    """Check new filings for cybersecurity disclosures.
    Args:
        filings (list): List of filings to check
    Returns:
        list: List of new disclosures found
    """
    try:
        disclosures = load_disclosures()
        new_disclosures = []
        
        # Create a set of existing filing URLs for faster lookup
        existing_filing_urls = {d.get('filing_url', '') for d in disclosures}
        
        # Process each filing
        for filing in filings:
            cik_number = filing['cik']
            form_type = filing['form_type']
            filing_url = filing['filing_href']
            
            # Skip if we've already processed this filing
            if filing_url in existing_filing_urls:
                logger.debug(f"Skipping already processed filing: {filing_url}")
                continue
            
            # Only process 8-K forms
            if form_type in ['8-K', '8-K/A']:
                # Check both item_105 and cybersecurity terms
                found_105, terms_105, context_105 = process_filing(filing, SEARCH_TERMS['item_105'])
                found_cyber, terms_cyber, context_cyber = process_filing(filing, SEARCH_TERMS['cybersecurity'])
                
                if found_105 or found_cyber:
                    ticker_symbol = get_ticker_symbol(cik_number, filing['company_name'])
                    ticker_part = f" ${ticker_symbol}" if ticker_symbol else ""
                    logger.info(f"{filing['pubDate']}\nA cybersecurity incident has been disclosed by {filing['company_name']}{ticker_part} (CIK: {cik_number})\n\nView SEC Filing: {filing_url}")
                    
                    # Combine matching terms and context
                    matching_terms = []
                    context = ""
                    if found_105:
                        matching_terms.extend(terms_105)
                        context += context_105 + "\n\n"
                    if found_cyber:
                        matching_terms.extend(terms_cyber)
                        context += context_cyber
                        
                    logger.info(f"Matching terms: {', '.join(matching_terms)}")
                    
                    new_disclosure = {
                        'company_name': filing['company_name'],
                        'cik': cik_number,
                        'ticker': ticker_symbol,
                        'form_type': form_type,
                        'filing_date': filing['pubDate'],
                        'filing_url': filing_url,
                        'matching_terms': matching_terms,
                        'context': context.strip()
                    }
                    new_disclosures.append(new_disclosure)
        
        # Save new disclosures
        if new_disclosures:
            save_disclosures(disclosures + new_disclosures)
            
        return new_disclosures
            
    except Exception as e:
        logger.error(f"Error checking new filings: {e}")
        return []

def process_disclosures(filings, notification_function):
    """Process disclosures and send notifications.
    Args:
        filings (list): List of filings to process
        notification_function (callable): Function to call for each disclosure
    """
    if not filings:
        logger.info("No new filings to process")
        return

    for filing in filings:
        try:
            company_name = filing.get('company_name', '')
            cik_number = filing.get('cik', '')
            document_link = filing.get('filing_url', '')
            pub_date = filing.get('filing_date', '')
            ticker_symbol = filing.get('ticker', '')

            notification_function(
                company_name,
                cik_number,
                ticker_symbol,
                document_link,
                pub_date
            )
        except Exception as e:
            logger.error(f"Error processing disclosure: {e}")
            continue
