import re
from typing import Dict, List, Tuple, Optional, Set
from bs4 import BeautifulSoup
from src.models.filing import Filing, FilingSection
from src.parsers.section_parser import SectionParser
from src.utils.logger import get_logger
from src.config import SEARCH_TERMS

logger = get_logger(__name__)

class DisclosureAnalyzer:
    """
    Analyzer for detecting cybersecurity incidents in SEC filings.
    """
    
    def __init__(self, section_parser: Optional[SectionParser] = None):
        """
        Initialize the disclosure analyzer.
        
        Args:
            section_parser: SectionParser instance to use for parsing sections
        """
        self.section_parser = section_parser or SectionParser()
        
        # Load search terms
        self.item_105_terms = SEARCH_TERMS['item_105']
        self.cybersecurity_terms = SEARCH_TERMS['cybersecurity']
        
        # Compile regex patterns for performance
        self.item_105_patterns = [
            re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for term in self.item_105_terms
        ]
        
        self.cybersecurity_patterns = [
            re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for term in self.cybersecurity_terms
        ]
        
        # Known false positive contexts (segments that might contain
        # cybersecurity terms but are not indicative of incidents)
        self.false_positive_contexts = [
            "forward-looking statements",
            "forward looking statements",
            "risk factors",
            "not experienced any",
            "no cybersecurity incidents",
            "has not had",
            "has not experienced",
            "hypothetically",
            "future incident",
            "potential incident",
            "in the event of",
            "could result in",
            "would result in",
            "may result in",
            "might result in",
            "potentially",
            "uncertainties",
            "potential future",
            "ability to prevent",
            "ability to contain",
            "risks related to",
            "could be subject to",
            "may be subject to",
            "can be no assurance",
            "cautionary statement"
        ]
        
        # Compile false positive patterns
        self.false_positive_patterns = [
            re.compile(re.escape(context), re.IGNORECASE)
            for context in self.false_positive_contexts
        ]
        
    def analyze_filing(self, filing: Filing, html_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Analyze a filing for cybersecurity incident disclosures.
        
        Args:
            filing: Filing object to analyze
            html_content: HTML content of the filing
            
        Returns:
            Tuple of (has_disclosure, matching_terms, contexts)
        """
        logger.info(f"Analyzing filing: {filing.company_name} ({filing.form_type}) URL: {filing.filing_href}")
        
        # Only process 8-K forms
        if filing.form_type not in ['8-K', '8-K/A']:
            logger.debug(f"Skipping non-8K filing: {filing.form_type} for {filing.filing_href}")
            return False, [], []
            
        # Parse document sections
        soup = BeautifulSoup(html_content, 'html.parser')
        document_text = soup.get_text(separator=' ')
        filing.raw_content = document_text
        
        # Extract all sections
        logger.debug(f"Extracting sections for {filing.filing_href}")
        sections = self.section_parser.extract_sections(document_text)
        filing.sections = sections
        logger.debug(f"Found sections: {list(sections.keys())} for {filing.filing_href}")
        
        # Rule 1: Always alert if a valid Item 1.05 section exists
        item_105_section = None
        for name, section in filing.sections.items():
            if "item 1.05" in name.lower():
                item_105_section = section
                logger.info(f"Found potential Item 1.05 section for {filing.filing_href}")
                break
        
        if item_105_section:
            section_text = item_105_section.content.lower()
            is_short_ref = False
            if len(section_text.strip()) < 50: # Use a slightly larger threshold
                references = ["see item", "incorporated by reference", "not applicable", "previously disclosed"]
                if any(ref in section_text for ref in references):
                    is_short_ref = True
                    logger.info(f"Item 1.05 section appears to be a short reference for {filing.filing_href}")
                
            # If the section exists and is NOT just a short reference, and not clearly a false positive context
            if not is_short_ref and not self._is_false_positive(section_text):
                logger.info(f"Item 1.05 disclosure confirmed for {filing.filing_href}")
                context = self._get_context(document_text, item_105_section.content, 200) # Get context from full doc
                return True, ["Item 1.05"], [context]
            else:
                logger.info(f"Item 1.05 section found but dismissed (short ref: {is_short_ref}, FP check: {self._is_false_positive(section_text)}) for {filing.filing_href}")

        # Rule 2: If no Item 1.05 alert, check Item 8.01 for cybersecurity keywords
        logger.debug(f"Checking Item 8.01 for {filing.filing_href}")
        item_801_disclosure = self._check_item_801_disclosure(filing)
        if item_801_disclosure[0]:
            logger.info(f"Found cybersecurity disclosure in Item 8.01 of {filing.company_name} for {filing.filing_href}")
            return True, item_801_disclosure[1], item_801_disclosure[2]
            
        # No disclosure found based on rules
        logger.info(f"No cybersecurity disclosure found for {filing.filing_href}")
        return False, [], []
    
    def _check_item_105_disclosure(self, filing: Filing) -> Tuple[bool, List[str], List[str]]:
        """DEPRECATED - Logic moved to analyze_filing. Kept for potential future use or refactoring."""
        logger.warning("_check_item_105_disclosure is deprecated and should not be called directly.")
        return False, [], []
    
    def _check_item_801_disclosure(self, filing: Filing) -> Tuple[bool, List[str], List[str]]:
        """
        Check if a filing's Item 8.01 section contains cybersecurity disclosures.
        
        Args:
            filing: Filing object to check
            
        Returns:
            Tuple of (has_disclosure, matching_terms, contexts)
        """
        matching_terms = []
        contexts = []
        
        # Check if we have an Item 8.01 section
        item_801_section = None
        for name, section in filing.sections.items():
            if "item 8.01" in name.lower():
                item_801_section = section
                break
        
        if item_801_section is None:
            return False, [], []
            
        # Check for cybersecurity terms ONLY within Item 8.01 section
        section_text = item_801_section.content.lower()
        
        # First check if this section appears to be a forward-looking statement
        # (in case our section parser didn't catch it)
        forward_looking_indicators = [
            "forward-looking", "forward looking", "future event", "future result", 
            "potential risk", "uncertainties", "cautionary statement"
        ]
        if any(indicator in section_text.lower() for indicator in forward_looking_indicators):
            logger.debug("Item 8.01 section appears to contain forward-looking statements; skipping")
            return False, [], []
        
        # Check for cybersecurity terms in the section
        for i, pattern in enumerate(self.cybersecurity_patterns):
            matches = pattern.finditer(section_text)
            for match in matches:
                term = self.cybersecurity_terms[i]
                
                # Get context around match
                context = self._get_context(section_text, match.group(), 200)  # Increased context size
                
                # Check if context contains false positive indicators
                if not self._is_false_positive(context):
                    # Double-check for forward-looking language near the match
                    if not any(fw_term in context.lower() for fw_term in forward_looking_indicators):
                        matching_terms.append(term)
                        contexts.append(context)
                    else:
                        logger.debug(f"Skipping match '{term}' due to nearby forward-looking language")
                else:
                    logger.debug(f"False positive match '{term}' in context: {context[:50]}...")
        
        # If we found matching terms in Item 8.01, it's a disclosure
        if matching_terms:
            return True, matching_terms, contexts
            
        return False, [], []
    
    def _get_context(self, text: str, match_text: str, context_size: int = 100) -> str:
        """Get context around a match in text."""
        match_pos = text.find(match_text.lower())
        if match_pos >= 0:
            start = max(0, match_pos - context_size)
            end = min(len(text), match_pos + len(match_text) + context_size)
            return text[start:end]
        return ""
        
    def _is_false_positive(self, context: str) -> bool:
        """Check if a context is likely a false positive."""
        # Check for false positive indicators
        for pattern in self.false_positive_patterns:
            if pattern.search(context):
                return True
                
        # Check if the match is within a forward-looking statements section
        forward_looking_indicators = [
            "forward-looking statement",
            "forward looking statement",
            "forward-looking information",
            "such statements involve risks",
            "risk and uncertainties",
            "future events",
            "future performance",
            "future results",
            "future financial"
        ]
        
        # Check for forward-looking statement section indicators
        for indicator in forward_looking_indicators:
            if indicator.lower() in context.lower():
                logger.debug(f"Found forward-looking statement context: '{indicator}'")
                return True
        
        # Additional checks for negations before cybersecurity terms
        negations = ["not", "no", "none", "never", "without"]
        for negation in negations:
            # Look for patterns like "not experienced any cybersecurity incident"
            for term in self.cybersecurity_terms:
                neg_pattern = re.compile(
                    r'\b' + re.escape(negation) + r'\b.{0,30}\b' + re.escape(term) + r'\b', 
                    re.IGNORECASE
                )
                if neg_pattern.search(context):
                    return True
                    
        return False 
