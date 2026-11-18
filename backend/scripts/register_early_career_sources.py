import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, Company
from sqlalchemy import text

db = SessionLocal()

new_candidates = [
    # (name, slug, adapter, url, industry, country)
    ("Oscar Health", "oscar", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/oscar/jobs", "Healthcare", "USA"),
    ("Maven Clinic", "mavenclinic", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/mavenclinic/jobs", "Healthcare", "USA"),
    ("Clover Health", "cloverhealth", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/cloverhealth/jobs", "Healthcare", "USA"),
    ("GeneDx", "genedx", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/genedx/jobs", "Healthcare & Genomics", "USA"),
    ("Affirm", "affirm", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/affirm/jobs", "Fintech & Banking", "USA"),
    ("Carta", "carta", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/carta/jobs", "Finance & Equity", "USA"),
    ("Gusto", "gusto", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/gusto/jobs", "Payroll & HR Tech", "USA"),
    ("Duolingo", "duolingo", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/duolingo/jobs", "EdTech & Language", "USA"),
    ("Databricks", "databricks", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/databricks/jobs", "Data & AI", "USA"),
    ("Cloudflare", "cloudflare", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs", "Cloud & Security", "USA"),
    ("Scale AI", "scaleai", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/scaleai/jobs", "Artificial Intelligence", "USA"),
    ("GitLab", "gitlab", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs", "DevOps & Software", "USA"),
    ("Reddit", "reddit", "GREENHOUSE", "https://boards-api.greenhouse.io/v1/boards/reddit/jobs", "Social Media & Tech", "USA"),
]

for name, slug, adapter, url, industry, country in new_candidates:
    # Check if company exists
    company = db.query(Company).filter(Company.canonical_name.ilike(name)).first()
    if not company:
        company = Company(
            canonical_name=name,
            website=f"https://www.{slug}.com",
            industry=industry,
            country=country
        )
        db.add(company)
        db.flush()
        print(f"[NEW COMPANY] Created company: {name} (ID: {company.id})")
    else:
        print(f"[EXISTING COMPANY] Found {name} (ID: {company.id})")

    # Check if source exists
    source = db.query(Source).filter(
        (Source.canonical_source_url == url) | 
        (Source.external_board_id == slug) |
        (Source.source_name == f"{name} Greenhouse")
    ).first()

    if not source:
        source = Source(
            source_name=f"{name} Greenhouse",
            company_id=company.id,
            source_type=adapter,
            canonical_source_url=url,
            external_board_id=slug,
            configuration={"board_token": slug, "industry": industry, "country": country},
            is_active=True,
            health_status="HEALTHY"
        )
        db.add(source)
        db.flush()
        print(f"[NEW SOURCE] Registered: {source.source_name} (ID: {source.id})")
    else:
        source.is_active = True
        source.health_status = "HEALTHY"
        source.configuration = {"board_token": slug, "industry": industry, "country": country}
        print(f"[EXISTING SOURCE] Updated & enabled: {source.source_name} (ID: {source.id})")

db.commit()
db.close()
print("\n[OK] All high-value sources registered & activated.")
