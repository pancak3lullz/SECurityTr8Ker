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
            "risk factors",
            "not experienced any",
            "no cybersecurity incidents",
            "has not had",
            "has not experienced",
            "hypothetically",
            "future incident",
            "potential incident",
            "in the event of",
            "could result in"
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
        logger.info(f"Analyzing filing: {filing.company_name} ({filing.form_type})")
        
        # Only process 8-K forms
        if filing.form_type not in ['8-K', '8-K/A']:
            logger.debug(f"Skipping non-8K filing: {filing.form_type}")
            return False, [], []
            
        # Parse document sections
        soup = BeautifulSoup(html_content, 'html.parser')
        document_text = soup.get_text(separator=' ')
        filing.raw_content = document_text
        
        # Extract all sections
        sections = self.section_parser.extract_sections(document_text)
        filing.sections = sections
        
        # First check for Item 1.05 disclosures
        item_105_disclosure = self._check_item_105_disclosure(filing)
        if item_105_disclosure[0]:
            logger.info(f"Found Item 1.05 disclosure in {filing.company_name}")
            # Keep track of matching terms and contexts
            terms = item_105_disclosure[1]
            contexts = item_105_disclosure[2]
            return True, terms, contexts
            
        # Then check if Item 8.01 contains cybersecurity terms
        item_801_disclosure = self._check_item_801_disclosure(filing)
        if item_801_disclosure[0]:
            logger.info(f"Found cybersecurity disclosure in Item 8.01 of {filing.company_name}")
            # Keep track of matching terms and contexts
            terms = item_801_disclosure[1]
            contexts = item_801_disclosure[2]
            return True, terms, contexts
            
        # No disclosure found
        return False, [], []
    
    def _check_item_105_disclosure(self, filing: Filing) -> Tuple[bool, List[str], List[str]]:
        """
        Check if a filing contains an Item 1.05 disclosure.
        
        Args:
            filing: Filing object to check
            
        Returns:
            Tuple of (has_disclosure, matching_terms, contexts)
        """
        matching_terms = []
        contexts = []
        
        # Check if we have an Item 1.05 section
        found_item_105 = False
        item_105_section = None
        
        for name, section in filing.sections.items():
            if "item 1.05" in name.lower():
                found_item_105 = True
                item_105_section = section
                break
        
        # If we found Item 1.05 section, check for cybersecurity terms
        if found_item_105 and item_105_section:
            # If Item 1.05 exists, confirm it's not empty or just refers to another section
            section_text = item_105_section.content.lower()
            
            # Check if section is substantial (not just a reference)
            if len(section_text.strip()) < 30:
                # Very short section might be just a reference
                references = ["see item", "incorporated by reference", "not applicable"]
                if any(ref in section_text for ref in references):
                    logger.debug(f"Item 1.05 section appears to be just a reference")
                    return False, [], []
            
            # Match Item 1.05 term itself as a matching term
            matching_terms.append("Item 1.05")
            contexts.append(self._get_context(section_text, "item 1.05", 100))
            
            # Check if the section actually discusses a cybersecurity incident
            # by looking for cybersecurity terms
            for i, pattern in enumerate(self.cybersecurity_patterns):
                matches = pattern.finditer(section_text)
                for match in matches:
                    term = self.cybersecurity_terms[i]
                    
                    # Get context around match
                    context = self._get_context(section_text, match.group(), 100)
                    
                    # Check if context contains false positive indicators
                    if not self._is_false_positive(context):
                        matching_terms.append(term)
                        contexts.append(context)
                    else:
                        logger.debug(f"False positive match '{term}' in context: {context}")
            
            # If we have Item 1.05 and any cybersecurity terms, it's a disclosure
            if len(matching_terms) > 1:  # More than just "Item 1.05" itself
                return True, matching_terms, contexts
                
            # Even if no cybersecurity terms, having Item 1.05 is significant
            # But let's do a final check to make sure it's not a false positive
            if not self._is_false_positive(section_text):
                return True, matching_terms, contexts
        
        # Check entire document for explicit Item 1.05 mentions
        if not found_item_105:
            document_text = filing.raw_content.lower() if filing.raw_content else ""
            for pattern in self.item_105_patterns:
                matches = pattern.finditer(document_text)
                for match in matches:
                    # Get context around match
                    context = self._get_context(document_text, match.group(), 100)
                    
                    # Check if context contains false positive indicators
                    if not self._is_false_positive(context):
                        return True, [match.group()], [context]
        
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
        
        # Check for cybersecurity terms in the section
        for i, pattern in enumerate(self.cybersecurity_patterns):
            matches = pattern.finditer(section_text)
            for match in matches:
                term = self.cybersecurity_terms[i]
                
                # Get context around match
                context = self._get_context(section_text, match.group(), 100)
                
                # Check if context contains false positive indicators
                if not self._is_false_positive(context):
                    matching_terms.append(term)
                    contexts.append(context)
        
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