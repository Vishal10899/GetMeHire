import re
import httpx
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

ATS_PATTERNS = [
    # Greenhouse
    {
        "provider": "GREENHOUSE",
        "patterns": [
            r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9_\-]+)",
            r"boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_\-]+)",
            r"job-boards\.greenhouse\.io/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs?content=true"
    },
    # Lever
    {
        "provider": "LEVER",
        "patterns": [
            r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)",
            r"api\.lever\.co/v0/postings/([a-zA-Z0-9_\-]+)",
            r"api\.eu\.lever\.co/v0/postings/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://api.lever.co/v0/postings/{board_id}?mode=json"
    },
    # Ashby
    {
        "provider": "ASHBY",
        "patterns": [
            r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)",
            r"api\.ashbyhq\.com/posting-api/job-board/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://api.ashbyhq.com/posting-api/job-board/{board_id}"
    },
    # Workable
    {
        "provider": "WORKABLE",
        "patterns": [
            r"apply\.workable\.com/([a-zA-Z0-9_\-]+)",
            r"([a-zA-Z0-9_\-]+)\.workable\.com",
        ],
        "feed_template": "https://apply.workable.com/api/v1/widget/accounts/{board_id}"
    },
    # SmartRecruiters
    {
        "provider": "SMARTRECRUITERS",
        "patterns": [
            r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)",
            r"api\.smartrecruiters\.com/v1/companies/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://api.smartrecruiters.com/v1/companies/{board_id}/postings?limit=100"
    },
    # Personio
    {
        "provider": "PERSONIO",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.jobs\.personio\.(?:de|com)",
        ],
        "feed_template": "https://{board_id}.jobs.personio.de/xml?language=en"
    },
    # Recruitee
    {
        "provider": "RECRUITEE",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.recruitee\.com",
        ],
        "feed_template": "https://{board_id}.recruitee.com/api/offers/"
    },
    # BambooHR
    {
        "provider": "BAMBOOHR",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.bamboohr\.com/careers",
            r"([a-zA-Z0-9_\-]+)\.bamboohr\.com/jobs",
        ],
        "feed_template": "https://{board_id}.bamboohr.com/careers/list"
    },
    # Teamtailor
    {
        "provider": "TEAMTAILOR",
        "patterns": [
            r"career\.([a-zA-Z0-9_\-]+)\.(?:com|io|co|se|org|net)",
            r"(?!career\b)([a-zA-Z0-9_\-]+)\.teamtailor\.com",
            r"([a-zA-Z0-9_\-]+)\.teamtailor\.com",
        ],
        "feed_template": "https://{board_id}.teamtailor.com/jobs.rss"
    },
    # Breezy HR
    {
        "provider": "BREEZY",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.breezy\.hr",
        ],
        "feed_template": "https://{board_id}.breezy.hr/json"
    },
    # Workday
    {
        "provider": "WORKDAY",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:en-US/)?([a-zA-Z0-9_\-]+)",
            r"([a-zA-Z0-9_\-]+)\.myworkdayjobs\.com/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://{board_id}.myworkdayjobs.com"
    },
    # iCIMS
    {
        "provider": "ICIMS",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.icims\.com",
            r"careers-([a-zA-Z0-9_\-]+)\.icims\.com",
        ],
        "feed_template": "https://{board_id}.icims.com/jobs/search?pr=0&schema=1&in_iframe=1"
    },
    # Jobvite
    {
        "provider": "JOBVITE",
        "patterns": [
            r"jobs\.jobvite\.com/([a-zA-Z0-9_\-]+)",
        ],
        "feed_template": "https://jobs.jobvite.com/{board_id}/search?format=json"
    },
    # Oracle Recruiting Cloud
    {
        "provider": "ORACLE",
        "patterns": [
            r"([a-zA-Z0-9_\-]+)\.fa\.([a-zA-Z0-9_\-]+)\.ocs\.oraclecloud\.com",
            r"([a-zA-Z0-9_\-]+)\.oraclecloud\.com/hcmUI/CandidateExperience",
        ],
        "feed_template": "https://{board_id}.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    },
    # SAP SuccessFactors
    {
        "provider": "SUCCESSFACTORS",
        "patterns": [
            r"career\d*\.successfactors\.com.*?company=([a-zA-Z0-9_\-]+)",
            r"([a-zA-Z0-9_\-]+)\.successfactors\.com",
        ],
        "feed_template": "https://career4.successfactors.com/career?company={board_id}&rcm_site_locale=en_US"
    },
]

COMMON_CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/about/careers",
    "/company/careers",
    "/join-us",
    "/work-with-us",
    "/open-roles",
    "/positions",
]

class CareerCrawlerService:
    """
    Multi-Level Deep Crawling & ATS Detection Service:
    - Level 1: Official Career Page Discovery from website.
    - Level 2: ATS Detection & Public Board Identifier extraction.
    - Level 3: Multi-page Job Extraction management.
    - Level 4: Fallback HTML/JSON-LD Career Page Extraction.
    """

    @classmethod
    def discover_career_page(cls, website_url: str) -> Optional[str]:
        """
        Level 1: Discovers official career page from verified company website.
        """
        if not website_url:
            return None
        website_url = website_url.strip()
        if not website_url.startswith("http://") and not website_url.startswith("https://"):
            website_url = f"https://{website_url}"

        headers = {
            "User-Agent": "GetMeHireBot/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            # 1. Probe common career path conventions
            for path in COMMON_CAREER_PATHS:
                probe_url = urljoin(website_url, path)
                try:
                    resp = client.get(probe_url, headers=headers)
                    if resp.status_code == 200 and len(resp.text) > 500:
                        # Verify page mentions jobs/careers
                        lower = resp.text.lower()
                        if any(term in lower for term in ["job", "career", "open position", "join our team"]):
                            return str(resp.url)
                except Exception:
                    continue

            # 2. Inspect homepage for career anchors
            try:
                resp = client.get(website_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        txt = a.get_text(separator=" ", strip=True).lower()
                        href = a["href"].strip()
                        if any(w in txt for w in ["careers", "jobs", "join us", "work with us", "we're hiring"]):
                            return urljoin(str(resp.url), href)
            except Exception:
                pass

        return None

    @classmethod
    def detect_ats(cls, career_url: str, html_content: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Level 2: Detects supported ATS and extracts board identifier from URL or HTML body.
        Returns (ats_provider: str, board_id: Optional[str], canonical_feed_url: Optional[str]).
        """
        if not career_url:
            return "WEB_SCRAPER", None, None

        # Check URL patterns first
        for entry in ATS_PATTERNS:
            provider = entry["provider"]
            for pat in entry["patterns"]:
                match = re.search(pat, career_url, re.IGNORECASE)
                if match:
                    board_id = match.group(1).lower()
                    feed_url = entry["feed_template"].format(board_id=board_id)
                    return provider, board_id, feed_url

        # Check HTML content if provided or fetch it
        if html_content is None:
            try:
                headers = {"User-Agent": "GetMeHireBot/2.0 (+https://getmehire.com/bot)"}
                with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                    resp = client.get(career_url, headers=headers)
                    if resp.status_code == 200:
                        html_content = resp.text
            except Exception:
                pass

        if html_content:
            for entry in ATS_PATTERNS:
                provider = entry["provider"]
                for pat in entry["patterns"]:
                    match = re.search(pat, html_content, re.IGNORECASE)
                    if match:
                        board_id = match.group(1).lower()
                        feed_url = entry["feed_template"].format(board_id=board_id)
                        return provider, board_id, feed_url

        # Fallback to Level 4 Web Scraper
        return "WEB_SCRAPER", None, career_url
