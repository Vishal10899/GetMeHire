import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job
from sqlalchemy import func, or_

db = SessionLocal()

countries = ["Germany", "Canada", "Australia", "United Kingdom", "India"]

for c in countries:
    print(f"\n==================== {c.upper()} ====================")
    total = db.query(Job).filter(Job.country.ilike(f"%{c}%")).count()
    fresher_friendly = db.query(Job).filter(
        Job.country.ilike(f"%{c}%"),
        Job.early_career_category.in_([
            "TRUE_FRESHER", "GRADUATE", "ENTRY_LEVEL", "EARLY_CAREER",
            "JUNIOR", "TRAINEE", "INTERNSHIP", "APPRENTICESHIP", "EXPERIENCE_FLEXIBLE"
        ])
    ).all()
    print(f"Total jobs: {total}, Fresher-friendly: {len(fresher_friendly)}")
    for j in fresher_friendly[:8]:
        print(f"  • [{j.early_career_category}] {j.title} (min_exp: {j.min_experience_years}) - loc: {j.location}")

db.close()
