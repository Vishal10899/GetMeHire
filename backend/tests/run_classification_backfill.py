from app.core.database import SessionLocal
from app.models import Job
from app.ingestion.classifier import classify_profession_with_confidence

db = SessionLocal()
jobs = db.query(Job).all()
updated_count = 0
changed_professions = 0

print(f"Applying refined classification rules to {len(jobs)} database jobs...")
for j in jobs:
    prof, conf = classify_profession_with_confidence(j.title, j.department or "", j.description or "")
    if j.profession != prof or abs((j.classification_confidence or 0.0) - conf) > 0.01:
        if j.profession != prof:
            changed_professions += 1
        j.profession = prof
        j.classification_confidence = conf
        updated_count += 1

db.commit()
print(f"Classification backfill completed: {updated_count} jobs updated ({changed_professions} corrected professions).")

# Check new confidence stats
total_jobs = db.query(Job).count()
high_conf = db.query(Job).filter(Job.classification_confidence >= 0.70).count()
low_conf = db.query(Job).filter(Job.classification_confidence < 0.70).count()
print(f"High/Medium Confidence (>= 0.70): {high_conf} / {total_jobs} ({high_conf/total_jobs*100:.1f}%)")
print(f"Low Confidence (< 0.70): {low_conf} / {total_jobs} ({low_conf/total_jobs*100:.1f}%)")
