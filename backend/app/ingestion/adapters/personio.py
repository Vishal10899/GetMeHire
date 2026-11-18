import time
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

def safe_parse_xml(xml_content: str) -> ET.Element:
    """
    Secure XML parsing defending against XXE and entity expansion attacks.
    Explicitly rejects DTD and external entities before parsing.
    """
    lower_content = xml_content.lower()
    if "<!doctype" in lower_content or "<!entity" in lower_content:
        raise ValueError("Security violation: DTD and external entity declarations are prohibited in XML feeds")
    return ET.fromstring(xml_content)

class PersonioAdapter(SourceAdapter):
    """
    Adapter for Personio public XML job feeds.
    Fetches job listings from:
    https://{company_slug}.jobs.personio.de/xml?language=en
    or https://{company_slug}.jobs.personio.com/xml?language=en
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("board_url"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug")
        feed_domain = config.get("feed_domain", "de")

        if not company_slug and source_url:
            # Extract from e.g. https://personio.jobs.personio.de/xml or https://personio.jobs.personio.com
            host = source_url.split("/")[2] if "://" in source_url else source_url.split("/")[0]
            if ".jobs.personio." in host:
                company_slug = host.split(".jobs.personio.")[0]
                feed_domain = host.split(".jobs.personio.")[1].split("/")[0]
            else:
                company_slug = host.split(".")[0]

        if not company_slug:
            raise ValueError("Personio company_slug could not be determined from configuration or URL")

        # Determine primary and fallback URLs
        primary_url = config.get("board_url") or f"https://{company_slug}.jobs.personio.{feed_domain}/xml?language=en"
        fallback_domain = "com" if feed_domain == "de" else "de"
        fallback_url = f"https://{company_slug}.jobs.personio.{fallback_domain}/xml?language=en"

        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "text/xml, application/xml",
        }
        client_timeout = httpx.Timeout(30.0, connect=10.0)

        max_retries = 3
        backoff_seconds = 1.0
        xml_text = None

        with httpx.Client(timeout=client_timeout, follow_redirects=True) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(primary_url, headers=headers)
                    if resp.status_code == 404 and feed_domain != fallback_domain:
                        # Attempt fallback domain
                        resp_fallback = client.get(fallback_url, headers=headers)
                        if resp_fallback.status_code == 200:
                            resp = resp_fallback
                    if resp.status_code == 404:
                        raise Exception(f"Personio XML feed for '{company_slug}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Personio XML feed (HTTP 429)")
                    resp.raise_for_status()
                    xml_text = resp.text
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2
                        continue
                    raise

        if not xml_text:
            return [], {"completed": True}, False

        try:
            root = safe_parse_xml(xml_text)
        except Exception as e:
            raise ValueError(f"Failed to parse Personio XML feed: {e}")

        jobs_list = []
        positions = root.findall("position")
        for pos in positions:
            # Extract structured position data
            job_dict: Dict[str, Any] = {
                "_company_slug": company_slug,
                "_feed_domain": feed_domain,
                "id": pos.findtext("id"),
                "name": pos.findtext("name"),
                "office": pos.findtext("office"),
                "department": pos.findtext("department"),
                "subcompany": pos.findtext("subcompany"),
                "employmentType": pos.findtext("employmentType"),
                "seniority": pos.findtext("seniority"),
                "schedule": pos.findtext("schedule"),
                "createdAt": pos.findtext("createdAt"),
                "descriptions": [],
            }
            # Extract jobDescription blocks
            descs_elem = pos.find("jobDescriptions")
            if descs_elem is not None:
                for d in descs_elem.findall("jobDescription"):
                    d_name = d.findtext("name")
                    d_val = d.findtext("value")
                    job_dict["descriptions"].append({"name": d_name, "value": d_val})

            jobs_list.append(job_dict)

        return jobs_list, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id") or "").strip()
            title = (raw_record.get("name") or "").strip()
            if not external_id or not title:
                return None

            company_slug = raw_record.get("_company_slug") or "careers"
            feed_domain = raw_record.get("_feed_domain") or "de"

            # Construct clean description from structured jobDescription sections
            desc_html_parts = []
            for d in raw_record.get("descriptions", []):
                h_name = d.get("name")
                h_val = d.get("value")
                if h_name:
                    desc_html_parts.append(f"<h3>{h_name}</h3>")
                if h_val:
                    desc_html_parts.append(h_val)

            if desc_html_parts:
                soup = BeautifulSoup("\n".join(desc_html_parts), "html.parser")
                clean_desc = soup.get_text(separator="\n").strip()
            else:
                clean_desc = f"Open position for {title}."

            # Department
            dept_name = raw_record.get("department")

            # Location and country resolution
            office = raw_record.get("office") or "Europe"
            norm_loc, norm_city, norm_region, norm_country, detected_remote = normalize_location_and_country(
                office, title
            )

            # Employment type
            raw_emp = (raw_record.get("employmentType") or "full_time").lower()
            emp_type = "FULL_TIME"
            if "part" in raw_emp:
                emp_type = "PART_TIME"
            elif "freelance" in raw_emp or "contract" in raw_emp:
                emp_type = "CONTRACT"
            elif "intern" in raw_emp or "trainee" in raw_emp:
                emp_type = "INTERNSHIP"

            # Seniority
            seniority = (raw_record.get("seniority") or "").lower()
            exp_level = "MID"
            if "entry" in seniority or "junior" in seniority or "graduate" in seniority:
                exp_level = "ENTRY"
            elif "senior" in seniority or "lead" in seniority:
                exp_level = "SENIOR"
            elif "director" in seniority or "executive" in seniority:
                exp_level = "EXECUTIVE"

            # Canonical Application URL
            app_url = f"https://{company_slug}.jobs.personio.{feed_domain}/job/{external_id}"

            # Posting date
            created_str = raw_record.get("createdAt")
            posting_dt = datetime.utcnow()
            if created_str:
                try:
                    posting_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            # Taxonomy skills extraction
            tech_skills = [
                "python", "react", "fastapi", "django", "node", "typescript", "javascript",
                "aws", "docker", "kubernetes", "sql", "postgres", "golang", "java", "ruby",
                "ai", "machine learning", "product", "sales", "marketing", "devops", "erp"
            ]
            matched_skills = [s.capitalize() for s in tech_skills if s in clean_desc.lower() or s in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc,
                department=dept_name,
                location=norm_loc,
                city=norm_city,
                region=norm_region,
                country=norm_country,
                remote_type=detected_remote,
                employment_type=emp_type,
                experience_level=exp_level,
                skills=matched_skills,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None
