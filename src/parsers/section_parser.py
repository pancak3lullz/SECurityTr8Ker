import re
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
from src.models.filing import FilingSection
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SectionParser:
    """
    A robust parser for SEC filing sections using state machine approach.
    """
    
    # Common patterns for section headers in SEC filings
    SECTION_PATTERNS = [
        # Standard item pattern (e.g., "Item 1.05 Material Cybersecurity Incidents")
        r'(Item\s+\d+\.\d+)[^a-zA-Z0-9]*([^\n\r]*)',
        # Alternative format (e.g., "ITEM 1.05")
        r'(ITEM\s+\d+\.\d+)[^a-zA-Z0-9]*([^\n\r]*)',
        # Format with parentheses (e.g., "Item 1.05) Material Cybersecurity Incidents")
        r'(Item\s+\d+\.\d+\))[^a-zA-Z0-9]*([^\n\r]*)',
    ]
    
    # Known section names to help with validation
    KNOWN_SECTIONS = {
        "item 1.05": "Material Cybersecurity Incidents",
        "item 8.01": "Other Events",
        # Add more known sections as needed
    }
    
    # Patterns to identify forward-looking statements sections
    FORWARD_LOOKING_PATTERNS = [
        r'(Forward-Looking\s+Statements?).*?(?=Item\s+\d+\.\d+|$)',
        r'(FORWARD-LOOKING\s+STATEMENTS?).*?(?=ITEM\s+\d+\.\d+|$)',
        r'(Cautionary\s+Statement\s+Regarding\s+Forward-Looking.*?)(?=Item\s+\d+\.\d+|$)',
        r'(CAUTIONARY\s+STATEMENT\s+REGARDING\s+FORWARD-LOOKING.*?)(?=ITEM\s+\d+\.\d+|$)'
    ]
    
    def __init__(self):
        # Compile regex patterns for performance
        self.section_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                for pattern in self.SECTION_PATTERNS]
        
        # Compile forward-looking statements patterns
        self.forward_looking_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL)
                                        for pattern in self.FORWARD_LOOKING_PATTERNS]
                                
    def clean_text(self, text: str) -> str:
        """
        Clean and standardize text for processing.
        """
        # Remove HTML/XML tags
        text = re.sub(r'(<[^>]+>)|(&#\d{1,4};)', ' ', text)
        # Standardize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_sections(self, document_text: str) -> Dict[str, FilingSection]:
        """
        Extract all sections from document text using a state machine approach.
        """
        # First clean the text
        clean_text = self.clean_text(document_text)
        
        # Identify forward-looking statements sections to exclude them
        forward_looking_sections = self._identify_forward_looking_sections(clean_text)
        logger.debug(f"Found {len(forward_looking_sections)} forward-looking statement sections")
        
        # Find all potential section headers
        section_candidates = []
        for pattern in self.section_patterns:
            for match in pattern.finditer(clean_text):
                section_name = match.group(1).strip()
                section_title = match.group(2).strip() if len(match.groups()) > 1 else ""
                position = match.start()
                
                # Skip if this position is within a forward-looking statement section
                if any(start <= position <= end for start, end in forward_looking_sections):
                    logger.debug(f"Skipping section {section_name} found in forward-looking statements")
                    continue
                    
                section_candidates.append((section_name, section_title, position))
        
        # Sort by position in document
        section_candidates.sort(key=lambda x: x[2])
        
        if not section_candidates:
            logger.warning("No sections found in document")
            return {}
            
        # Build sections dict
        sections = {}
        for i, (section_name, section_title, start_pos) in enumerate(section_candidates):
            # Determine end position (start of next section or end of document)
            end_pos = section_candidates[i+1][2] if i < len(section_candidates) - 1 else len(clean_text)
            
            # Skip if this section is entirely within a forward-looking statement
            if any(start <= start_pos and end >= end_pos for start, end in forward_looking_sections):
                logger.debug(f"Skipping section {section_name} contained within forward-looking statements")
                continue
                
            # Check if this section contains forward-looking statements
            section_contains_fls = False
            for fls_start, fls_end in forward_looking_sections:
                # If the forward-looking statement starts within this section
                if start_pos <= fls_start < end_pos:
                    # Adjust the section end to exclude the forward-looking statement
                    end_pos = fls_start
                    section_contains_fls = True
                    logger.debug(f"Adjusted section {section_name} to exclude forward-looking statements")
                    
            # Extract content
            content = clean_text[start_pos:end_pos].strip()
            
            # Normalize section name for consistent keys
            normalized_name = section_name.lower()
            
            # Create section object
            section = FilingSection(
                name=normalized_name,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos
            )
            
            # Validate section (basic check)
            if self._validate_section(normalized_name, section_title, content):
                sections[normalized_name] = section
            else:
                logger.debug(f"Skipping invalid section: {normalized_name}")
        
        logger.info(f"Extracted {len(sections)} valid sections from document")
        return sections
    
    def _identify_forward_looking_sections(self, text: str) -> List[Tuple[int, int]]:
        """
        Identify the start and end positions of forward-looking statements sections.
        
        Args:
            text: The document text
            
        Returns:
            List of tuples (start_pos, end_pos) for each forward-looking section
        """
        sections = []
        
        for pattern in self.forward_looking_patterns:
            for match in pattern.finditer(text):
                sections.append((match.start(), match.end()))
                
        return sections
    
    def _validate_section(self, section_name: str, section_title: str, content: str) -> bool:
        """
        Validate a section to ensure it's a real section and not a false positive.
        """
        # Check if section name is one of our known sections
        if section_name in self.KNOWN_SECTIONS:
            # For known sections, optionally verify expected title
            expected_title = self.KNOWN_SECTIONS[section_name].lower()
            if expected_title in section_title.lower():
                return True
            # Still return true even if title doesn't match exactly
            return True
            
        # For unknown sections, must have reasonable content length
        if len(content) < 20:  # Too short to be a real section
            return False
            
        # Check for section number pattern (e.g., item X.XX)
        if not re.match(r'item\s+\d+\.\d+', section_name, re.IGNORECASE):
            return False
            
        return True
    
    def extract_item_section(self, document_text: str, item_number: str) -> Optional[FilingSection]:
        """
        Extract a specific item section from the document.
        
        Args:
            document_text: The document text to parse
            item_number: The specific item number to extract (e.g., "1.05" or "8.01")
            
        Returns:
            FilingSection if found, None otherwise
        """
        # Format item number pattern
        if not item_number.startswith("item "):
            item_number = f"item {item_number}"
            
        # Get all sections
        sections = self.extract_sections(document_text)
        
        # Look for exact match first
        for section_name, section in sections.items():
            if section_name.lower() == item_number.lower():
                return section
                
        # Look for partial match as fallback
        for section_name, section in sections.items():
            if item_number.lower() in section_name.lower():
                return section
                
        return None 
