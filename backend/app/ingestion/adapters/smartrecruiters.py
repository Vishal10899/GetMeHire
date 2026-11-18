import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

class SmartRecruitersAdapter(SourceAdapter):
    """
    Adapter for SmartRecruiters public posting API.
    Fetches job listings from:
    https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset={offset}
    and enriches with job details from:
    https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("company_identifier") or config.get("board_url"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug") or config.get("company_identifier") or config.get("board_id")
        if not company_slug and source_url:
            if "/companies/" in source_url:
                after = source_url.split("/companies/")[1]
                company_slug = after.split("/")[0].split("?")[0]
            else:
                parts = [p for p in source_url.rstrip("/").split("/") if p]
                if parts:
                    last_part = parts[-1].split("?")[0]
                    if last_part == "postings" and len(parts) >= 2:
                        company_slug = parts[-2].split("?")[0]
                    else:
                        company_slug = last_part

        if not company_slug:
            raise ValueError("SmartRecruiters company identifier could not be determined from configuration or URL")

        checkpoint = checkpoint or {}
        offset = int(checkpoint.get("offset", 0))
        limit = int(config.get("page_size", 100))

        api_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
        params = {"limit": limit, "offset": offset}
        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "application/json",
        }
        client_timeout = httpx.Timeout(30.0, connect=10.0)

        max_retries = 3
        backoff_seconds = 1.0
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(api_url, params=params, headers=headers)
                    if resp.status_code == 404:
                        raise Exception(f"SmartRecruiters company '{company_slug}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on SmartRecruiters API (HTTP 429)")
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

            total_found = data.get("totalFound", 0)
            raw_postings = data.get("content", [])
            enriched_postings = []

            fetch_details = config.get("fetch_details", False)
            max_details = int(config.get("max_details", 5))
            for idx, posting in enumerate(raw_postings):
                pid = posting.get("id")
                posting["_company_slug"] = company_slug
                if fetch_details and pid and idx < max_details:
                    detail_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings/{pid}"
                    try:
                        time.sleep(0.04)  # Polite throttle
                        d_resp = client.get(detail_url, headers=headers)
                        if d_resp.status_code == 200:
                            posting["detail"] = d_resp.json()
                    except Exception:
                        pass
                enriched_postings.append(posting)

            next_offset = offset + len(raw_postings)
            has_more = next_offset < total_found and len(raw_postings) > 0
            next_checkpoint = {
                "offset": next_offset,
                "total_found": total_found,
                "completed": not has_more,
            }

        return enriched_postings, next_checkpoint, has_more

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id") or "").strip()
            title = (raw_record.get("name") or "").strip()
            if not external_id or not title:
                return None

            company_slug = raw_record.get("_company_slug") or "jobs"
            detail = raw_record.get("detail", {})

            # Clean and combine job description sections
            sections = detail.get("jobAd", {}).get("sections", {})
            desc_parts = []
            if sections.get("companyDescription", {}).get("text"):
                desc_parts.append(sections["companyDescription"]["text"])
            if sections.get("jobDescription", {}).get("text"):
                desc_parts.append(sections["jobDescription"]["text"])
            if sections.get("qualifications", {}).get("text"):
                desc_parts.append(f"<h3>Qualifications</h3>{sections['qualifications']['text']}")
            if sections.get("additionalInformation", {}).get("text"):
                desc_parts.append(f"<h3>Additional Information</h3>{sections['additionalInformation']['text']}")

            if desc_parts:
                soup = BeautifulSoup("\n".join(desc_parts), "html.parser")
                clean_desc = soup.get_text(separator="\n").strip()
            else:
                clean_desc = f"Open position for {title}."

            # Department
            dept = raw_record.get("department")
            dept_name = None
            if isinstance(dept, dict):
                dept_name = dept.get("label") or dept.get("name")
            elif isinstance(dept, str):
                dept_name = dept

            # Location handling
            loc_data = raw_record.get("location", {})
            city = loc_data.get("city")
            region = loc_data.get("region")
            country_val = loc_data.get("country")
            full_loc = loc_data.get("fullLocation")

            location_str = full_loc or f"{city or ''}, {country_val or ''}".strip(", ") or "Worldwide"
            norm_loc, norm_city, norm_region, norm_country, detected_remote = normalize_location_and_country(
                location_str, title
            )

            is_remote = loc_data.get("remote", False)
            is_hybrid = loc_data.get("hybrid", False)

            remote_type = detected_remote
            if is_remote or "remote" in location_str.lower():
                remote_type = "REMOTE"
            elif is_hybrid and remote_type != "REMOTE":
                remote_type = "HYBRID"

            # Application URL preservation
            app_url = f"https://jobs.smartrecruiters.com/{company_slug}/{external_id}"

            # Posting date
            date_str = raw_record.get("releasedDate") or detail.get("releasedDate")
            posting_dt = datetime.utcnow()
            if date_str:
                try:
                    posting_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            # Taxonomy skills extraction
            tech_skills = [
                "python", "react", "fastapi", "django", "node", "typescript", "javascript",
                "aws", "docker", "kubernetes", "sql", "postgres", "golang", "java", "c++",
                "ai", "machine learning", "product", "sales", "marketing", "devops", "cloud"
            ]
            matched_skills = [s.capitalize() for s in tech_skills if s in clean_desc.lower() or s in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc,
                department=dept_name,
                location=norm_loc,
                city=norm_city or city,
                region=norm_region or region,
                country=norm_country or country_val,
                remote_type=remote_type,
                employment_type="FULL_TIME",
                experience_level="SENIOR" if "senior" in title.lower() else "MID",
                skills=matched_skills,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None
