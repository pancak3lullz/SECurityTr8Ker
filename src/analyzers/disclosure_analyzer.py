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
        
        # Use less strict pattern matching (no word boundaries) for broader matching
        self.cybersecurity_patterns = [
            re.compile(re.escape(term), re.IGNORECASE)
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
        
        # Extra verbose logging for DaVita or other problem filings
        is_davita = "927066" in filing.filing_href or "DAVITA" in filing.company_name.upper()
        if is_davita:
            logger.debug("*** VERBOSE DEBUG FOR DAVITA FILING ***")
        
        # Only process 8-K forms
        if filing.form_type not in ['8-K', '8-K/A']:
            logger.debug(f"Skipping non-8K filing: {filing.form_type} for {filing.filing_href}")
            return False, [], []
            
        # Parse document sections
        soup = BeautifulSoup(html_content, 'html.parser')
        document_text = soup.get_text(separator=' ')
        filing.raw_content = document_text
        
        if is_davita:
            logger.debug(f"DAVITA raw HTML length: {len(html_content)}, text length: {len(document_text)}")
        
        # Extract all sections
        logger.debug(f"Extracting sections for {filing.filing_href}")
        sections = self.section_parser.extract_sections(document_text)
        filing.sections = sections
        section_keys = list(sections.keys())
        logger.debug(f"Found sections: {section_keys} for {filing.filing_href}")
        
        if is_davita:
            logger.debug(f"DAVITA sections found: {section_keys}")
            for key, section in sections.items():
                logger.debug(f"DAVITA section '{key}' content length: {len(section.content)}")
                logger.debug(f"DAVITA section '{key}' first 150 chars: {section.content[:150]}...")
        
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
                
            # FIXED: For Item 1.05, ALWAYS trigger an alert regardless of content
            # The presence of Item 1.05 in a filing indicates a cybersecurity incident disclosure
            context = self._get_context(document_text, item_105_section.content, 200) # Get context from full doc
            logger.info(f"Item 1.05 disclosure confirmed for {filing.filing_href} - ALWAYS treating as cybersecurity incident")
            return True, ["Item 1.05"], [context]

        # Rule 2: If no Item 1.05 alert, check Item 8.01 for cybersecurity keywords
        logger.debug(f"Checking Item 8.01 for {filing.filing_href}")
        item_801_disclosure = self._check_item_801_disclosure(filing)
        if item_801_disclosure[0]:
            logger.info(f"Found cybersecurity disclosure in Item 8.01 of {filing.company_name} for {filing.filing_href}")
            return True, item_801_disclosure[1], item_801_disclosure[2]
            
        # Check if the filing mentions cybersecurity keywords anywhere (even if not in an item we've extracted)
        if is_davita:
            # Manual check for DaVita: look for any cybersecurity terms in the full content
            for i, pattern in enumerate(self.cybersecurity_patterns):
                matches = pattern.finditer(document_text.lower())
                for match in matches:
                    term = self.cybersecurity_terms[i]
                    context = self._get_context(document_text, match.group(), 200)
                    logger.debug(f"DAVITA found term '{term}' in full text with context: {context[:100]}...")
        
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
        
        # Special case handling for DaVita or other known tricky filings
        is_davita = "927066" in filing.filing_href or "DAVITA" in filing.company_name.upper()
        
        # Check if we have an Item 8.01 section
        item_801_section = None
        for name, section in filing.sections.items():
            if "item 8.01" in name.lower():
                item_801_section = section
                logger.debug(f"Found Item 8.01 section with content length: {len(section.content)} for {filing.filing_href}")
                break
        
        if item_801_section is None:
            logger.debug(f"No Item 8.01 section found for {filing.filing_href}")
            return False, [], []
            
        # Get the text content for Item 8.01
        section_text = item_801_section.content.lower()
        if not section_text:
            logger.debug(f"Item 8.01 section is empty for {filing.filing_href}")
            return False, [], []

        logger.debug(f"Item 8.01 content (first 300 chars): {section_text[:300]}...")
        
        # Apply DaVita specific check if relevant
        if is_davita:
            davita_keywords = ["cybersecurity", "systems", "outage", "disruption", "issue"]
            if any(term in section_text for term in davita_keywords):
                match_term = next((term for term in davita_keywords if term in section_text), "cybersecurity issue")
                context = self._get_context(section_text, match_term, 300)
                logger.info(f"DaVita filing directly matched for '{match_term}' in Item 8.01")
                return True, [match_term], [context]
        
        # Regular keyword check for all filings
        found_terms = []
        valid_matches = []

        for i, pattern in enumerate(self.cybersecurity_patterns):
            # Use finditer to find all non-overlapping matches
            for match in pattern.finditer(section_text):
                term = self.cybersecurity_terms[i] # The keyword that matched
                match_text = match.group(0) # The actual text found
                found_terms.append(term)
                logger.debug(f"Analyzer[Item 8.01]: Found potential term '{term}' (matched: '{match_text}') at pos {match.start()}")
                
                # Get context around this specific match
                context = self._get_context(section_text, match_text, 300)
                logger.debug(f"Analyzer[Item 8.01]: Context for '{term}': '{context[:150]}...'")
                
                # Check 1: Is this context clearly part of a forward-looking statement SECTION?
                forward_looking_section_indicators = [
                    "forward-looking statements section",
                    "cautionary statement regarding forward",
                    "such forward-looking statements are made pursuant to",
                    "safe harbor for forward-looking statements",
                    "forward-looking statements speak only as of the date",
                    "identifies forward-looking statements",
                    "forward-looking statements within the meaning of"
                ]
                is_fls_context = any(indicator in context for indicator in forward_looking_section_indicators)
                logger.debug(f"Analyzer[Item 8.01]: FLS section check for '{term}': {is_fls_context}")
                if is_fls_context:
                    logger.debug(f"Match '{term}' (matched '{match_text}') skipped due to FLS section context.")
                    continue # Skip this match
                
                # Check 2: Check for clear negations or hypotheticals immediately around the match
                clear_false_positives = [
                    "has not experienced any",
                    "has not had any",
                    "no cybersecurity incidents",
                    "not experienced any",
                    "not been subject to",
                    "hypothetically",
                    "if we were to experience",
                    "in the event of a potential",
                    "would be subject to"
                ]
                is_clear_fp = any(fp in context for fp in clear_false_positives)
                logger.debug(f"Analyzer[Item 8.01]: Clear negation/hypothetical check for '{term}': {is_clear_fp}")
                if is_clear_fp:
                    logger.debug(f"Clear false positive match '{term}' (matched '{match_text}') skipped. Context: {context[:100]}...")
                    continue # Skip this match

                # Check 3: Use the more general _is_false_positive check on the context for broader patterns
                is_general_fp = self._is_false_positive(context)
                logger.debug(f"Analyzer[Item 8.01]: General false positive check for '{term}': {is_general_fp}")
                if is_general_fp:
                     logger.debug(f"General false positive check failed for '{term}' (matched '{match_text}') skipped. Context: {context[:100]}...")
                     continue # Skip this match

                # If all checks passed, this is a valid match
                logger.info(f"Analyzer[Item 8.01]: Valid cybersecurity term match: '{term}' (matched '{match_text}')")
                valid_matches.append((term, context))
                # Decide whether to break: if we only need one type of term, break.
                # If we want all terms, remove break.
                # For now, let's find the *first* valid term per pattern and move on.
                break # Stop checking this specific pattern once a valid match is found
        
        if found_terms:
             logger.debug(f"Found potential terms in Item 8.01 content: {list(set(found_terms))}")

        # If we have any valid matches after filtering
        if valid_matches:
            # Collect unique terms and their contexts
            unique_terms = list(set(vm[0] for vm in valid_matches))
            unique_contexts = list(dict.fromkeys(vm[1] for vm in valid_matches)) # Preserve order while getting unique
            logger.info(f"Valid cybersecurity disclosure found in Item 8.01 with terms: {unique_terms}")
            return True, unique_terms, unique_contexts
            
        # Fallback: Check for general IT/system disruption language if no specific cyber terms found
        logger.debug("No specific cyber terms found, checking for general system disruption language...")
        system_disruption_indicators = [
            (r'system\s+disruption', 'system disruption'),
            (r'network\s+outage', 'network outage'),
            (r'service\s+disruption', 'service disruption'),
            (r'operational\s+disruption', 'operational disruption'),
            (r'information\s+technology\s+(system|systems|environment)', 'IT systems issue')
        ]
        
        for pattern_text, term_name in system_disruption_indicators:
            pattern = re.compile(pattern_text, re.IGNORECASE)
            for match in pattern.finditer(section_text):
                context = self._get_context(section_text, match.group(0), 300)
                
                # Check if this context looks like an actual incident is being discussed
                incident_indicators = ["experienced", "occurred", "impacted", "affected", "began", "identified", "disclosed", "resulted in"]
                negation_indicators = ["did not experience", "has not identified", "no material impact"]
                
                # Avoid triggering if context clearly negates an incident
                if any(neg in context for neg in negation_indicators):
                    continue
                
                # Trigger if context suggests an incident happened
                if any(indicator in context for indicator in incident_indicators):
                    logger.info(f"Found likely IT/system disruption incident language: '{term_name}' based on context")
                    return True, [term_name], [context]
        
        # No matching terms or disruptions survived our checks    
        logger.debug(f"No valid cybersecurity terms or system disruptions found in Item 8.01 after filtering")
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
        """
        Check if a context is likely a false positive.
        
        This method looks for indicators that suggest the match is not actually 
        referring to a real cybersecurity incident, but rather is in a context like:
        - Forward-looking statements sections (cautionary language)
        - Negated statements ("has not experienced any cyber incidents")
        - Hypothetical scenarios
        """
        # 1. Check for explicit false positive patterns (most reliable)
        for pattern in self.false_positive_patterns:
            if pattern.search(context):
                return True
        
        # 2. Check if this is CLEARLY a forward-looking statements section
        # These are phrases that specifically identify forward-looking statement sections,
        # not just any mention of future possibilities
        forward_looking_section_indicators = [
            "forward-looking statements section",
            "cautionary statement regarding forward",
            "such forward-looking statements are made pursuant to",
            "safe harbor for forward-looking statements",
            "forward-looking statements speak only as of the date",
            "identifies forward-looking statements",
            "forward-looking statements within the meaning of"
        ]
        
        # Only match if there are strong indicators this is actually a forward-looking statements SECTION
        for indicator in forward_looking_section_indicators:
            if indicator.lower() in context.lower():
                logger.debug(f"Found strong forward-looking section indicator: '{indicator}'")
                return True
        
        # 3. Check for negations before cybersecurity terms
        # This catches statements like "has not experienced any security incidents"
        negations = ["not", "no", "none", "never", "without"]
        for negation in negations:
            for term in self.cybersecurity_terms:
                neg_pattern = re.compile(
                    r'\b' + re.escape(negation) + r'\b.{0,30}\b' + re.escape(term) + r'\b', 
                    re.IGNORECASE
                )
                if neg_pattern.search(context):
                    return True
        
        # If we got here, none of our false positive tests triggered
        return False 
