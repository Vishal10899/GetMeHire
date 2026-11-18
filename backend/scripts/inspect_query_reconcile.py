import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job, Company
from sqlalchemy import func, or_

db = SessionLocal()

print("--- DATA ANALYST / ANALYTICS IN INDIA ---")
jobs = db.query(Job).filter(
    Job.country.ilike("%India%"),
    or_(Job.title.ilike("%Analyst%"), Job.title.ilike("%Data%"))
).all()
print(f"Total Analyst/Data jobs in India: {len(jobs)}")
for j in jobs[:10]:
    print(f"  [{j.early_career_category}] {j.title} (min_exp: {j.min_experience_years}) at company_id {j.company_id}")

print("\n--- GERMANY JOBS ---")
ger_jobs = db.query(Job).filter(Job.country.ilike("%Germany%")).all()
print(f"Total Germany jobs: {len(ger_jobs)}")
for j in ger_jobs[:10]:
    print(f"  [{j.early_career_category}] {j.title}")

print("\n--- CANADA JOBS ---")
can_jobs = db.query(Job).filter(Job.country.ilike("%Canada%")).all()
print(f"Total Canada jobs: {len(can_jobs)}")
for j in can_jobs[:10]:
    print(f"  [{j.early_career_category}] {j.title}")

print("\n--- AUSTRALIA JOBS ---")
aus_jobs = db.query(Job).filter(Job.country.ilike("%Australia%")).all()
print(f"Total Australia jobs: {len(aus_jobs)}")
for j in aus_jobs[:10]:
    print(f"  [{j.early_career_category}] {j.title}")

db.close()
