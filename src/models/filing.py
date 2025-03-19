from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FilingSection:
    """Represents a section within an SEC filing."""
    name: str
    content: str
    start_pos: int
    end_pos: int


@dataclass
class Filing:
    """Represents an SEC filing document with structured data and metadata."""
    form_type: str
    company_name: str
    cik: str
    filing_href: str
    filing_date: str
    ticker_symbol: Optional[str] = None
    raw_content: Optional[str] = None
    html_content: Optional[str] = None
    sections: Dict[str, FilingSection] = field(default_factory=dict)
    matching_terms: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    
    @property
    def filing_url(self) -> str:
        """Alias for filing_href for backwards compatibility."""
        return self.filing_href
    
    @property
    def has_item_105(self) -> bool:
        """Check if filing has Item 1.05 section."""
        return any(name.lower() == "item 1.05" for name in self.sections.keys())
    
    @property
    def has_item_801(self) -> bool:
        """Check if filing has Item 8.01 section."""
        return any(name.lower() == "item 8.01" for name in self.sections.keys())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "company_name": self.company_name,
            "cik": self.cik,
            "ticker": self.ticker_symbol,
            "form_type": self.form_type,
            "filing_date": self.filing_date,
            "filing_url": self.filing_href,
            "matching_terms": self.matching_terms,
            "context": "\n\n".join(self.contexts).strip()
        } 