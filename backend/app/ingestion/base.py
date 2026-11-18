from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class NormalizedJob(BaseModel):
    external_job_id: str
    title: str
    description: str
    company_name: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    remote_type: str = "ONSITE"  # REMOTE, HYBRID, ONSITE
    work_arrangement: Optional[str] = "ONSITE"  # ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED
    remote_eligibility: Optional[str] = "UNSPECIFIED"  # WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED
    employment_type: str = "FULL_TIME"  # FULL_TIME, PART_TIME, CONTRACT, FREELANCE, INTERNSHIP, APPRENTICESHIP, TEMPORARY, PERMANENT, SEASONAL, CASUAL, COMMISSION, PERFORMANCE_BASED, FIXED_TERM, SHIFT_BASED, OTHER
    experience_level: Optional[str] = None  # ENTRY, MID, SENIOR, LEAD, EXECUTIVE
    min_experience_years: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "YEAR"
    posting_date: Optional[datetime] = None
    application_url: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class SourceAdapter(ABC):
    """
    Source Adapter Contract:
    Every source integration must implement this interface to preserve
    system boundaries and keep ingestion decoupled from search/accounts.
    """

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validates configuration parameters before execution."""
        pass

    @abstractmethod
    def fetch_page(self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        """
        Fetches one page of raw records.
        Returns: (raw_records, next_checkpoint, has_more)
        """
        pass

    @abstractmethod
    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        """
        Parses single raw record and normalizes into common schema.
        Returns NormalizedJob or None if invalid/rejected.
        """
        pass

    def classify_error(self, exc: Exception) -> str:
        """Categorizes exception into standardized failure type."""
        err_str = str(exc).lower()
        # Network, DNS, socket, timeout, or transient 5xx HTTP gateway errors
        transient_indicators = [
            "timeout", "timed out", "connection", "connect", "getaddrinfo",
            "gaierror", "nameresolution", "network", "reset by peer",
            "remote end closed", "sslsyscallerror", "ssl error",
            "500", "502", "503", "504", "service unavailable",
            "bad gateway", "gateway timeout", "temporarily unavailable"
        ]
        if any(ind in err_str for ind in transient_indicators):
            return "TRANSIENT"
        elif "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
            return "RATE_LIMIT"
        elif "401" in err_str or "403" in err_str or "auth" in err_str or "forbidden" in err_str or "unauthorized" in err_str:
            return "AUTHENTICATION"
        elif "parse" in err_str or "json" in err_str or "keyerror" in err_str or "xml" in err_str:
            return "PARSE"
        return "PERMANENT"
