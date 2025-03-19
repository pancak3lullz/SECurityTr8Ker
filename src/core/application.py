import time
import asyncio
from typing import List, Dict, Any, Optional, Set, Callable
from datetime import datetime
from src.models.filing import Filing
from src.api.sec_api import SECApiClient
from src.parsers.section_parser import SectionParser
from src.analyzers.disclosure_analyzer import DisclosureAnalyzer
from src.core.storage_service import StorageService
from src.core.scheduler import SECScheduler
from src.notifiers.notification_service import NotificationService, create_notification_service
from src.notifiers.status_notifier import StatusNotifier
from src.utils.logger import get_logger
from src.config import DISCLOSURES_FILE, REQUEST_INTERVAL, MAX_CONCURRENT_REQUESTS, MAX_RETRIES

logger = get_logger(__name__)

class SECurityTr8Ker:
    """
    Main application class for SECurityTr8Ker.
    Orchestrates the entire workflow of fetching, analyzing, and notifying.
    """
    
    def __init__(self, 
                 storage_file: str = DISCLOSURES_FILE,
                 check_interval: int = 600,
                 cache_dir: str = './cache',
                 business_hours_only: bool = True):
        """
        Initialize the application.
        
        Args:
            storage_file: Path to disclosure storage file
            check_interval: Interval in seconds between checks
            cache_dir: Directory for caching requests
            business_hours_only: Only check filings during SEC business hours
        """
        self.storage_file = storage_file
        self.cache_dir = cache_dir
        self.check_interval = check_interval
        self.business_hours_only = business_hours_only
        self.running = False
        
        logger.info("Initializing SECurityTr8Ker application")
        
        # Configuration
        self.last_check_time = 0
        
        # Initialize components
        self.sec_client = SECApiClient(
            cache_dir=cache_dir,
            request_interval=REQUEST_INTERVAL,
            max_retries=MAX_RETRIES
        )
        self.section_parser = SectionParser()
        self.disclosure_analyzer = DisclosureAnalyzer(self.section_parser)
        self.storage_service = StorageService(storage_file)
        self.notification_service = create_notification_service()
        
        # For rate limiting
        self.max_concurrent_requests = MAX_CONCURRENT_REQUESTS
        
        # Initialize status notifier for SEC business hours
        self.status_notifier = StatusNotifier(self.notification_service)
        
        # Get Twitter bio update function if available
        self.twitter_bio_updater = self._get_twitter_bio_updater()
        
        # Initialize SEC scheduler if using business hours
        if business_hours_only:
            self.scheduler = SECScheduler(
                operation_callback=self._check_filings,
                open_notification_callback=None,
                close_notification_callback=None,
                bio_update_callback=self.twitter_bio_updater
            )
        else:
            self.scheduler = None
        
        # Statistics
        self.stats = {
            'filings_processed': 0,
            'disclosures_found': 0,
            'notifications_sent': 0,
            'start_time': datetime.now().isoformat(),
            'last_check_time': None,
            'business_hours_only': business_hours_only
        }
        
        logger.info("SECurityTr8Ker application initialized")
        logger.info(f"Active notification channels: {', '.join(self.notification_service.active_channels)}")
        logger.info(f"Business hours mode: {'Enabled' if business_hours_only else 'Disabled'}")
        if self.twitter_bio_updater:
            logger.info("Twitter bio updater available")
        else:
            logger.info("Twitter bio updater not available")
    
    def _get_twitter_bio_updater(self) -> Optional[Callable]:
        """Get Twitter bio update function if available."""
        # Check if Twitter notifier is available
        for name, channel in self.notification_service.channels.items():
            if name == "twitter" and hasattr(channel, "update_profile_bio"):
                # Return the update_profile_bio method
                return channel.update_profile_bio
        
        return None
        
    def start(self):
        """Start the monitoring loop."""
        if self.running:
            logger.warning("SECurityTr8Ker is already running")
            return
            
        self.running = True
        logger.info("SECurityTr8Ker starting up...")
        
        # We're removing the Twitter bio update at startup to avoid hitting rate limits
        
        try:
            if self.business_hours_only and self.scheduler:
                # Run with business hours scheduler
                logger.info("Starting in business hours mode")
                
                # Log current status
                if self.scheduler.is_business_hours():
                    logger.info("Currently within SEC business hours")
                else:
                    status = self.scheduler.get_next_business_hours()
                    logger.info(status["message"])
                
                # Start scheduler
                self.scheduler.start()
            else:
                # Run continuously
                logger.info("Starting in continuous mode (runs 24/7)")
                self._monitoring_loop()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            logger.info("SECurityTr8Ker shutdown complete")
            
    def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        
        if self.scheduler:
            self.scheduler.stop()
            
        logger.info("SECurityTr8Ker shutting down...")
        
    def _monitoring_loop(self):
        """Main monitoring loop, runs continuously."""
        while self.running:
            try:
                self._check_filings()
                
                # Sleep until next check time
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    async def _process_filing_async(self, filing: Filing) -> Optional[Filing]:
        """
        Process a single filing asynchronously.
        
        Args:
            filing: Filing to process
            
        Returns:
            Filing if it contains a disclosure, None otherwise
        """
        try:
            # Skip if already processed
            if self.storage_service.has_processed_url(filing.filing_href):
                logger.debug(f"Skipping already processed filing: {filing.filing_href}")
                return None
                
            # Get ticker symbol
            try:
                filing.ticker_symbol = await asyncio.to_thread(
                    self.sec_client.get_ticker_symbol, filing.cik
                )
            except Exception as e:
                logger.warning(f"Failed to get ticker symbol for {filing.cik}: {e}")
                # Continue processing even without ticker symbol
                
            # Get document content
            try:
                html_content = await asyncio.to_thread(
                    self.sec_client.get_document_content, filing.filing_href
                )
                
                if not html_content:
                    logger.warning(f"Failed to fetch content for {filing.filing_href}")
                    
                    # Still track this URL as processed to avoid reprocessing
                    self.storage_service.track_filing_without_saving(filing)
                    return None
            except Exception as e:
                logger.warning(f"Error fetching content for {filing.filing_href}: {e}")
                
                # Still track this URL as processed to avoid reprocessing
                self.storage_service.track_filing_without_saving(filing)
                return None
                
            # Analyze for disclosures
            has_disclosure, matching_terms, contexts = self.disclosure_analyzer.analyze_filing(
                filing, html_content
            )
            
            if has_disclosure:
                # Update filing with results
                filing.matching_terms = matching_terms
                filing.contexts = contexts
                
                return filing
            else:
                # Track filings without disclosures so we don't reprocess them
                self.storage_service.track_filing_without_saving(filing)
                
            return None
            
        except Exception as e:
            logger.error(f"Error processing filing {filing.filing_href}: {e}")
            
            # Track this URL as processed to avoid reprocessing
            try:
                self.storage_service.track_filing_without_saving(filing)
            except Exception as e2:
                logger.error(f"Failed to track filing as processed: {e2}")
                
            return None
    
    async def _check_filings_async(self):
        """Check filings asynchronously for better performance."""
        # Fetch filings from RSS feed
        logger.info("Fetching SEC RSS feed for 8-K filings...")
        filings = self.sec_client.fetch_rss_feed()
        
        if not filings:
            logger.warning("No filings found in RSS feed")
            # Update Twitter bio even if no new filings were found
            self._update_twitter_bio_after_batch(0, 0)
            return
            
        # Count how many new filings we're actually processing
        new_filings_count = 0
        for filing in filings:
            if not self.storage_service.has_processed_url(filing.filing_href):
                new_filings_count += 1
        
        logger.info(f"Found {len(filings)} filings, {new_filings_count} are new and need processing")
        
        # If all filings were already processed, skip analysis
        if new_filings_count == 0:
            logger.info("All filings have been processed previously, skipping analysis")
            self._update_twitter_bio_after_batch(len(filings), 0)
            return
        
        self.stats['filings_processed'] += new_filings_count
        logger.info(f"Found {len(filings)} filings to inspect")
        logger.info("Inspecting documents for cybersecurity disclosures...")
        
        # Process filings with better concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def process_with_semaphore(filing):
            async with semaphore:
                return await self._process_filing_async(filing)
        
        # Process filings with controlled concurrency
        tasks = [process_with_semaphore(filing) for filing in filings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        disclosures = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception during filing processing: {result}")
            elif result is not None:
                disclosures.append(result)
        
        # Process disclosures
        if disclosures:
            logger.info(f"Found {len(disclosures)} new cybersecurity disclosure(s)")
            self.stats['disclosures_found'] += len(disclosures)
            
            for filing in disclosures:
                # Add to storage
                added = self.storage_service.add_disclosure(filing)
                
                if added:
                    # Send notifications
                    notification_results = self.notification_service.notify_all(filing)
                    
                    # Count successful notifications
                    successful_notifications = sum(1 for success in notification_results.values() if success)
                    self.stats['notifications_sent'] += successful_notifications
        else:
            logger.info("No new cybersecurity disclosures found in this batch")
        
        # Update Twitter bio after batch processing with the count of filings inspected
        self._update_twitter_bio_after_batch(len(filings), new_filings_count)
    
    def _update_twitter_bio_after_batch(self, filings_count: int, new_filings_count: int = None):
        """
        Update Twitter bio after a batch has been processed.
        
        Args:
            filings_count: Total number of filings in the RSS feed
            new_filings_count: Number of new filings processed (default: same as filings_count)
        """
        if not self.twitter_bio_updater:
            return
            
        try:
            now = datetime.now()
            
            # Get SEC status if using business hours mode
            sec_status = ""
            if self.business_hours_only and self.scheduler:
                is_business_hours = self.scheduler.is_business_hours()
                sec_status = "SEC is OPEN. " if is_business_hours else "SEC is CLOSED. "
                logger.info(f"Current SEC status for bio update: {sec_status.strip()}")
            
            # If new_filings_count wasn't provided, assume it's the same as filings_count
            if new_filings_count is None:
                new_filings_count = filings_count
            
            # We don't need batch info anymore as requested by the user
            # Just pass the SEC status to the Twitter bio updater
            success = self.twitter_bio_updater(now, additional_info=sec_status)
            
            if success:
                logger.info(f"Updated Twitter bio after processing batch ({new_filings_count} new of {filings_count} total filings)")
            else:
                logger.error("Failed to update Twitter bio after batch processing")
        except Exception as e:
            logger.error(f"Error updating Twitter bio after batch: {e}")
    
    def _check_filings(self):
        """Check filings for disclosures."""
        try:
            # Run async processing
            asyncio.run(self._check_filings_async())
        except Exception as e:
            logger.error(f"Error checking filings: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        # Update with the latest counts
        self.stats.update({
            'filings_processed': self.stats['filings_processed'],
            'disclosures_found': self.stats['disclosures_found'],
            'notifications_sent': self.stats['notifications_sent'],
            'uptime_seconds': (datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds(),
            'total_disclosures': self.storage_service.get_disclosure_count(),
            'api_client_stats': self.sec_client.get_stats()
        })
        
        # Add scheduler info if available
        if self.scheduler:
            self.stats['sec_status'] = self.scheduler.get_status()
        
        return self.stats 