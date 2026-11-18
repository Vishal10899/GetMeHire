import html
import re
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_full

class GreenhouseAdapter(SourceAdapter):
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("board_token") or config.get("board_url"))

    def fetch_page(self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        board_token = config.get("board_token") or config.get("board_id")
        if not board_token and source_url:
            match = re.search(r"(?:boards|boards-api)\.greenhouse\.io/(?:v1/boards/)?([a-zA-Z0-9_\-]+)", source_url)
            if match:
                board_token = match.group(1)
            else:
                parts = source_url.rstrip("/").split("/")
                board_token = parts[-1].split("?")[0]

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        headers = {"User-Agent": "JobDiscoveryPlatform/2.0 (+https://example.com/bot)"}

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 429:
                raise Exception("Rate limit exceeded (HTTP 429)")
            if resp.status_code == 404:
                raise Exception("Greenhouse board not found (HTTP 404)")
            resp.raise_for_status()
            data = resp.json()

        jobs_list = data.get("jobs", [])
        # Greenhouse returns all jobs in one payload
        return jobs_list, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id"))
            title = raw_record.get("title", "").strip()
            if not external_id or not title:
                return None

            raw_content = raw_record.get("content", "")
            unescaped = html.unescape(raw_content) if raw_content else ""
            soup = BeautifulSoup(unescaped, "html.parser")
            clean_desc = soup.get_text(separator="\n").strip()
            clean_text_only = re.sub(r"[^\w\s]", "", clean_desc).strip()
            if not clean_text_only or len(clean_text_only) < 5:
                clean_desc = f"Opportunity for {title}. Please review the official application page for full responsibilities and qualifications."

            location_data = raw_record.get("location", {})
            location_str = location_data.get("name") if isinstance(location_data, dict) else str(location_data)

            # Deterministic location and country normalization
            norm_loc, city, region, country, code, remote_type = normalize_location_full(location_str, title)

            # Departments
            departments = raw_record.get("departments", [])
            dept_name = departments[0].get("name") if departments and isinstance(departments[0], dict) else None

            # Posting date
            updated_at = raw_record.get("updated_at")
            posting_dt = None
            if updated_at:
                try:
                    posting_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            title_lower = title.lower()

            # Extracted keywords/skills
            keywords_to_check = ["python", "react", "fastapi", "django", "node", "typescript", "aws", "docker", "kubernetes", "sql", "postgres", "go", "java"]
            matched_skills = [k.capitalize() for k in keywords_to_check if k in clean_desc.lower() or k in title_lower]

            app_url = raw_record.get("absolute_url") or f"https://boards.greenhouse.io/jobs/{external_id}"

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc if clean_desc else title,
                department=dept_name,
                location=norm_loc,
                city=city,
                region=region,
                country=country,
                country_code=code,
                remote_type=remote_type,
                employment_type="FULL_TIME",
                experience_level="MID" if "senior" not in title_lower else "SENIOR",
                skills=matched_skills,
                posting_date=posting_dt or datetime.utcnow(),
                application_url=app_url,
                raw_data=raw_record
            )
        except Exception:
            return None
