import re
import httpx
from typing import List, Tuple
from app.discovery.connectors.base import BaseDiscoveryConnector, DiscoveredCompanyCandidate
from app.discovery.normalizer import clean_company_name, extract_canonical_domain
from app.ingestion.normalizer import normalize_location_and_country

FALLBACK_OPEN_DIRECTORY = """
- [Automattic](https://automattic.com/work-with-us/) | Worldwide | Distributed / Remote
- [Basecamp](https://basecamp.com/about/jobs) | Chicago, IL, United States | Remote
- [Buffer](https://buffer.com/journey) | Worldwide | Remote
- [DuckDuckGo](https://duckduckgo.com/hiring) | Worldwide | Remote
- [Elastic](https://www.elastic.co/about/careers) | Mountain View, CA, United States | Distributed
- [GitLab](https://about.gitlab.com/jobs/) | Worldwide | All Remote
- [InVision](https://www.invisionapp.com/careers) | New York, NY, United States | Remote
- [Mozilla](https://careers.mozilla.org/) | Mountain View, CA, United States | Global Remote
- [Red Hat](https://www.redhat.com/en/jobs) | Raleigh, NC, United States | Global
- [Canonical](https://canonical.com/careers) | London, United Kingdom | Remote
- [TransferWise](https://wise.com/jobs) | London, United Kingdom | Global
- [ThoughtWorks](https://www.thoughtworks.com/careers) | Chicago, IL, United States | Global
- [Postman](https://www.postman.com/company/careers/) | Bengaluru, India | Hybrid / Remote
- [Canva](https://www.canva.com/careers/) | Sydney, Australia | Hybrid
- [Atlassian](https://www.atlassian.com/company/careers) | Sydney, Australia | Distributed
- [Doist](https://doist.com/careers) | Worldwide | Remote
- [Ghost](https://ghost.org/careers/) | Worldwide | Remote
- [Zapier](https://zapier.com/jobs/) | Worldwide | Remote
- [Gofore](https://gofore.com/en/careers/) | Helsinki, Finland | Europe
- [Netcentric](https://www.netcentric.biz/careers.html) | Zurich, Switzerland | Europe
- [Olark](https://www.olark.com/jobs/) | Ann Arbor, MI, United States | Remote
- [Simple](https://www.simple.com/careers) | Portland, OR, United States | North America
- [Toggl](https://toggl.com/jobs/) | Tallinn, Estonia | Remote
- [Travis CI](https://travis-ci.com/careers) | Berlin, Germany | Remote
- [Clever](https://clever.com/about/careers) | San Francisco, CA, United States | Remote
- [DigitalOcean](https://www.digitalocean.com/careers) | New York, NY, United States | Remote
- [Fastly](https://www.fastly.com/about/careers) | San Francisco, CA, United States | Global
- [HashiCorp](https://www.hashicorp.com/jobs) | San Francisco, CA, United States | Remote
- [Heroku](https://www.heroku.com/careers) | San Francisco, CA, United States | Remote
- [Honeycomb](https://www.honeycomb.io/careers/) | San Francisco, CA, United States | Remote
- [HubSpot](https://www.hubspot.com/careers) | Cambridge, MA, United States | Hybrid
- [Medium](https://medium.com/jobs-at-medium) | San Francisco, CA, United States | Hybrid
- [PagerDuty](https://www.pagerduty.com/careers/) | San Francisco, CA, United States | Global
- [Pivotal](https://pivotal.io/careers) | San Francisco, CA, United States | Global
- [Prezi](https://prezi.com/jobs/) | Budapest, Hungary | Europe
- [Rackspace](https://jobs.jobvite.com/rackspace) | San Antonio, TX, United States | Global
- [Stripe](https://stripe.com/jobs) | San Francisco, CA, United States | Global
- [Twilio](https://www.twilio.com/company/jobs) | San Francisco, CA, United States | Global
- [Viget](https://www.viget.com/careers) | Falls Church, VA, United States | Remote
- [Wildbit](https://wildbit.com/about) | Philadelphia, PA, United States | Remote
"""

class OpenDirectoryConnector(BaseDiscoveryConnector):
    """
    Ingests genuine international technology and enterprise employers from curated
    open-source hiring directories (e.g., Hiring Without Whiteboards, 770+ international companies).
    """

    @property
    def source_name(self) -> str:
        return "Open Hiring Directory (International)"

    def discover(self, limit: int = 1000) -> List[DiscoveredCompanyCandidate]:
        url = "https://raw.githubusercontent.com/poteto/hiring-without-whiteboards/master/README.md"
        headers = {
            "User-Agent": "GetMeHire-DiscoveryPlatform bot@getmehire.com (+https://getmehire.com/terms; public indexer)",
            "Accept": "text/plain, text/markdown"
        }

        candidates = []
        text = ""
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200 and len(resp.text) > 500:
                    text = resp.text
        except Exception:
            pass

        if not text:
            text = FALLBACK_OPEN_DIRECTORY

        lines = text.split("\n")
        for line in lines:
            if len(candidates) >= limit:
                break
            # Match lines like: - [Accenture](https://www.accenture.com/careers) | San Francisco, CA | Notes
            match = re.match(r"^-\s+\[([^\]]+)\]\((https?://[^\)]+)\)(?:\s*\|\s*([^\|]+))?", line.strip())
            if not match:
                continue

            raw_name = match.group(1).strip()
            url_target = match.group(2).strip()
            raw_loc = (match.group(3) or "").strip()

            canonical_name = clean_company_name(raw_name)
            if not canonical_name:
                continue

            domain = extract_canonical_domain(url_target)
            is_career = any(w in url_target.lower() for w in ["career", "job", "ats", "greenhouse", "lever", "ashby"])

            # Determine location and country
            country = "United States"
            operating_region = "North America"
            if raw_loc:
                _, _, reg, ctry, _ = normalize_location_and_country(raw_loc, "")
                if ctry and ctry != "United States":
                    country = ctry
                    if country in ["United Kingdom", "Germany", "France", "Netherlands", "Poland", "Sweden", "Switzerland", "Spain", "Italy", "Ireland", "Finland", "Estonia", "Hungary"]:
                        operating_region = "Europe"
                    elif country in ["India", "Pakistan", "Bangladesh"]:
                        operating_region = "South Asia"
                    elif country in ["Singapore", "Malaysia", "Indonesia", "Vietnam", "Philippines", "Thailand"]:
                        operating_region = "Southeast Asia"
                    elif country in ["Japan", "China", "South Korea", "Taiwan"]:
                        operating_region = "East Asia"
                    elif country in ["Brazil", "Argentina", "Colombia", "Peru", "Chile", "Mexico"]:
                        operating_region = "South America"
                    elif country in ["Australia", "New Zealand"]:
                        operating_region = "Oceania"
                    elif country in ["South Africa", "Nigeria", "Kenya", "Egypt", "Ghana"]:
                        operating_region = "Africa"
                    elif country in ["Israel", "United Arab Emirates", "Saudi Arabia", "Turkey"]:
                        operating_region = "Middle East"

            candidate = DiscoveredCompanyCandidate(
                name=canonical_name,
                domain=domain,
                website=url_target if not is_career else (f"https://{domain}" if domain else url_target),
                career_page_url=url_target if is_career else None,
                country=country,
                operating_region=operating_region,
                industry="Software & IT",
                discovery_source="OPEN_HIRING_DIRECTORY",
                aliases=[raw_name] if raw_name != canonical_name else [],
                metadata={
                    "raw_location": raw_loc,
                    "curated_directory": "hiring-without-whiteboards"
                }
            )
            candidates.append(candidate)

        return candidates
