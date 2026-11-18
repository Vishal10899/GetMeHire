from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DiscoveredCompanyCandidate(BaseModel):
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    career_page_url: Optional[str] = None
    country: Optional[str] = "United States"
    operating_region: Optional[str] = "North America"
    industry: Optional[str] = "Software & IT"
    ats_provider: Optional[str] = None
    ats_board_id: Optional[str] = None
    discovery_source: str
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseDiscoveryConnector(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the discovery source."""
        pass

    @abstractmethod
    def discover(self, limit: int = 1000) -> List[DiscoveredCompanyCandidate]:
        """Discovers company candidates from permitted public sources."""
        pass
