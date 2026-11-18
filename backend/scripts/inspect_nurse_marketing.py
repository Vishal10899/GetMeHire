import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job

db = SessionLocal()

print("--- NURSING JOBS GLOBALLY ---")
nurse_jobs = db.query(Job).filter(Job.title.ilike("%Nurse%")).all()
print(f"Total Nurse jobs globally: {len(nurse_jobs)}")
for j in nurse_jobs[:10]:
    print(f"  • [{j.country}] [{j.early_career_category}] {j.title}")

print("\n--- MARKETING IN AUSTRALIA ---")
mkt_jobs = db.query(Job).filter(Job.country.ilike("%Australia%"), Job.title.ilike("%Marketing%")).all()
print(f"Total Marketing in Australia: {len(mkt_jobs)}")
for j in mkt_jobs[:10]:
    print(f"  • [{j.country}] [{j.early_career_category}] {j.title}")

print("\n--- HEALTHCARE IN CANADA ---")
can_health = db.query(Job).filter(Job.country.ilike("%Canada%"), Job.profession == "HEALTHCARE_MEDICAL").all()
print(f"Total Healthcare in Canada: {len(can_health)}")
for j in can_health[:10]:
    print(f"  • [{j.country}] [{j.early_career_category}] {j.title}")

db.close()
