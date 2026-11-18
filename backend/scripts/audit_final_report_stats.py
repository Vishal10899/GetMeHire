import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import Job, Company, Source
from sqlalchemy import func

def audit():
    db = SessionLocal()
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
    stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
    closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()
    total_comps = db.query(Company).count()
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active == True).count()

    print(f"TOTAL_JOBS: {total_jobs}")
    print(f"ACTIVE_JOBS: {active_jobs}")
    print(f"STALE_JOBS: {stale_jobs}")
    print(f"CLOSED_JOBS: {closed_jobs}")
    print(f"TOTAL_COMPANIES: {total_comps}")
    print(f"TOTAL_SOURCES: {total_sources} ({active_sources} active)")

    print("\n--- COUNTRY BREAKDOWN ---")
    countries = (
        db.query(Job.country, Job.country_code, func.count(Job.id))
        .group_by(Job.country, Job.country_code)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    for c, code, cnt in countries:
        pct = (cnt / total_jobs) * 100
        print(f"  {code or '--'}: {c or 'Unspecified/Remote'} -> {cnt} ({pct:.2f}%)")

    unspecified = db.query(func.count(Job.id)).filter(Job.country.is_(None)).scalar()
    print(f"\nTotal Unspecified/Remote: {unspecified} ({unspecified/total_jobs*100:.2f}%)")
    print(f"Total Country-Coded: {total_jobs - unspecified} ({(total_jobs - unspecified)/total_jobs*100:.2f}%)")

    print("\n--- PROFESSIONS / CATEGORIES BREAKDOWN ---")
    profs = (
        db.query(Job.profession, func.count(Job.id))
        .group_by(Job.profession)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    for p, cnt in profs:
        pct = (cnt / total_jobs) * 100
        print(f"  {p or 'UNKNOWN'}: {cnt} ({pct:.2f}%)")

    print("\n--- REMOTE BREAKDOWN ---")
    remotes = (
        db.query(Job.remote_type, func.count(Job.id))
        .group_by(Job.remote_type)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    for r, cnt in remotes:
        pct = (cnt / total_jobs) * 100
        print(f"  {r}: {cnt} ({pct:.2f}%)")

    print("\n--- NEW COMPANIES VERIFIED ---")
    new_comps = ["On Running", "Duolingo", "Komodo Health", "Toast", "Monzo"]
    for nc in new_comps:
        comp = db.query(Company).filter(Company.canonical_name == nc).first()
        if comp:
            cjobs = db.query(Job).filter(Job.company_id == comp.id).count()
            cactive = db.query(Job).filter(Job.company_id == comp.id, Job.status == "ACTIVE").count()
            print(f"  {nc} (ID: {comp.id}): {cjobs} total jobs ({cactive} active)")

    db.close()

if __name__ == "__main__":
    audit()
