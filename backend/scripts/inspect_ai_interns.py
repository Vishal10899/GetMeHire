import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job

db = SessionLocal()

print("--- AI / ML INTERN & ENTRY LEVEL JOBS WORLDWIDE ---")
jobs = db.query(Job).filter(
    Job.title.ilike("%Intern%"),
    Job.title.ilike("%AI%") | Job.title.ilike("%Machine Learning%") | Job.title.ilike("%Data Scientist%")
).all()

print(f"Total AI/ML Intern jobs: {len(jobs)}")
for j in jobs[:15]:
    desc_sample = (j.description or "")[:300].replace("\n", " ")
    print(f"  • ID {j.id} | [{j.early_career_category}] {j.title} | {j.location} | comp_id: {j.company_id}")
    print(f"    Desc preview: {desc_sample[:180]}...")

db.close()
