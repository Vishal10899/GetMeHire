from app.core.database import SessionLocal
from app.models import Job
from app.ingestion.taxonomy import TAXONOMY_FAMILIES
from sqlalchemy import func

db = SessionLocal()

print("=== CLASSIFICATION QUALITY AUDIT ACROSS ALL 14 FAMILIES ===\n")
total_jobs = db.query(Job).count()
low_conf_count = db.query(Job).filter(Job.classification_confidence < 0.70).count()
print(f"Total Database Jobs: {total_jobs}")
print(f"Low Confidence Jobs (< 0.70): {low_conf_count} ({low_conf_count/total_jobs*100:.1f}%)\n")

print("--- Low Confidence Samples (< 0.70) ---")
low_conf_sample = db.query(Job).filter(Job.classification_confidence < 0.70).limit(15).all()
for j in low_conf_sample:
    print(f"  [{j.profession}] (Conf: {j.classification_confidence}) | Title: '{j.title}' | Dept: '{j.department}'")

print("\n--- Family Samples (2 per family) ---")
for fam_key in sorted(TAXONOMY_FAMILIES.keys()):
    count = db.query(Job).filter(Job.profession == fam_key).count()
    samples = db.query(Job).filter(Job.profession == fam_key).limit(2).all()
    print(f"\nFamily: {fam_key} (Total: {count})")
    for s in samples:
        print(f"   * '{s.normalized_title or s.title}' (Conf: {s.classification_confidence}) | Dept: '{s.department}'")
