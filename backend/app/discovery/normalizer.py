import re
import urllib.parse
from typing import Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models import Company

# Common international legal business entity suffixes
LEGAL_SUFFIXES = [
    r"\binc(?:\.|\b)",
    r"\bincorporated\b",
    r"\bcorp(?:\.|\b)",
    r"\bcorporation\b",
    r"\bllc(?:\.|\b)",
    r"\bl\.l\.c\.(?:\.|\b)",
    r"\bpty(?:\.|\b)\s+ltd(?:\.|\b)",
    r"\bpty(?:\.|\b)",
    r"\bltd(?:\.|\b)",
    r"\blimited\b",
    r"\bplc(?:\.|\b)",
    r"\bgmbh\b",
    r"\bag\b",
    r"\bs\.a\.(?:\.|\b)",
    r"\bsa\b",
    r"\bb\.v\.(?:\.|\b)",
    r"\bbv\b",
    r"\bco(?:\.|\b)",
    r"\bcompany\b",
    r"\bholdings?\b",
    r"\bgroup\b",
    r"\bab\b",
    r"\bse\b",
]

SECOND_LEVEL_TLDS = {
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "co.jp", "ne.jp", "ac.jp",
    "com.au", "net.au", "org.au", "edu.au",
    "co.nz", "net.nz", "org.nz",
    "com.br", "org.br", "net.br",
    "co.in", "net.in", "org.in", "gen.in",
    "com.sg", "net.sg", "org.sg",
    "com.my", "net.my", "org.my",
    "co.za", "org.za", "net.za",
    "com.tr", "org.tr",
    "com.mx", "org.mx",
}

KNOWN_ATS_DOMAINS = {
    "lever.co", "greenhouse.io", "ashbyhq.com", "smartrecruiters.com",
    "workable.com", "bamboohr.com", "teamtailor.com", "recruitee.com",
    "breezy.hr", "personio.de", "personio.com", "myworkdayjobs.com",
    "icims.com", "jobvite.com", "oraclecloud.com", "taleo.net"
}

def clean_company_name(raw_name: str) -> str:
    """
    Cleans corporate titles (e.g. 'MICROSOFT CORP' -> 'Microsoft', 'Alphabet Inc.' -> 'Alphabet')
    for canonical indexing while preserving trademark identity.
    """
    if not raw_name:
        return ""
    name = raw_name.strip()

    # If all-caps (e.g. SEC EDGAR 'AMAZON COM INC'), title case it
    if name.isupper() and len(name) > 3:
        name = name.title()

    # Remove legal suffixes
    for pattern in LEGAL_SUFFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

    # Clean punctuation and trailing commas / dots
    name = re.sub(r"[\,\.\-\/\\]+$", "", name).strip()
    name = re.sub(r"\s+", " ", name).strip()

    # Handle known canonical exceptions
    exceptions = {
        "Amazon Com": "Amazon",
        "Meta Platforms": "Meta",
        "Alphabet": "Google",
        "Apple Computer": "Apple",
        "Tesla Motors": "Tesla",
    }
    return exceptions.get(name, name)


def extract_canonical_domain(url: str) -> Optional[str]:
    """
    Extracts root domain (e.g. 'https://careers.stripe.com/jobs' -> 'stripe.com').
    Correctly recognizes international two-part TLDs (e.g. .co.uk, .com.au).
    """
    if not url:
        return None
    url_str = url.strip()
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = f"https://{url_str}"

    try:
        parsed = urllib.parse.urlparse(url_str)
        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return None

        parts = hostname.split(".")
        if len(parts) <= 1:
            return hostname

        # Check for known second-level TLDs
        if len(parts) >= 3:
            candidate_slt = f"{parts[-2]}.{parts[-1]}"
            if candidate_slt in SECOND_LEVEL_TLDS:
                return f"{parts[-3]}.{candidate_slt}"

        # Standard single TLD (e.g. stripe.com)
        return ".".join(parts[-2:])
    except Exception:
        return None


def is_duplicate_company(
    db: Session,
    name: str,
    domain: Optional[str] = None,
    aliases: Optional[List[str]] = None
) -> Optional[Company]:
    """
    Prevents duplicate company records using:
    1. Exact or canonical domain matching.
    2. Canonical name or cleaned name matching.
    3. Alias matching.
    Returns existing Company record if duplicate, else None.
    """
    clean_name = clean_company_name(name)

    # 1. Domain match (strongest identity, excluding shared public ATS domains)
    if domain:
        norm_dom = extract_canonical_domain(domain)
        if norm_dom and norm_dom.lower() not in KNOWN_ATS_DOMAINS:
            match = db.query(Company).filter(
                or_(
                    Company.domain == norm_dom,
                    Company.website.ilike(f"%{norm_dom}%")
                )
            ).first()
            if match:
                return match

    # 2. Canonical name match (case-insensitive)
    match_name = db.query(Company).filter(
        or_(
            func.lower(Company.canonical_name) == name.strip().lower(),
            func.lower(Company.canonical_name) == clean_name.lower()
        )
    ).first()
    if match_name:
        return match_name

    # 3. Check aliases
    if aliases:
        for alias in aliases:
            if not alias:
                continue
            match_alias = db.query(Company).filter(
                or_(
                    func.lower(Company.canonical_name) == alias.strip().lower(),
                    Company.aliases.contains([alias.strip()])
                )
            ).first()
            if match_alias:
                return match_alias

    return None
