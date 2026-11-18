from app.core.database import SessionLocal
from app.models import Job, Source, Company
from app.ingestion.taxonomy import TAXONOMY_FAMILIES
from urllib.parse import urlparse

db = SessionLocal()

print("=== LIVE JOB QUALITY AUDIT ACROSS ALL SOURCES & FAMILIES ===\n")

total_jobs = db.query(Job).count()
active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()

print(f"Total Stored Jobs: {total_jobs}")
print(f"Status Breakdown: ACTIVE={active_jobs}, POSSIBLY_STALE={stale_jobs}, CLOSED={closed_jobs}\n")

# Check missing required fields
missing_titles = db.query(Job).filter((Job.title == None) | (Job.title == "")).count()
missing_urls = db.query(Job).filter((Job.application_url == None) | (Job.application_url == "")).count()
missing_desc = db.query(Job).filter((Job.description == None) | (Job.description == "")).count()
missing_prof = db.query(Job).filter((Job.profession == None) | (Job.profession == "")).count()

print(f"Missing Fields Audit:")
print(f"  Missing Title: {missing_titles}")
print(f"  Missing Application URL: {missing_urls}")
print(f"  Missing Description: {missing_desc}")
print(f"  Missing Profession: {missing_prof}\n")

print("--- Source-by-Source Audit ---")
sources = db.query(Source).all()
for s in sources:
    jobs_count = db.query(Job).filter(Job.source_id == s.id).count()
    sample = db.query(Job).filter(Job.source_id == s.id).first()
    if sample:
        parsed_url = urlparse(sample.application_url or "")
        valid_host = bool(parsed_url.netloc and parsed_url.scheme in ["http", "https"])
        print(f"Source: {s.source_name} ({s.source_type})")
        print(f"  Job Count: {jobs_count} | Active: {s.is_active}")
        print(f"  Sample: '{sample.normalized_title or sample.title}' ({sample.profession}, Conf: {sample.classification_confidence})")
        print(f"  Apply URL Host: {parsed_url.netloc} (Valid: {valid_host})")
        print(f"  Location: '{sample.location}' | Has Summary: {bool(sample.system_summary)}")
        print("-" * 50)

print("\n--- Profession Families Quality Audit (14 tracks) ---")
for f_key in sorted(TAXONOMY_FAMILIES.keys()):
    f_count = db.query(Job).filter(Job.profession == f_key).count()
    f_sample = db.query(Job).filter(Job.profession == f_key).first()
    if f_sample:
        company_name = f_sample.company.canonical_name if f_sample.company else "Unknown"
        print(f"Family: {f_key} ({f_count} listings)")
        print(f"  Sample Job: '{f_sample.normalized_title or f_sample.title}' at {company_name}")
        print(f"  Confidence: {f_sample.classification_confidence} | Raw Title: '{f_sample.title}'")
        print(f"  Apply URL: {f_sample.application_url[:65]}...")
