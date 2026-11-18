import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

class LeverAdapter(SourceAdapter):
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("site"))

    def fetch_page(self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug")
        if not company_slug and source_url:
            parts = source_url.rstrip("/").split("/")
            company_slug = parts[-1]

        api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        headers = {
            "User-Agent": "JobDiscoveryPlatform/2.0",
            "Accept-Encoding": "gzip, deflate",
        }
        client_timeout = httpx.Timeout(45.0, connect=15.0)

        with httpx.Client(timeout=client_timeout) as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 404:
                # Attempt fallback to Lever EU endpoint
                eu_api_url = f"https://api.eu.lever.co/v0/postings/{company_slug}?mode=json"
                resp_eu = client.get(eu_api_url, headers=headers)
                if resp_eu.status_code == 200:
                    resp = resp_eu
            if resp.status_code == 429:
                raise Exception("Rate limit exceeded (HTTP 429)")
            resp.raise_for_status()
            data = resp.json()

        return data, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id"))
            title = raw_record.get("text", "").strip()
            if not external_id or not title:
                return None

            description = raw_record.get("descriptionPlain") or raw_record.get("description") or title
            categories = raw_record.get("categories", {})
            location_str = categories.get("location")
            team_str = categories.get("team")
            commitment_str = categories.get("commitment", "Full-time")

            emp_type = "FULL_TIME"
            if commitment_str:
                c_low = commitment_str.lower()
                if "part" in c_low:
                    emp_type = "PART_TIME"
                elif "contract" in c_low:
                    emp_type = "CONTRACT"
                elif "intern" in c_low:
                    emp_type = "INTERNSHIP"

            workplace = raw_record.get("workplaceType", "").lower()
            norm_loc, city, region, country, detected_remote = normalize_location_and_country(location_str, title)

            remote_type = detected_remote
            if "remote" in workplace:
                remote_type = "REMOTE"
            elif "hybrid" in workplace and remote_type != "REMOTE":
                remote_type = "HYBRID"

            app_url = raw_record.get("hostedUrl") or raw_record.get("applyUrl") or f"https://jobs.lever.co/postings/{external_id}"

            created_at_ms = raw_record.get("createdAt")
            posting_dt = datetime.utcfromtimestamp(created_at_ms / 1000.0) if created_at_ms else datetime.utcnow()

            # Tech stack extraction
            keywords_to_check = ["python", "react", "fastapi", "django", "node", "typescript", "aws", "docker", "kubernetes", "sql", "postgres", "c++", "rust", "graphql"]
            matched_skills = [k.capitalize() for k in keywords_to_check if k in description.lower() or k in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=description,
                department=team_str,
                location=norm_loc,
                city=city,
                region=region,
                country=country,
                remote_type=remote_type,
                employment_type=emp_type,
                experience_level="SENIOR" if "senior" in title.lower() else "MID",
                skills=matched_skills,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record
            )
        except Exception:
            return None
