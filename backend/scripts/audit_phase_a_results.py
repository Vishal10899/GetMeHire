import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import Source, Company, Job
from sqlalchemy import func

db = SessionLocal()
print("=" * 70)
print("PHASE A FINAL DATA RECONCILIATION AUDIT")
print("=" * 70)

total_sources = db.query(Source).count()
total_companies = db.query(Company).count()
total_jobs = db.query(Job).count()
active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()

print(f"Total Sources:   {total_sources}")
print(f"Total Companies: {total_companies}")
print(f"Total Jobs:      {total_jobs}")
print(f"  ACTIVE:         {active_jobs}")
print(f"  POSSIBLY_STALE: {stale_jobs}")
print(f"  CLOSED:         {closed_jobs}")

print("\nBreakdown by Source Type:")
for stype, count in db.query(Source.source_type, func.count(Job.id)).join(Job, Job.source_id == Source.id).group_by(Source.source_type).order_by(func.count(Job.id).desc()).all():
    print(f"  {stype:16}: {count} jobs")

print("\nPhase A New Sources Details:")
for s in db.query(Source).filter(Source.id >= 76).all():
    comp = db.query(Company).filter(Company.id == s.company_id).first()
    comp_name = comp.canonical_name if comp else "Unknown"
    jobs = db.query(Job).filter(Job.source_id == s.id).all()
    valid_urls = sum(1 for j in jobs if j.application_url and j.application_url.startswith("http"))
    valid_pct = (valid_urls / len(jobs) * 100) if jobs else 0
    print(f"\n  Source ID {s.id}: {s.source_name} ({s.source_type})")
    print(f"    Host Company: {comp_name} | Health: {s.health_status}")
    print(f"    Total Jobs: {len(jobs)} | Valid URL Percentage: {valid_pct:.1f}%")
    if jobs:
        j0 = jobs[0]
        # Check actual hiring company for j0
        hiring_comp = db.query(Company).filter(Company.id == j0.company_id).first()
        hname = hiring_comp.canonical_name if hiring_comp else comp_name
        print(f"    Sample Job: \"{j0.title}\"")
        print(f"      Hiring Employer: {hname}")
        print(f"      Location: {j0.location} | Remote: {j0.remote_type} | Country: {j0.country}")
        print(f"      Skills: {j0.skills[:5]}")
        print(f"      Application URL: {j0.application_url}")

# Verify original 15 sources are 100% intact
print("\n" + "=" * 70)
print("ORIGINAL 15 SOURCES INTEGRITY AUDIT")
print("=" * 70)
orig_sources = db.query(Source).filter(Source.id < 76).all()
print(f"Count of original sources: {len(orig_sources)}")
all_orig_healthy = all(s.health_status == "HEALTHY" for s in orig_sources)
print(f"All original sources HEALTHY: {all_orig_healthy}")
for s in sorted(orig_sources, key=lambda x: x.source_name):
    orig_job_count = db.query(Job).filter(Job.source_id == s.id).count()
    print(f"  - {s.source_name:32} ({s.source_type:10}): {orig_job_count:4} jobs | Health: {s.health_status}")

db.close()
