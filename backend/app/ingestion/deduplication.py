import hashlib
import re
from typing import Optional
from app.ingestion.base import NormalizedJob

def clean_text_for_fingerprint(text: Optional[str]) -> str:
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Strip HTML entities e.g. &amp;, &#123;
    clean = re.sub(r"&[a-zA-Z0-9#]+;", " ", clean)
    # Strip non-alphanumeric except spaces
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", clean)
    # Collapse multiple whitespaces
    clean = re.sub(r"\s+", " ", clean).strip().lower()
    return clean

def compute_content_fingerprint(job: NormalizedJob, company_name: str) -> str:
    """
    Computes deterministic SHA-256 fingerprint for a normalized job.
    Uses title, company, cleaned description snippet, location, and remote type.
    """
    normalized_title = clean_text_for_fingerprint(job.title)
    normalized_company = clean_text_for_fingerprint(company_name)
    normalized_desc = clean_text_for_fingerprint(job.description[:1000])
    normalized_loc = clean_text_for_fingerprint(job.location or job.country or "")
    remote = (job.remote_type or "").upper()
    emp_type = (job.employment_type or "").upper()

    fingerprint_input = f"{normalized_title}|{normalized_company}|{normalized_desc}|{normalized_loc}|{remote}|{emp_type}"
    return hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
