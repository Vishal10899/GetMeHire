import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("""
    SELECT (early_career_metadata->>'is_fresher_friendly')::boolean as is_fresher_friendly, early_career_category, count(*) 
    FROM jobs 
    WHERE status IN ('ACTIVE', 'POSSIBLY_STALE')
    GROUP BY early_career_metadata->>'is_fresher_friendly', early_career_category
    ORDER BY count(*) DESC;
""")).fetchall()

print("Active jobs by fresher friendly & category:")
for row in res:
    print(f"  fresher_friendly={str(row[0]).ljust(5)} | category={str(row[1]).ljust(25)} | count={row[2]}")

total_fresher = db.execute(text("""
    SELECT count(*) FROM jobs 
    WHERE status IN ('ACTIVE', 'POSSIBLY_STALE') AND (early_career_metadata->>'is_fresher_friendly')::boolean = TRUE;
""")).scalar()
print(f"\nTotal active fresher friendly: {total_fresher}")

# Breakdown by early career category
cat_res = db.execute(text("""
    SELECT early_career_category, count(*) 
    FROM jobs 
    WHERE status IN ('ACTIVE', 'POSSIBLY_STALE')
    GROUP BY early_career_category
    ORDER BY count(*) DESC;
""")).fetchall()

print("\nBreakdown by early_career_category:")
for row in cat_res:
    print(f"  {str(row[0]).ljust(30)}: {row[1]}")

db.close()
