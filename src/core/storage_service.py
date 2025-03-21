import os
import json
import time
from typing import List, Dict, Any, Optional, Set
from src.models.filing import Filing
from src.utils.logger import get_logger

logger = get_logger(__name__)

class StorageService:
    """
    Service for persistent storage of processed filings.
    """
    
    def __init__(self, storage_file: str):
        """
        Initialize storage service.
        
        Args:
            storage_file: Path to the storage file
        """
        self.storage_file = storage_file
        self.processed_ciks = set()  # Cache of processed CIKs for quick lookup
        self.processed_urls = set()  # Cache of processed URLs for quick lookup
        
        # Load existing data
        self._load_data()
        
    def _load_data(self):
        """Load existing data from storage file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                # Handle different formats
                if isinstance(data, list):
                    self.disclosures = data
                elif isinstance(data, dict):
                    self.disclosures = list(data.values())
                else:
                    logger.warning(f"Unknown storage format in {self.storage_file}. Initializing empty list.")
                    self.disclosures = []
                    
                # Build cache of processed items for quick lookup
                for disclosure in self.disclosures:
                    if 'cik' in disclosure:
                        self.processed_ciks.add(disclosure['cik'])
                    
                    # Handle both 'filing_url' and 'filing_href' for backward compatibility
                    if 'filing_url' in disclosure:
                        self.processed_urls.add(disclosure['filing_url'])
                    if 'filing_href' in disclosure:
                        self.processed_urls.add(disclosure['filing_href'])
                        
                logger.info(f"Loaded {len(self.disclosures)} existing disclosures from {self.storage_file}")
                logger.info(f"Cached {len(self.processed_urls)} processed URLs")
                
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading disclosures from {self.storage_file}: {e}")
                self.disclosures = []
        else:
            logger.info(f"Storage file {self.storage_file} does not exist. Initializing empty disclosures list.")
            self.disclosures = []
    
    def save_data(self):
        """Save disclosures to storage file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_file)), exist_ok=True)
            
            try:
                # First attempt: Direct write (most reliable when file is mounted as a volume in Docker)
                with open(self.storage_file, 'w') as f:
                    json.dump(self.disclosures, f, indent=2)
                logger.info(f"Saved {len(self.disclosures)} disclosures to {self.storage_file} (direct write)")
                return True
            except (IOError, OSError) as direct_write_error:
                logger.warning(f"Direct write to {self.storage_file} failed: {direct_write_error}. Trying atomic write...")
                
                # Second attempt: Atomic write with temp file
                temp_file = f"{self.storage_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(self.disclosures, f, indent=2)
                
                try:
                    # Try rename (this may fail if the file is mounted as a volume)
                    os.rename(temp_file, self.storage_file)
                    logger.info(f"Saved {len(self.disclosures)} disclosures to {self.storage_file} (atomic rename)")
                    return True
                except OSError as rename_error:
                    logger.warning(f"Rename operation failed: {rename_error}. Trying copy approach...")
                    
                    # Final attempt: Copy contents instead of rename
                    with open(temp_file, 'r') as src:
                        content = src.read()
                        
                    with open(self.storage_file, 'w') as dst:
                        dst.write(content)
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass  # Ignore cleanup errors
                        
                    logger.info(f"Saved {len(self.disclosures)} disclosures to {self.storage_file} (copy approach)")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving disclosures to {self.storage_file}: {e}", exc_info=True)
            return False
    
    def add_disclosure(self, filing: Filing) -> bool:
        """
        Add a new disclosure to storage.
        
        Args:
            filing: Filing to add
            
        Returns:
            bool: True if added, False if already exists or error
        """
        # Check if already processed
        if filing.filing_href in self.processed_urls:
            logger.debug(f"Disclosure already exists for URL: {filing.filing_href}")
            return False
            
        # Convert to dict for storage
        disclosure_dict = filing.to_dict()
        
        # Add timestamp
        disclosure_dict['added_at'] = time.time()
        
        # Add to storage
        self.disclosures.append(disclosure_dict)
        
        # Add both filing_href and filing_url to processed_urls set
        self.processed_urls.add(filing.filing_href)
        if hasattr(filing, 'filing_url') and filing.filing_url != filing.filing_href:
            self.processed_urls.add(filing.filing_url)
            
        self.processed_ciks.add(filing.cik)
        
        # Save to disk
        self.save_data()
        
        logger.info(f"Added new disclosure for {filing.company_name}")
        return True
    
    def has_processed_url(self, url: str) -> bool:
        """Check if a URL has already been processed."""
        is_processed = url in self.processed_urls
        if is_processed:
            logger.debug(f"URL has been processed before: {url}")
        return is_processed
        
    def has_processed_cik(self, cik: str) -> bool:
        """Check if a CIK has already been processed."""
        return cik in self.processed_ciks
        
    def get_disclosures(self, limit: Optional[int] = None, 
                        order_by_date: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of disclosures.
        
        Args:
            limit: Maximum number of disclosures to return (None for all)
            order_by_date: Whether to order by date (newest first)
            
        Returns:
            List of disclosure dicts
        """
        if order_by_date:
            sorted_disclosures = sorted(
                self.disclosures, 
                key=lambda x: x.get('filing_date', ''), 
                reverse=True
            )
        else:
            sorted_disclosures = self.disclosures.copy()
            
        if limit is not None:
            return sorted_disclosures[:limit]
            
        return sorted_disclosures
        
    def get_disclosure_count(self) -> int:
        """Get total number of disclosures."""
        return len(self.disclosures)
        
    def clear(self) -> bool:
        """Clear all disclosures (for testing)."""
        self.disclosures = []
        self.processed_ciks = set()
        self.processed_urls = set()
        return self.save_data()
        
    def track_filing_without_saving(self, filing: Filing) -> None:
        """
        Register a filing as processed without saving it as a disclosure.
        Useful for tracking filings that don't contain cybersecurity disclosures.
        
        Args:
            filing: Filing to track
        """
        self.processed_urls.add(filing.filing_href)
        logger.debug(f"Marked filing as processed (without saving): {filing.filing_href}") 
