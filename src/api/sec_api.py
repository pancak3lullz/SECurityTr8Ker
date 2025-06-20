import os
import time
import requests
import json
import random
from typing import Dict, List, Optional, Tuple, Union
import xmltodict
from datetime import datetime, timedelta
from functools import lru_cache
from src.models.filing import Filing
from src.utils.logger import get_logger
from src.config import USER_AGENT, RSS_URL, REQUEST_INTERVAL

logger = get_logger(__name__)

class SECApiClient:
    """Client for interacting with SEC APIs with built-in caching and rate limiting."""
    
    def __init__(self, user_agent: str = USER_AGENT, 
                 cache_dir: str = './cache',
                 request_interval: float = REQUEST_INTERVAL,
                 max_retries: int = 3):
        """
        Initialize the SEC API client.
        
        Args:
            user_agent: User agent string for SEC API requests
            cache_dir: Directory to store cached responses
            request_interval: Minimum time between requests in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.user_agent = user_agent
        self.cache_dir = cache_dir
        self.request_interval = request_interval
        self.last_request_time = 0
        self.max_retries = max_retries
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Track request statistics
        self.request_count = 0
        self.cache_hits = 0
        self.retry_count = 0
        
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_interval:
            sleep_time = self.request_interval - time_since_last_request
            logger.debug(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _get_cache_path(self, url: str) -> str:
        """Get cache file path for a URL."""
        # Create a filename from the URL (removing invalid chars)
        filename = "".join(c if c.isalnum() else "_" for c in url)
        # Limit filename length
        if len(filename) > 100:
            filename = filename[:100]
        return os.path.join(self.cache_dir, f"{filename}.json")
    
    def _get_cached_response(self, url: str, max_age: int = 3600) -> Optional[Dict]:
        """
        Get cached response for URL if available and not expired.
        
        Args:
            url: URL of the request
            max_age: Maximum age of cache in seconds (default: 1 hour)
            
        Returns:
            Cached response dict or None if not available or expired
        """
        cache_path = self._get_cache_path(url)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid
                cache_time = cached_data.get('cached_at', 0)
                current_time = time.time()
                
                if current_time - cache_time <= max_age:
                    self.cache_hits += 1
                    logger.debug(f"Cache hit for {url}")
                    return cached_data.get('data')
                else:
                    logger.debug(f"Cache expired for {url}")
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted cache for {url}: {e}")
                # Delete corrupted cache file
                try:
                    os.remove(cache_path)
                    logger.info(f"Removed corrupted cache file: {cache_path}")
                except OSError as ose:
                    logger.warning(f"Failed to remove corrupted cache file: {ose}")
            except Exception as e:
                logger.warning(f"Failed to read cache for {url}: {e}")
                
        return None
    
    def _save_to_cache(self, url: str, data: Dict):
        """Save response data to cache."""
        cache_path = self._get_cache_path(url)
        
        try:
            cache_data = {
                'cached_at': time.time(),
                'data': data
            }
            
            # Write to temporary file first
            temp_cache_path = f"{cache_path}.tmp"
            with open(temp_cache_path, 'w') as f:
                json.dump(cache_data, f)
                
            # Rename to final path (atomic operation)
            os.replace(temp_cache_path, cache_path)
                
            logger.debug(f"Saved response to cache: {url}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {url}: {e}")
            # Attempt to clean up temp file if it exists
            try:
                if os.path.exists(temp_cache_path):
                    os.remove(temp_cache_path)
            except:
                pass
    
    def _exponential_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff time with jitter."""
        base_delay = min(self.request_interval * 2 ** retry_count, 60)  # Cap at 60 seconds
        jitter = random.uniform(0, 0.5 * base_delay)  # Add up to 50% jitter
        return base_delay + jitter
    
    def fetch_url(self, url: str, use_cache: bool = True, 
                  cache_max_age: int = 3600, retry_count: int = 0) -> Tuple[bool, Union[Dict, str, bytes]]:
        """
        Fetch data from a URL with caching and rate limiting.
        
        Args:
            url: URL to fetch
            use_cache: Whether to use cached response if available
            cache_max_age: Maximum age of cache in seconds
            retry_count: Current retry attempt (used internally)
            
        Returns:
            Tuple of (success, response_data)
        """
        # Check cache first if enabled
        if use_cache:
            cached_data = self._get_cached_response(url, cache_max_age)
            if cached_data is not None:
                return True, cached_data
        
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        # Make the request
        headers = {'User-Agent': self.user_agent}
        
        try:
            self.request_count += 1
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    data = response.json()
                    if use_cache:
                        self._save_to_cache(url, data)
                    return True, data
                except json.JSONDecodeError:
                    # If not JSON, return content
                    if use_cache and response.content:
                        # For non-JSON responses, we don't cache by default
                        # But we could implement a different caching mechanism if needed
                        pass
                    return True, response.content
            elif response.status_code == 429:  # Too Many Requests
                if retry_count < self.max_retries:
                    self.retry_count += 1
                    backoff_time = self._exponential_backoff(retry_count)
                    logger.warning(f"Rate limited (429) for {url}. Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                    # Recursive retry with incremented counter
                    return self.fetch_url(url, use_cache, cache_max_age, retry_count + 1)
                else:
                    logger.error(f"HTTP error 429: {url} (max retries exceeded)")
                    return False, f"HTTP error 429 (max retries exceeded)"
            else:
                if retry_count < self.max_retries and response.status_code >= 500:
                    # Retry server errors
                    self.retry_count += 1
                    backoff_time = self._exponential_backoff(retry_count)
                    logger.warning(f"Server error {response.status_code} for {url}. Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                    # Recursive retry with incremented counter
                    return self.fetch_url(url, use_cache, cache_max_age, retry_count + 1)
                else:
                    logger.error(f"HTTP error {response.status_code}: {url}")
                    return False, f"HTTP error {response.status_code}"
                
        except requests.Timeout:
            if retry_count < self.max_retries:
                self.retry_count += 1
                backoff_time = self._exponential_backoff(retry_count)
                logger.warning(f"Request timeout for {url}. Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
                # Recursive retry with incremented counter
                return self.fetch_url(url, use_cache, cache_max_age, retry_count + 1)
            else:
                logger.error(f"Request timeout for {url} (max retries exceeded)")
                return False, "Request timeout (max retries exceeded)"
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            if retry_count < self.max_retries:
                self.retry_count += 1
                backoff_time = self._exponential_backoff(retry_count)
                logger.warning(f"Request failed for {url}. Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
                # Recursive retry with incremented counter
                return self.fetch_url(url, use_cache, cache_max_age, retry_count + 1)
            return False, str(e)
    
    def fetch_rss_feed(self) -> List[Filing]:
        """
        Fetch the SEC RSS feed and parse filings.
        
        Returns:
            List of Filing objects
        """
        logger.info(f"Fetching SEC RSS feed from {RSS_URL}")
        
        # RSS feeds change frequently, use shorter cache time
        success, response = self.fetch_url(RSS_URL, cache_max_age=300)
        
        if not success:
            logger.error(f"Failed to fetch RSS feed: {response}")
            return []
            
        try:
            # Parse XML
            if isinstance(response, bytes):
                feed = xmltodict.parse(response)
            else:
                # If we got cached JSON
                feed = response
                
            # Process items
            filings = []
            
            if 'rss' in feed and 'channel' in feed['rss']:
                items = feed['rss']['channel'].get('item', [])
                
                # Ensure items is a list
                if not isinstance(items, list):
                    items = [items]
                    
                logger.info(f"Found {len(items)} items in RSS feed")
                
                # Process each item
                for item in items:
                    try:
                        filing = self._parse_rss_item(item)
                        if filing:
                            filings.append(filing)
                    except Exception as e:
                        logger.error(f"Error parsing RSS item: {e}")
            
            logger.info(f"Successfully processed {len(filings)} filings from RSS feed")
            return filings
            
        except Exception as e:
            logger.error(f"Error processing RSS feed: {e}")
            return []
    
    def _parse_rss_item(self, item: Dict) -> Optional[Filing]:
        """Parse an RSS feed item into a Filing object."""
        try:
            # Extract filing info from xbrlFiling
            xbrl_filing = item.get('edgar:xbrlFiling', {})
            
            # Form type is in the description field, not in xbrlFiling
            form_type = item.get('description', '')
            company_name = xbrl_filing.get('edgar:companyName', '')
            cik = xbrl_filing.get('edgar:cikNumber', '')
            
            # Get the document URL from xbrlFiles
            filing_href = ''
            if 'edgar:xbrlFiles' in xbrl_filing:
                xbrl_files = xbrl_filing['edgar:xbrlFiles'].get('edgar:xbrlFile', [])
                
                # Ensure xbrl_files is a list
                if not isinstance(xbrl_files, list):
                    xbrl_files = [xbrl_files]
                
                # Look for HTML file
                for xbrl_file in xbrl_files:
                    if xbrl_file.get('@edgar:url', '').endswith(('.htm', '.html')):
                        filing_href = xbrl_file.get('@edgar:url', '')
                        break
            
            # Skip incomplete items
            if not all([form_type, company_name, cik, filing_href]):
                logger.debug(f"Skipping incomplete item: {item}")
                return None
            
            # Only process 8-K filings for cybersecurity disclosures
            if form_type != '8-K':
                logger.debug(f"Skipping non-8-K filing: {form_type}")
                return None
            
            filing = Filing(
                form_type=form_type,
                company_name=company_name,
                cik=cik,
                filing_href=filing_href,
                filing_date=item.get('pubDate', '')
            )
            
            return filing
            
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None
    
    def get_ticker_symbol(self, cik: str) -> Optional[str]:
        """Get ticker symbol for a CIK number with caching."""
        # Format CIK to 10 digits
        cik = cik.lstrip('0')
        padded_cik = cik.zfill(10)
        
        url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
        
        # Company information doesn't change often, longer cache time
        success, response = self.fetch_url(url, cache_max_age=86400)  # 24 hours
        
        if success and isinstance(response, dict):
            tickers = response.get('tickers', [])
            if tickers and isinstance(tickers, list) and len(tickers) > 0:
                return tickers[0]
        
        return None
    
    def get_document_content(self, url: str) -> Optional[str]:
        """Fetch document content with caching."""
        logger.debug(f"Fetching document from {url}")
        
        # Filing content rarely changes, longer cache time
        success, response = self.fetch_url(url, cache_max_age=86400)  # 24 hours
        
        if success:
            if isinstance(response, bytes):
                return response.decode('utf-8', errors='replace')
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        
        return None
    
    def get_stats(self) -> Dict:
        """Get API client statistics."""
        return {
            'requests': self.request_count,
            'cache_hits': self.cache_hits,
            'retries': self.retry_count,
            'cache_hit_ratio': self.cache_hits / max(1, self.request_count),
            'request_interval': self.request_interval
        } 