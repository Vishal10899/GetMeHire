import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country
from app.core.config import settings

class USAJobsAdapter(SourceAdapter):
    """
    Adapter for the official USAJOBS Open Data API.
    API Documentation: https://developer.usajobs.gov/api-reference/get-api-search
    Requirements:
      - Host: data.usajobs.gov
      - User-Agent: Valid developer email address
      - Authorization-Key: Valid developer API key
    Credentials are NEVER printed or committed.
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        api_key = config.get("api_key") or getattr(settings, "USAJOBS_API_KEY", None)
        user_agent_email = config.get("user_agent_email") or getattr(settings, "USAJOBS_USER_AGENT_EMAIL", None)
        # USAJobs requires both Authorization-Key and User-Agent email
        return bool(api_key and user_agent_email)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        api_key = config.get("api_key") or getattr(settings, "USAJOBS_API_KEY", None)
        user_agent_email = config.get("user_agent_email") or getattr(settings, "USAJOBS_USER_AGENT_EMAIL", None)

        if not api_key or not user_agent_email:
            raise PermissionError("USAJobs API requires USAJOBS_API_KEY and USAJOBS_USER_AGENT_EMAIL environment configuration")

        page = int(checkpoint.get("page", 1))
        results_per_page = int(config.get("results_per_page", 25))
        keyword = config.get("keyword", "")

        api_url = "https://data.usajobs.gov/api/Search"
        params = {
            "Page": page,
            "ResultsPerPage": results_per_page,
        }
        if keyword:
            params["Keyword"] = keyword

        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": user_agent_email,
            "Authorization-Key": api_key,
            "Accept": "application/json",
        }
        client_timeout = httpx.Timeout(30.0, connect=10.0)

        max_retries = 3
        backoff_seconds = 2.0
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(api_url, params=params, headers=headers)
                    if resp.status_code == 401:
                        raise PermissionError("USAJobs authentication failed: Invalid or expired Authorization-Key")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on USAJobs API (HTTP 429)")
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

        search_result = data.get("SearchResult", {})
        raw_items = search_result.get("SearchResultItems", [])

        # Pagination metadata
        user_area = search_result.get("UserArea", {})
        try:
            total_pages = int(user_area.get("NumberOfPages", 1))
        except (ValueError, TypeError):
            total_pages = 1

        has_more = page < total_pages and len(raw_items) > 0
        next_checkpoint = {
            "page": page + 1,
            "total_pages": total_pages,
            "completed": not has_more,
        }

        return raw_items, next_checkpoint, has_more

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            matched_id = str(raw_record.get("MatchedObjectId") or "")
            desc = raw_record.get("MatchedObjectDescriptor", {})

            external_id = str(desc.get("PositionID") or matched_id).strip()
            title = (desc.get("PositionTitle") or "").strip()
            if not external_id or not title:
                return None

            department_name = desc.get("DepartmentName")
            org_name = desc.get("OrganizationName")
            company_name = department_name or org_name or "United States Federal Government"

            # Construct clean description
            user_area = desc.get("UserArea", {})
            details = user_area.get("Details", {})
            job_summary = details.get("JobSummary") or ""
            key_reqs = details.get("KeyRequirements") or []

            desc_parts = []
            if job_summary:
                desc_parts.append(job_summary)
            if key_reqs:
                desc_parts.append("Key Requirements:\n" + "\n".join(f"- {r}" for r in key_reqs))

            if desc_parts:
                soup = BeautifulSoup("\n\n".join(desc_parts), "html.parser")
                clean_desc = soup.get_text(separator="\n").strip()
            else:
                clean_desc = f"Federal vacancy for {title} at {company_name}."

            # Location extraction
            locations = desc.get("PositionLocation", [])
            primary_loc = locations[0] if locations and isinstance(locations, list) else {}
            loc_name = primary_loc.get("LocationName") or primary_loc.get("CityName") or "United States"
            city_val = primary_loc.get("CityName")
            state_val = primary_loc.get("CountrySubdivisionCode")
            country_val = primary_loc.get("CountryCode") or "United States"

            norm_loc, norm_city, norm_region, norm_country, detected_remote = normalize_location_and_country(
                loc_name, title
            )

            # Remote / Telework eligibility
            telework_eligible = details.get("TeleworkEligible", False)
            remote_type = detected_remote
            if telework_eligible or "remote" in title.lower() or "telework" in loc_name.lower():
                remote_type = "REMOTE"

            # Remuneration / Salary
            remunerations = desc.get("PositionRemuneration", [])
            salary_min = None
            salary_max = None
            salary_period = "YEAR"
            if remunerations and isinstance(remunerations, list):
                remun = remunerations[0]
                if remun.get("MinimumRange"):
                    try:
                        salary_min = Decimal(str(remun["MinimumRange"]))
                    except Exception:
                        pass
                if remun.get("MaximumRange"):
                    try:
                        salary_max = Decimal(str(remun["MaximumRange"]))
                    except Exception:
                        pass
                interval = (remun.get("RateIntervalCode") or "").upper()
                if "HOUR" in interval:
                    salary_period = "HOUR"
                elif "MONTH" in interval:
                    salary_period = "MONTH"

            # Application URL
            app_url = desc.get("PositionURI")
            apply_urls = desc.get("ApplyURI", [])
            if apply_urls and isinstance(apply_urls, list) and apply_urls[0]:
                app_url = apply_urls[0]
            if not app_url:
                app_url = f"https://www.usajobs.gov/job/{external_id}"

            # Posting date
            start_date = desc.get("PublicationStartDate")
            posting_dt = datetime.utcnow()
            if start_date:
                try:
                    posting_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            # Technical and professional skills
            tech_skills = [
                "python", "react", "fastapi", "django", "node", "typescript", "javascript",
                "aws", "docker", "kubernetes", "sql", "postgres", "cybersecurity", "security",
                "cloud", "data analysis", "project management", "network", "linux"
            ]
            matched_skills = [s.capitalize() for s in tech_skills if s in clean_desc.lower() or s in title.lower()]

            return NormalizedJob(
                external_job_id=f"usajobs-{external_id}",
                title=title,
                description=clean_desc,
                company_name=company_name,
                department=org_name or department_name,
                location=norm_loc,
                city=norm_city or city_val,
                region=norm_region or state_val,
                country=norm_country or country_val,
                remote_type=remote_type,
                employment_type="FULL_TIME",
                experience_level="MID",
                skills=matched_skills,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency="USD",
                salary_period=salary_period,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None
