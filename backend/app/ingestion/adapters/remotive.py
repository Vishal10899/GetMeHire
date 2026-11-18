import re
import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

def parse_salary_string(salary_str: Optional[str]) -> Tuple[Optional[Decimal], Optional[Decimal], str]:
    """
    Parses salary strings like '$85k - $155k', '80000 - 120000 USD', or '$90,000/year'.
    Returns (salary_min, salary_max, currency).
    """
    if not salary_str:
        return None, None, "USD"

    currency = "USD"
    if "€" in salary_str or "eur" in salary_str.lower():
        currency = "EUR"
    elif "£" in salary_str or "gbp" in salary_str.lower():
        currency = "GBP"

    # Strip currency symbols and commas for regex matching
    s_clean = re.sub(r"[\$€£,]", "", salary_str).lower().strip()

    # Match ranges with 'k': e.g. 85k - 155k or 85k to 155k
    k_range = re.search(r"(\d+(?:\.\d+)?)\s*k\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*k", s_clean)
    if k_range:
        s_min = Decimal(str(int(float(k_range.group(1)) * 1000)))
        s_max = Decimal(str(int(float(k_range.group(2)) * 1000)))
        return s_min, s_max, currency

    # Match numeric ranges: e.g. 80000 - 120000
    num_range = re.search(r"(\d{4,7})\s*(?:-|to)\s*(\d{4,7})", s_clean)
    if num_range:
        s_min = Decimal(num_range.group(1))
        s_max = Decimal(num_range.group(2))
        return s_min, s_max, currency

    # Single value with 'k': e.g. 100k
    single_k = re.search(r"(\d+(?:\.\d+)?)\s*k", s_clean)
    if single_k:
        val = Decimal(str(int(float(single_k.group(1)) * 1000)))
        return val, val, currency

    return None, None, currency

class RemotiveAdapter(SourceAdapter):
    """
    Adapter for Remotive's dedicated public remote-jobs feed.
    API documentation: https://remotive.com/api/remote-jobs
    Terms of service compliance:
      - Preserves direct backlink to the Remotive job URL.
      - Preserves original employer attribution.
      - Restricts sync frequency to 4 times daily (0 */6 * * *).
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        # Remotive public feed does not require mandatory auth keys
        return True

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        base_url = config.get("endpoint_url") or source_url or "https://remotive.com/api/remote-jobs"

        params = {}
        if config.get("category"):
            params["category"] = config["category"]
        if config.get("search"):
            params["search"] = config["search"]
        if config.get("limit"):
            params["limit"] = int(config["limit"])

        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; Remotive syndication indexer)",
            "Accept": "application/json",
        }
        client_timeout = httpx.Timeout(35.0, connect=10.0)

        max_retries = 3
        backoff_seconds = 2.0
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(base_url, params=params, headers=headers)
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Remotive API (HTTP 429). Please schedule at most 4 calls/day.")
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2
                        continue
                    raise

        if not data or not isinstance(data, dict):
            return [], {"completed": True}, False

        jobs_list = data.get("jobs", [])
        return jobs_list, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id") or "").strip()
            title = (raw_record.get("title") or "").strip()
            if not external_id or not title:
                return None

            company_name = (raw_record.get("company_name") or "").strip() or "Remotive Employer"
            category = raw_record.get("category")

            raw_desc = raw_record.get("description", "")
            if raw_desc:
                soup = BeautifulSoup(raw_desc, "html.parser")
                clean_desc = soup.get_text(separator="\n").strip()
            else:
                clean_desc = f"Remote opportunity for {title} at {company_name}."

            req_loc = raw_record.get("candidate_required_location") or "Worldwide"
            norm_loc, city, region, country, _ = normalize_location_and_country(req_loc, title)

            # All Remotive jobs are remote
            remote_type = "REMOTE"

            # Employment type
            raw_emp = (raw_record.get("job_type") or "full_time").lower()
            emp_type = "FULL_TIME"
            if "part" in raw_emp:
                emp_type = "PART_TIME"
            elif "contract" in raw_emp or "freelance" in raw_emp:
                emp_type = "CONTRACT"
            elif "intern" in raw_emp:
                emp_type = "INTERNSHIP"

            # Parse compensation if available
            salary_min, salary_max, currency = parse_salary_string(raw_record.get("salary"))

            # Application URL: Preserve exact Remotive URL as required by API terms
            app_url = raw_record.get("url") or f"https://remotive.com/remote-jobs/{external_id}"

            # Posting date
            pub_date = raw_record.get("publication_date")
            posting_dt = datetime.utcnow()
            if pub_date:
                try:
                    posting_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            # Skills: combine provided tags with text matching
            tags = raw_record.get("tags") or []
            tag_skills = [t.capitalize() for t in tags if isinstance(t, str) and len(t) > 1]

            tech_skills = [
                "python", "react", "fastapi", "django", "node", "typescript", "javascript",
                "aws", "docker", "kubernetes", "sql", "postgres", "golang", "java", "ruby",
                "ai", "machine learning", "product", "sales", "marketing", "devops", "design"
            ]
            matched_skills = [s.capitalize() for s in tech_skills if s in clean_desc.lower() or s in title.lower()]
            all_skills = list(dict.fromkeys(tag_skills + matched_skills))

            return NormalizedJob(
                external_job_id=f"remotive-{external_id}",
                title=title,
                description=clean_desc,
                company_name=company_name,
                department=category,
                location=norm_loc or req_loc,
                city=city,
                region=region,
                country=country,
                remote_type=remote_type,
                employment_type=emp_type,
                experience_level="SENIOR" if "senior" in title.lower() else "MID",
                skills=all_skills,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None
