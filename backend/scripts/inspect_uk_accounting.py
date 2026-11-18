import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job

db = SessionLocal()

print("--- ACCOUNTING / FINANCE IN UK ---")
jobs = db.query(Job).filter(
    Job.country.ilike("%United Kingdom%") | Job.country.ilike("%UK%"),
    Job.title.ilike("%Account%") | Job.title.ilike("%Finance%") | Job.title.ilike("%Audit%")
).all()

print(f"Total Accounting/Finance jobs in UK: {len(jobs)}")
for j in jobs[:15]:
    print(f"  • ID {j.id} | [{j.early_career_category}] {j.title} | {j.location} | comp_id: {j.company_id}")

db.close()
