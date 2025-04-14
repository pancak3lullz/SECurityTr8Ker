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
        # Match "Item<space(s)>X.XX" possibly followed by ')'
        r'(Item\s+\d+\.\d+)\)?',
        # Match "ITEM<space(s)>X.XX" possibly followed by ')'
        r'(ITEM\s+\d+\.\d+)\)?',
    ]
    
    # Known section names to help with validation
    KNOWN_SECTIONS = {
        "item 1.05": "Material Cybersecurity Incidents",
        "item 8.01": "Other Events",
        "item 9.01": "Financial Statements and Exhibits",
        "item 7.01": "Regulation FD Disclosure",
        "item 2.02": "Results of Operations and Financial Condition",
        "item 5.02": "Departure of Directors or Certain Officers"
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
        Extract all sections from document text using a combination of
        HTML structure analysis and regex.
        """
        soup = BeautifulSoup(document_text, 'html.parser')

        section_candidates = []
        logger.debug("Scanning document for potential section headers using combined approach...")

        # --- Find candidates using common tags and patterns ---
        potential_header_tags = soup.find_all(['b', 'strong', 'p', 'div'])
        processed_starts = set() # Avoid duplicate matches from overlapping tags
        found_via_tag = False # Debug flag

        for tag_index, tag in enumerate(potential_header_tags):
            # Get text, replacing non-breaking spaces before cleaning further
            tag_text = tag.get_text(separator=' ').replace('\xa0', ' ').strip()
            if not tag_text:
                continue
            
            # DEBUG: Log tag text if it might contain an item header
            if 'item ' in tag_text.lower() and len(tag_text) < 100:
                logger.debug(f"Parser[TagCheck {tag_index}]: Checking tag text: '{tag_text}'")

            # Use regex on the tag's text content
            for pattern in self.section_patterns:
                match = pattern.search(tag_text)
                if match:
                    # Group 1 is the item identifier (e.g., "Item 8.01" or "Item 1.05)")
                    section_name = match.group(1).strip()
                    # DEBUG: Log if Item 8.01 is potentially found
                    if '8.01' in section_name:
                        logger.debug(f"Parser[TagMatch]: Potential Item 8.01 found via tag: '{tag_text}'")
                        found_via_tag = True
                        
                    section_title = "" # Title is no longer captured by regex
                    # The matched header is the whole match (group 0)
                    matched_header_text = match.group(0).strip()
                    
                    # Estimate position in the *original* document text if possible (can be fragile)
                    approx_pos = document_text.find(matched_header_text)
                    if approx_pos == -1:
                        # Fallback: find the tag's approximate start
                        approx_pos = document_text.find(str(tag))
                    if approx_pos == -1:
                        approx_pos = 0 # Default if we can't find it
                        
                    # Store candidate details including the tag's text
                    candidate_detail = {
                        "name": section_name,
                        "title": section_title,
                        "header_text": matched_header_text, # Text that matched regex
                        "approx_pos": approx_pos, # For initial rough sorting/deduplication
                        "found_by": "tag"
                    }
                    # Avoid adding essentially the same header match found nearby
                    is_duplicate = False
                    for existing in section_candidates:
                        if abs(existing["approx_pos"] - candidate_detail["approx_pos"]) < 50 and \
                           existing["name"] == candidate_detail["name"]:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        section_candidates.append(candidate_detail)
                        logger.debug(f"Found candidate via tag: {candidate_detail}")
                        break # Move to next tag once a pattern matches

        # --- Clean the full text ONCE for positioning and fallback regex --- 
        full_cleaned_text = self.clean_text(document_text)
        logger.debug(f"Parser: Full cleaned text length: {len(full_cleaned_text)}")
        
        # --- Refine positions and add candidates from fallback regex --- 
        final_candidates = []
        processed_clean_starts = set()
        
        # Update positions for tag-found candidates using cleaned text
        for cand in section_candidates:
             if cand["found_by"] == "tag":
                 cleaned_header = self.clean_text(cand["header_text"])
                 pos_in_cleaned = full_cleaned_text.find(cleaned_header)
                 if pos_in_cleaned != -1:
                     cand["position"] = pos_in_cleaned
                     cand["cleaned_header"] = cleaned_header
                     final_candidates.append(cand)
                     processed_clean_starts.add(pos_in_cleaned)
                 else:
                     logger.warning(f"Could not find cleaned header '{cleaned_header}' in cleaned text for tag-found candidate: {cand['name']}")
        
        # Add candidates from regex on full cleaned text (if not already found via tags)
        logger.debug("Applying fallback regex search on fully cleaned text...")
        found_via_fallback = False # Debug flag
        for pattern in self.section_patterns:
            for match in pattern.finditer(full_cleaned_text):
                position = match.start()
                if position not in processed_clean_starts:
                    # Group 1 is the item identifier
                    section_name = match.group(1).strip()
                    # DEBUG: Log if Item 8.01 is potentially found via fallback
                    if '8.01' in section_name:
                        logger.debug(f"Parser[FallbackMatch]: Potential Item 8.01 found via fallback regex at pos {position}: Header='{match.group(0).strip()}'")
                        found_via_fallback = True
                        
                    section_title = "" # Title not captured
                    # The matched header is the whole match (group 0)
                    cleaned_header = match.group(0).strip() 
                    
                    final_candidates.append({
                        "name": section_name,
                        "title": section_title,
                        "position": position,
                        "cleaned_header": cleaned_header,
                        "found_by": "regex_fallback"
                    })
                    processed_clean_starts.add(position)
                    # Removed detailed log here for brevity unless it's 8.01
                    if '8.01' not in section_name:
                         logger.debug(f"Found candidate via fallback: Name='{section_name}', Pos={position}")

        # DEBUG: Log if Item 8.01 wasn't found by either method
        if not found_via_tag and not found_via_fallback:
             logger.warning("Parser: Item 8.01 header was NOT matched by tag or fallback regex.")

        # --- Process final candidates --- 
        if not final_candidates:
            logger.warning("No final section candidates found after processing")
            return {}

        # Sort by final position in cleaned text
        final_candidates.sort(key=lambda x: x["position"]) 

        # Identify forward-looking sections based on cleaned text positions
        forward_looking_sections = self._identify_forward_looking_sections(full_cleaned_text)
        logger.debug(f"Identified {len(forward_looking_sections)} forward-looking statement spans")

        sections = {}
        num_candidates = len(final_candidates)
        for i, candidate in enumerate(final_candidates):
            section_name = candidate["name"]
            section_title = candidate["title"]
            start_pos = candidate["position"]
            cleaned_header = candidate["cleaned_header"]

            # Determine end position (start of next section's header or end of document)
            end_pos = final_candidates[i+1]["position"] if i < num_candidates - 1 else len(full_cleaned_text)

            logger.debug(f"Processing candidate: Name='{section_name}', Title='{section_title}', CleanedStart={start_pos}, InitialCleanedEnd={end_pos}")

            # Skip if this section's header start is within a forward-looking span
            if any(fls_start <= start_pos < fls_end for fls_start, fls_end in forward_looking_sections):
                 logger.debug(f"Skipping section '{section_name}' starting within a forward-looking span")
                 continue

            # Adjust end position if it overlaps with a forward-looking statement start
            adjusted_end_pos = end_pos
            for fls_start, fls_end in forward_looking_sections:
                if start_pos < fls_start < adjusted_end_pos:
                     logger.debug(f"Adjusting end position for section '{section_name}' from {adjusted_end_pos} to {fls_start} due to overlapping forward-looking statement")
                     adjusted_end_pos = fls_start

            # Extract content: from *after* the cleaned header text to the adjusted end position
            content_start = start_pos + len(cleaned_header)
            content = full_cleaned_text[content_start:adjusted_end_pos].strip()

            logger.debug(f"Extracted content for '{section_name}' (len: {len(content)}, start: {content_start}, end: {adjusted_end_pos}): '{content[:150]}...'" + ('[EMPTY]' if not content else ''))

            normalized_name = section_name.lower().replace(')', '') # Clean ')' from Item X.XX) pattern

            section = FilingSection(
                name=normalized_name,
                content=content, # Content no longer includes the header
                start_pos=content_start, # Position reflects start of actual content
                end_pos=adjusted_end_pos
            )

            # Validate section (use content only for length check now)
            if self._validate_section(normalized_name, section_title, content):
                sections[normalized_name] = section
                logger.debug(f"Added valid section: '{normalized_name}'")
            else:
                logger.debug(f"Skipping invalid or filtered section: '{normalized_name}' based on validation rule.")

        logger.info(f"Extracted {len(sections)} valid sections from document. Keys: {list(sections.keys())}")
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
        Content no longer includes the header text itself.
        """
        # Check if section name is one of our known sections
        known_section_match = False
        cleaned_section_name = section_name.lower().replace(')', '').strip()

        for known_key in self.KNOWN_SECTIONS:
            if known_key == cleaned_section_name:
                 known_section_match = True
                 logger.debug(f"Validated known section '{cleaned_section_name}' by item number.")
                 return True # Finding a known item number is sufficient

        # If it wasn't a directly known section (e.g. Item 1.05, Item 8.01)
        # Check for general item pattern validity
        if not re.match(r'item\s+\d+\.\d+', section_name, re.IGNORECASE):
             logger.debug(f"Validation failed: Section name '{section_name}' doesn't match item pattern.")
             return False

        # For unknown sections that match the pattern, allow them even if content is short
        logger.debug(f"Validated unknown section '{section_name}' by pattern.") 
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