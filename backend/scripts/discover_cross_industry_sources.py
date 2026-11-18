"""
Discover and verify accessible public ATS career boards across multiple industries:
Healthcare, Finance, Retail, Logistics, Tech, Education, etc.
Probes:
- Greenhouse (https://boards-api.greenhouse.io/v1/boards/{slug}/jobs)
- Lever (https://api.lever.co/v0/postings/{slug}?mode=json)
- Ashby (https://api.ashbyhq.com/posting-api/job-board/{slug})
- SmartRecruiters (https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1)
"""

import httpx

candidates = [
    # HEALTHCARE & PHARMA / BIOTECH
    ("greenhouse", "onemedical", "One Medical", "Healthcare", "US"),
    ("greenhouse", "mavenclinic", "Maven Clinic", "Healthcare", "US"),
    ("greenhouse", "ro", "Ro Healthcare", "Healthcare", "US"),
    ("greenhouse", "cityblock", "Cityblock Health", "Healthcare", "US"),
    ("greenhouse", "ginkgobioworks", "Ginkgo Bioworks", "Biotechnology", "US"),
    ("greenhouse", "tempus", "Tempus Labs", "Healthcare", "US"),
    ("greenhouse", "oscar", "Oscar Health", "Healthcare", "US"),
    ("greenhouse", "flatiron", "Flatiron Health", "Healthcare", "US"),
    ("greenhouse", "guardanthealth", "Guardant Health", "Healthcare", "US"),
    ("lever", "springhealth", "Spring Health", "Healthcare", "US"),
    ("lever", "modernhealth", "Modern Health", "Healthcare", "US"),
    ("ashby", "headway", "Headway Health", "Healthcare", "US"),

    # FINANCE & FINTECH
    ("smartrecruiters", "wise", "Wise", "Fintech", "UK"),
    ("greenhouse", "robinhood", "Robinhood", "Fintech", "US"),
    ("greenhouse", "coinbase", "Coinbase", "Fintech", "US"),
    ("greenhouse", "brex", "Brex", "Fintech", "US"),
    ("greenhouse", "plaid", "Plaid", "Fintech", "US"),
    ("greenhouse", "affirm", "Affirm", "Fintech", "US"),
    ("greenhouse", "chime", "Chime", "Fintech", "US"),
    ("greenhouse", "gusto", "Gusto", "Fintech", "US"),
    ("greenhouse", "carta", "Carta", "Fintech", "US"),
    ("greenhouse", "ripple", "Ripple", "Fintech", "US"),
    ("ashby", "ramp", "Ramp", "Fintech", "US"),
    ("lever", "monzo", "Monzo Bank", "Banking", "UK"),

    # RETAIL & CONSUMER & HOSPITALITY
    ("greenhouse", "sweetgreen", "Sweetgreen", "Hospitality & Food", "US"),
    ("greenhouse", "warbyparker", "Warby Parker", "Retail", "US"),
    ("greenhouse", "glossier", "Glossier", "Retail", "US"),
    ("greenhouse", "allbirds", "Allbirds", "Retail", "US"),
    ("greenhouse", "doordash", "DoorDash", "Logistics & Food", "US"),
    ("greenhouse", "instacart", "Instacart", "Retail & Delivery", "US"),
    ("greenhouse", "wayfair", "Wayfair", "Retail & E-commerce", "US"),
    ("greenhouse", "coupang", "Coupang", "E-commerce", "South Korea"),

    # LOGISTICS & MANUFACTURING & HARDWARE
    ("greenhouse", "flexport", "Flexport", "Logistics", "US"),
    ("greenhouse", "samsara", "Samsara", "IoT & Fleet", "US"),
    ("greenhouse", "zipline", "Zipline", "Aviation & Logistics", "US"),
    ("greenhouse", "andurilindustries", "Anduril Industries", "Defense & Aerospace", "US"),
    ("greenhouse", "relativity", "Relativity Space", "Aerospace", "US"),
    ("smartrecruiters", "deliveryhero", "Delivery Hero", "Food Delivery", "Germany"),

    # EDUCATION & EDTECH
    ("greenhouse", "coursera", "Coursera", "Education", "US"),
    ("greenhouse", "duolingo", "Duolingo", "Education", "US"),
    ("greenhouse", "khanacademy", "Khan Academy", "Education", "US"),
    ("greenhouse", "udemy", "Udemy", "Education", "US"),
    ("greenhouse", "guildeducation", "Guild", "Education", "US"),
    ("greenhouse", "quizlet", "Quizlet", "Education", "US"),

    # ENTERPRISE & PROFESSIONAL SERVICES
    ("greenhouse", "ironclad", "Ironclad", "Legal Tech", "US"),
    ("greenhouse", "checkr", "Checkr", "HR & Background", "US"),
    ("greenhouse", "segment", "Twilio Segment", "Software", "US"),
    ("ashby", "openai", "OpenAI", "Artificial Intelligence", "US"),
    ("ashby", "anthropic", "Anthropic", "Artificial Intelligence", "US"),
    ("lever", "palantir", "Palantir Technologies", "Enterprise Software", "US"),
    ("lever", "atlassian", "Atlassian", "Software", "Australia"),
]

headers = {"User-Agent": "GetMeHirePlatform/2.0"}

results = []
for ats, slug, name, industry, country in candidates:
    url = ""
    if ats == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    elif ats == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    elif ats == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    elif ats == "smartrecruiters":
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1"

    try:
        r = httpx.get(url, headers=headers, timeout=10)
        count = 0
        if r.status_code == 200:
            if ats == "greenhouse":
                count = len(r.json().get("jobs", []))
            elif ats == "lever":
                count = len(r.json())
            elif ats == "ashby":
                count = len(r.json().get("jobs", []))
            elif ats == "smartrecruiters":
                count = r.json().get("totalFound", 0)
            
            results.append({
                "ats": ats.upper(),
                "slug": slug,
                "name": name,
                "industry": industry,
                "country": country,
                "url": url,
                "job_count": count
            })
            print(f"[FOUND] {name} ({industry}, {country}) on {ats.upper()}: {count} jobs")
        else:
            print(f"[NOT FOUND] {name} ({slug}) on {ats}: status {r.status_code}")
    except Exception as e:
        print(f"[ERROR] {name} ({slug}) on {ats}: {e}")

print(f"\nTotal Active Verified Candidate Boards Found: {len(results)}")
total_jobs = sum(r['job_count'] for r in results)
print(f"Total Discovered Vacancies on These Boards: {total_jobs}")

import json
with open("backend/discovered_candidate_sources.json", "w") as f:
    json.dump(results, f, indent=2)
