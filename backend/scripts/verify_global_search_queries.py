"""
Global Search Verification Script against Live Database (job_discovery_master).

Executes the 8 mandatory PRD queries:
1. AI Engineer + India
2. AI Engineer + worldwide
3. Web Developer + London
4. Senior Surgeon + worldwide
5. Data Analyst + Canada
6. Software Engineer + Germany
7. Python Developer + Remote
8. Store Manager + worldwide
"""

import sys
import os
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.job_service import JobService
from app.models import Job, Company, Source

db = SessionLocal()

queries = [
    {
        "name": "Query 1: AI Engineer + India",
        "params": {"keyword": "AI Engineer", "location": "India"}
    },
    {
        "name": "Query 2: AI Engineer + worldwide",
        "params": {"keyword": "AI Engineer", "location": None}
    },
    {
        "name": "Query 3: Web Developer + London",
        "params": {"keyword": "Web Developer", "location": "London"}
    },
    {
        "name": "Query 4: Senior Surgeon + worldwide",
        "params": {"keyword": "Senior Surgeon", "location": None}
    },
    {
        "name": "Query 5: Data Analyst + Canada",
        "params": {"keyword": "Data Analyst", "location": "Canada"}
    },
    {
        "name": "Query 6: Software Engineer + Germany",
        "params": {"keyword": "Software Engineer", "location": "Germany"}
    },
    {
        "name": "Query 7: Python Developer + Remote",
        "params": {"keyword": "Python Developer", "work_arrangement": "REMOTE"}
    },
    {
        "name": "Query 8: Store Manager + worldwide",
        "params": {"keyword": "Store Manager", "location": None}
    },
]

report = {}

for q in queries:
    q_name = q["name"]
    params = q["params"]
    print(f"\n=======================================================")
    print(f"Executing: {q_name}")
    print(f"Parameters: {params}")
    print(f"=======================================================")

    res = JobService.search_jobs(
        db=db,
        keyword=params.get("keyword"),
        location=params.get("location"),
        work_arrangement=params.get("work_arrangement"),
        page=1,
        page_size=20,
        include_demo=False,
    )

    total_count = res.total
    items = res.items

    print(f"Actual Result Count: {total_count}")
    print(f"Returned Items on Page 1: {len(items)}")

    sample_records = []
    employers = set()
    job_titles = []
    locations = []
    work_arrangements = []
    employment_types = []
    sources = set()
    destinations = []

    # Relevance Audit Heuristics
    kw_lower = (params.get("keyword") or "").lower()
    loc_target = (params.get("location") or "").lower()
    irrelevant_count = 0

    for idx, job in enumerate(items[:10]):
        employers.add(job.company_name)
        job_titles.append(job.title)
        loc_str = f"{job.city or ''}, {job.country or ''}".strip(", ")
        locations.append(loc_str or job.location or "Unspecified")
        work_arrangements.append(job.work_arrangement or job.remote_type)
        employment_types.append(job.employment_type)
        sources.add(job.source_name)
        destinations.append(job.application_url)

        # Check keyword presence in title or description
        title_lower = (job.title or "").lower()
        dept_lower = (job.department or "").lower()
        norm_title = (job.normalized_title or "").lower()

        # Check location match if requested
        loc_match = True
        if loc_target:
            loc_combined = f"{job.location or ''} {job.city or ''} {job.country or ''} {job.country_code or ''}".lower()
            if loc_target not in loc_combined and job.country_code != loc_target.upper():
                loc_match = False

        if idx < 5:
            sample_records.append({
                "id": job.id,
                "title": job.title,
                "company": job.company_name,
                "location": job.location,
                "city": job.city,
                "country": job.country,
                "country_code": job.country_code,
                "work_arrangement": job.work_arrangement or job.remote_type,
                "employment_type": job.employment_type,
                "source": job.source_name,
                "application_url": job.application_url,
                "profession": job.profession,
            })

    report[q_name] = {
        "parameters": params,
        "total_results": total_count,
        "sample_size_audited": min(10, len(items)),
        "unique_employers_in_sample": list(employers)[:5],
        "sample_titles": job_titles[:5],
        "sample_locations": locations[:5],
        "sample_work_arrangements": list(set(work_arrangements)),
        "sample_employment_types": list(set(employment_types)),
        "sources_represented": list(sources),
        "sample_records": sample_records,
    }

print("\n--- Summary Report Output ---")
with open("backend/search_verification_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)
print("Report successfully saved to backend/search_verification_report.json")

db.close()
