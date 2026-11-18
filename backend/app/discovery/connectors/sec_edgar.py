import httpx
from typing import List, Dict, Any
from app.discovery.connectors.base import BaseDiscoveryConnector, DiscoveredCompanyCandidate
from app.discovery.normalizer import clean_company_name, extract_canonical_domain

# Industry classification heuristics based on corporate titles
INDUSTRY_KEYWORDS = {
    "Healthcare & Pharmaceuticals": ["pharmaceutical", "pharma", "therapeutics", "bio", "health", "medical", "hospital", "diagnostics", "oncology"],
    "Finance & Banking": ["bank", "banc", "financial", "capital", "insurance", "investment", "credit", "asset management", "trust", "reit"],
    "Energy": ["energy", "oil", "gas", "petroleum", "solar", "renewable", "power", "utility", "resources"],
    "Telecommunications": ["telecom", "communications", "wireless", "broadband", "network"],
    "Aerospace": ["aerospace", "defense", "aviation", "space"],
    "Automotive": ["automotive", "motors", "auto", "vehicle"],
    "Manufacturing": ["industrial", "manufacturing", "steel", "chemical", "materials", "packaging", "precision"],
    "E-commerce & Retail": ["retail", "stores", "ecommerce", "consumer", "brands", "apparel"],
    "Media & Entertainment": ["media", "entertainment", "broadcasting", "publishing", "gaming", "studios"],
    "Construction & Infrastructure": ["construction", "infrastructure", "engineering", "builders", "materials"],
    "Logistics & Supply Chain": ["logistics", "freight", "transport", "shipping", "marine", "supply chain"],
    "Hospitality": ["hotels", "resorts", "hospitality", "restaurants", "dining"],
    "Data Science & AI": ["ai", "artificial intelligence", "data", "analytics", "cloud"],
    "Software & IT": ["technologies", "software", "tech", "systems", "digital", "micro", "cyber", "information"],
}

FALLBACK_SEC_TICKERS = [
    {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    {"cik_str": 1018724, "ticker": "AMZN", "title": "AMAZON COM INC"},
    {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms, Inc."},
    {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
    {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
    {"cik_str": 200406, "ticker": "JNJ", "title": "JOHNSON & JOHNSON"},
    {"cik_str": 78003, "ticker": "PFE", "title": "PFIZER INC"},
    {"cik_str": 19617, "ticker": "JPM", "title": "JPMORGAN CHASE & CO"},
    {"cik_str": 70858, "ticker": "BAC", "title": "BANK OF AMERICA CORP /DE/"},
    {"cik_str": 34088, "ticker": "XOM", "title": "EXXON MOBIL CORP"},
    {"cik_str": 93410, "ticker": "CVX", "title": "CHEVRON CORP"},
    {"cik_str": 12927, "ticker": "BA", "title": "BOEING CO"},
    {"cik_str": 936468, "ticker": "LMT", "title": "LOCKHEED MARTIN CORP"},
    {"cik_str": 732717, "ticker": "T", "title": "AT&T INC."},
    {"cik_str": 732712, "ticker": "VZ", "title": "VERIZON COMMUNICATIONS INC"},
    {"cik_str": 104169, "ticker": "WMT", "title": "Walmart Inc."},
    {"cik_str": 1418135, "ticker": "DIS", "title": "Walt Disney Co"},
    {"cik_str": 1141391, "ticker": "MA", "title": "Mastercard Inc"},
    {"cik_str": 1403161, "ticker": "V", "title": "VISA INC."},
    {"cik_str": 50863, "ticker": "INTC", "title": "INTEL CORP"},
    {"cik_str": 2488, "ticker": "AMD", "title": "ADVANCED MICRO DEVICES INC"},
    {"cik_str": 1341439, "ticker": "ORCL", "title": "ORACLE CORP"},
    {"cik_str": 1108524, "ticker": "CRM", "title": "Salesforce, Inc."},
    {"cik_str": 1559720, "ticker": "ABNB", "title": "Airbnb, Inc."},
    {"cik_str": 1543151, "ticker": "UBER", "title": "Uber Technologies, Inc."},
]

class SecEdgarConnector(BaseDiscoveryConnector):
    """
    Ingests genuine publicly-registered companies from the US Securities and Exchange Commission (SEC)
    free public directory (EDGAR company_tickers.json).
    """

    @property
    def source_name(self) -> str:
        return "SEC EDGAR Public Registry"

    def discover(self, limit: int = 1000) -> List[DiscoveredCompanyCandidate]:
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {
            "User-Agent": "GetMeHire-DiscoveryPlatform bot@getmehire.com (+https://getmehire.com/terms; public indexer)",
            "Accept": "application/json"
        }

        candidates = []
        items = []
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    items = list(data.values()) if isinstance(data, dict) else data
        except Exception:
            pass

        if not items:
            items = FALLBACK_SEC_TICKERS

        for item in items[:limit]:
            raw_title = item.get("title", "").strip()
            ticker = item.get("ticker", "").strip().upper()
            cik = item.get("cik_str")

            if not raw_title or not ticker:
                continue

            canonical = clean_company_name(raw_title)
            if not canonical:
                continue

            # Deduce industry based on name heuristics
            lower_title = raw_title.lower()
            industry = "Software & IT"  # Default fallback
            for ind_name, kws in INDUSTRY_KEYWORDS.items():
                if any(kw in lower_title for kw in kws):
                    industry = ind_name
                    break

            candidate = DiscoveredCompanyCandidate(
                name=canonical,
                domain=None,  # Will be discovered via domain verifier
                website=None,
                career_page_url=None,
                country="United States",
                operating_region="North America",
                industry=industry,
                discovery_source="SEC_EDGAR_OPEN_REGISTRY",
                aliases=[raw_title, ticker] if raw_title != canonical else [ticker],
                metadata={
                    "ticker": ticker,
                    "cik": cik,
                    "sec_registered": True
                }
            )
            candidates.append(candidate)

        return candidates
