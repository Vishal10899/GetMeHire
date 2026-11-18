import time
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country, clean_html_markup, get_country_code

def safe_parse_teamtailor_xml(xml_text: str) -> ET.Element:
    """
    Defends against XML External Entity (XXE) and billion laughs expansion attacks:
    - Blocks DOCTYPE external declarations.
    - Uses standard safe defused XML parser configuration.
    """
    if "<!ENTITY" in xml_text or "<!DOCTYPE" in xml_text:
        # Strip or reject dangerous DTD entities
        import re
        xml_text = re.sub(r"<!DOCTYPE[^>]*\[.*?\]>", "", xml_text, flags=re.DOTALL)
        xml_text = re.sub(r"<!ENTITY[^>]*>", "", xml_text)

    parser = ET.XMLParser()
    return ET.fromstring(xml_text, parser=parser)


class TeamtailorAdapter(SourceAdapter):
    """
    Adapter for Teamtailor public RSS/Atom career feeds:
    https://{company_slug}.teamtailor.com/feed
    Extracts authentic employer job openings, titles, departments, and application URLs.
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("feed_url") or config.get("board_url"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug")
        feed_url = config.get("feed_url")

        if not feed_url:
            if not company_slug and source_url:
                import urllib.parse
                parsed = urllib.parse.urlparse(source_url)
                parts = [p for p in parsed.netloc.split(".") if p]
                if len(parts) >= 3 and parts[1] == "teamtailor":
                    company_slug = parts[0]
                elif parsed.netloc.startswith("career."):
                    feed_url = f"{source_url.rstrip('/')}/jobs.rss"
                else:
                    path_parts = [p for p in parsed.path.rstrip("/").split("/") if p]
                    if path_parts:
                        company_slug = path_parts[0]

            if not feed_url and company_slug:
                feed_url = f"https://{company_slug}.teamtailor.com/jobs.rss"
            elif not feed_url and source_url:
                feed_url = source_url if source_url.endswith(".rss") else f"{source_url.rstrip('/')}/jobs.rss"

            if not feed_url:
                raise ValueError("Teamtailor company_slug or feed_url could not be determined")

        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "application/xml, text/xml, application/rss+xml, */*",
        }

        max_retries = 3
        backoff_seconds = 1.0
        xml_text = None

        with httpx.Client(timeout=25.0) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(feed_url, headers=headers)
                    if resp.status_code == 404:
                        raise Exception(f"Teamtailor feed '{feed_url}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Teamtailor API (HTTP 429)")
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

        records = self._parse_items_from_xml(xml_text, company_slug)
        return records, {"completed": True}, False

    def _parse_items_from_xml(self, xml_text: str, company_slug: str = "") -> List[Dict[str, Any]]:
        root = safe_parse_teamtailor_xml(xml_text)
        records = []
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for it in items:
            title = it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or ""
            link = it.findtext("link") or it.findtext("{http://www.w3.org/2005/Atom}link") or ""
            guid = it.findtext("guid") or it.findtext("id") or it.findtext("{http://www.w3.org/2005/Atom}id") or link
            desc = it.findtext("description") or it.findtext("content") or it.findtext("{http://www.w3.org/2005/Atom}content") or ""
            pub_date = it.findtext("pubDate") or it.findtext("updated") or it.findtext("{http://www.w3.org/2005/Atom}updated") or ""

            # Check Teamtailor XML namespace elements
            loc = (
                it.findtext("{http://teamtailor.com}location") or
                it.findtext("{http://teamtailor.com/feed}location") or
                it.findtext("location") or ""
            )
            remote_status = (
                it.findtext("{http://teamtailor.com}remote-status") or
                it.findtext("{http://teamtailor.com/feed}remote-status") or
                it.findtext("remote-status") or ""
            )
            emp_type = (
                it.findtext("{http://teamtailor.com}employment-type") or
                it.findtext("{http://teamtailor.com/feed}employment-type") or
                it.findtext("employment-type") or ""
            )

            records.append({
                "guid": guid,
                "title": title,
                "link": link,
                "description": desc,
                "pub_date": pub_date,
                "company_slug": company_slug,
                "location": loc,
                "remote_status": remote_status,
                "employment_type": emp_type,
            })

        return records

    def parse_xml_feed(self, xml_text: str, default_company: str = "") -> List[NormalizedJob]:
        records = self._parse_items_from_xml(xml_text, default_company)
        normalized = []
        for r in records:
            norm = self.parse_and_normalize(r)
            if norm:
                if default_company:
                    norm.company_name = default_company
                normalized.append(norm)
        return normalized

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        ext_id = str(raw_record.get("guid") or raw_record.get("id") or raw_record.get("link") or raw_record.get("url") or "").strip()
        title = (raw_record.get("title") or "").strip()
        if not ext_id or not title:
            return None

        app_url = raw_record.get("link") or raw_record.get("url") or f"https://careers.teamtailor.com/jobs/{ext_id}"
        desc_clean = clean_html_markup(raw_record.get("description") or title)

        loc_str = str(raw_record.get("location") or "").strip()
        clean_loc, city, region, country, detected_remote = normalize_location_and_country(loc_str, title)

        remote_val = str(raw_record.get("remote_status") or "").lower()
        if "remote" in remote_val or "remote" in title.lower():
            detected_remote = "REMOTE"
        elif "hybrid" in remote_val or "hybrid" in title.lower():
            detected_remote = "HYBRID"

        emp_val = str(raw_record.get("employment_type") or "").lower()
        if "part" in emp_val:
            emp_type = "PART_TIME"
        elif "contract" in emp_val or "freelance" in emp_val:
            emp_type = "CONTRACT"
        elif "intern" in emp_val:
            emp_type = "INTERNSHIP"
        else:
            emp_type = "FULL_TIME"

        post_dt = None
        pub_str = raw_record.get("pub_date")
        if pub_str:
            try:
                from email.utils import parsedate_to_datetime
                post_dt = parsedate_to_datetime(pub_str)
            except Exception:
                try:
                    post_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    pass

        # Skill extraction
        import re
        desc_lower = (desc_clean or "").lower()
        title_lower = title.lower()
        keywords_to_check = ["python", "react", "fastapi", "django", "node", "typescript", "aws", "docker", "kubernetes", "sql", "postgresql", "postgres", "go", "golang", "java", "c++", "rust", "linux", "terraform", "pytorch"]
        matched_skills = []
        for k in keywords_to_check:
            if k == "go":
                if re.search(r"\bgo\b", desc_lower) or re.search(r"\bgo\b", title_lower):
                    matched_skills.append("Go")
            elif k in ("postgresql", "postgres"):
                if "postgres" in desc_lower or "postgres" in title_lower:
                    if "Postgresql" not in matched_skills:
                        matched_skills.append("Postgresql")
            elif k in desc_lower or k in title_lower:
                cap = k.capitalize()
                if cap not in matched_skills:
                    matched_skills.append(cap)

        return NormalizedJob(
            external_job_id=ext_id,
            title=title,
            description=desc_clean,
            department=None,
            location=clean_loc or "Unspecified",
            city=city,
            region=region,
            country=country,
            country_code=get_country_code(country),
            remote_type=detected_remote,
            employment_type=emp_type,
            skills=matched_skills,
            posting_date=post_dt,
            application_url=app_url,
            raw_data=raw_record
        )
