import httpx
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from datetime import datetime
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country, clean_html_markup, get_country_code

def is_allowed_by_robots(url: str, user_agent: str = "GetMeHireBot") -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(robots_url)
            if resp.status_code == 200:
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
                return rp.can_fetch(user_agent, url)
        return True
    except Exception:
        return True

class WebScraperAdapter(SourceAdapter):
    """
    Level 4 HTML & JSON-LD Career Page Extractor:
    - Parses structured schema.org/JobPosting JSON-LD when present.
    - Extracts authentic vacancy links and semantic parent cards from HTML.
    - Follows pagination links (rel="next", ?page=X, pagination anchors).
    - Fully adheres to robots.txt permissions.
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        base_url = config.get("career_page_url") or source_url
        current_url = checkpoint.get("next_url") or base_url
        page_num = int(checkpoint.get("page_num", 1))
        visited_urls = set(checkpoint.get("visited_urls", []))
        visited_urls.add(current_url)

        user_agent = "GetMeHireBot/2.0 (+https://getmehire.com/bot; permitted indexer)"

        # 1. Robots.txt Compliance Check
        if not is_allowed_by_robots(current_url, user_agent="GetMeHireBot"):
            raise Exception(f"Crawling disallowed by robots.txt for: {current_url}")

        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(current_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        extracted_jobs = []
        seen_job_urls = set()

        # 2. Extract JSON-LD JobPosting schema (Gold standard for career page indexing)
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                if not script.string:
                    continue
                data = json.loads(script.string.strip())
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        items = [data]
                    elif "@graph" in data and isinstance(data["@graph"], list):
                        items = [x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "JobPosting"]

                for item in items:
                    title = (item.get("title") or item.get("name") or "").strip()
                    job_url = item.get("url") or item.get("sameAs") or current_url
                    if job_url:
                        job_url = urljoin(current_url, job_url)
                    if title and job_url not in seen_job_urls:
                        seen_job_urls.add(job_url)
                        extracted_jobs.append({
                            "type": "json_ld",
                            "title": title,
                            "url": job_url,
                            "json_ld_data": item,
                            "parent_text": item.get("description", "")
                        })
            except Exception:
                continue

        # 3. HTML Anchor & Semantic Card Extraction (Fallback/Supplement)
        if len(extracted_jobs) == 0:
            links = soup.find_all("a", href=True)
            for a in links:
                href = a["href"].strip()
                text = a.get_text(separator=" ", strip=True)
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                full_url = urljoin(current_url, href)

                # Identify job detail links by path heuristics
                is_job_path = any(term in full_url.lower() for term in [
                    "/job/", "/jobs/", "/career/", "/careers/", "/position/", "/positions/",
                    "/openings/", "/vacancy/", "/vacancies/", "/role/", "/opportunity/"
                ])
                # Filter out generic listing / top-level index pages
                is_index_only = full_url.rstrip("/") in [base_url.rstrip("/"), current_url.rstrip("/")]

                if is_job_path and not is_index_only and len(text) > 3 and full_url not in seen_job_urls:
                    seen_job_urls.add(full_url)
                    parent_text = a.parent.get_text(separator=" ", strip=True) if a.parent else ""
                    extracted_jobs.append({
                        "type": "html_link",
                        "title": text,
                        "url": full_url,
                        "parent_text": parent_text
                    })

        # 4. Multi-page Pagination Link Discovery
        next_url = None
        # Heuristic A: <link rel="next"> or <a rel="next">
        next_link = soup.find(["link", "a"], rel=lambda r: r and "next" in r.lower())
        if next_link and next_link.get("href"):
            candidate = urljoin(current_url, next_link["href"])
            if candidate not in visited_urls:
                next_url = candidate

        # Heuristic B: Anchor text matching Next / Next Page / >
        if not next_url:
            for a in soup.find_all("a", href=True):
                txt = a.get_text(strip=True).lower()
                aria = (a.get("aria-label") or "").lower()
                if txt in ["next", "next page", "›", "»", "older", "next >", ">"] or "next" in aria:
                    candidate = urljoin(current_url, a["href"])
                    if candidate not in visited_urls and candidate != current_url:
                        next_url = candidate
                        break

        # Heuristic C: Parameterized query ?page=X if extracted items found
        if not next_url and len(extracted_jobs) >= 5 and page_num < 10:
            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            if "page" in query_params:
                try:
                    cur_p = int(query_params["page"][0])
                    query_params["page"] = [str(cur_p + 1)]
                    new_query = urlencode(query_params, doseq=True)
                    candidate = urlunparse(parsed._replace(query=new_query))
                    if candidate not in visited_urls:
                        next_url = candidate
                except Exception:
                    pass

        max_scraper_pages = int(config.get("max_pages", 50))
        has_more = bool(next_url and page_num < max_scraper_pages)
        next_checkpoint = {
            "page_num": page_num + 1,
            "next_url": next_url,
            "visited_urls": list(visited_urls),
            "completed": not has_more
        }

        return extracted_jobs, next_checkpoint, has_more

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            record_type = raw_record.get("type", "html_link")
            title = raw_record.get("title", "").strip()
            url = raw_record.get("url", "")
            if not title or not url:
                return None

            path_parts = [p for p in urlparse(url).path.split("/") if p]
            path_id = path_parts[-1] if path_parts else str(abs(hash(url)))
            external_id = f"scrape-{path_id}"

            desc = raw_record.get("parent_text") or f"Opportunity for {title}. Please review the official posting."
            clean_desc = clean_html_markup(desc) if desc else title
            if len(clean_desc.strip()) < 5:
                clean_desc = f"Opportunity for {title}. Please review the official application page for full requirements."

            location_raw = ""
            emp_type = "FULL_TIME"
            salary_min = None
            salary_max = None
            salary_currency = "USD"
            posting_dt = datetime.utcnow()

            # Enrich from JSON-LD if available
            if record_type == "json_ld":
                ld = raw_record.get("json_ld_data", {})
                ld_desc = ld.get("description")
                if ld_desc:
                    clean_desc = clean_html_markup(ld_desc)

                ld_loc = ld.get("jobLocation", {})
                if isinstance(ld_loc, dict):
                    addr = ld_loc.get("address", {})
                    if isinstance(addr, dict):
                        loc_parts = [
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("addressCountry")
                        ]
                        location_raw = ", ".join([str(p).strip() for p in loc_parts if p])
                    elif isinstance(addr, str):
                        location_raw = addr

                # Salary
                base_sal = ld.get("baseSalary", {})
                if isinstance(base_sal, dict):
                    val = base_sal.get("value", {})
                    salary_currency = base_sal.get("currency") or "USD"
                    if isinstance(val, dict):
                        salary_min = val.get("minValue")
                        salary_max = val.get("maxValue")
                    elif isinstance(val, (int, float)):
                        salary_min = float(val)

                # Date
                d_posted = ld.get("datePosted")
                if d_posted:
                    try:
                        posting_dt = datetime.fromisoformat(str(d_posted).replace("Z", "+00:00"))
                    except Exception:
                        pass

            norm_loc, city, region, country, detected_remote = normalize_location_and_country(location_raw, title)
            if "remote" in title.lower() or "remote" in clean_desc.lower():
                detected_remote = "REMOTE"
            elif "hybrid" in title.lower() or "hybrid" in clean_desc.lower():
                detected_remote = "HYBRID"

            keywords = [
                "python", "react", "fastapi", "django", "node", "typescript",
                "aws", "docker", "kubernetes", "sql", "postgresql", "go", "java",
                "sales", "marketing", "finance", "accounting", "hr", "operations"
            ]
            skills = [k.capitalize() for k in keywords if k in clean_desc.lower() or k in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc,
                location=norm_loc or "Unspecified",
                city=city,
                region=region,
                country=country,
                country_code=get_country_code(country),
                remote_type=detected_remote,
                employment_type=emp_type,
                skills=skills,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                posting_date=posting_dt,
                application_url=url,
                raw_data=raw_record
            )
        except Exception:
            return None
