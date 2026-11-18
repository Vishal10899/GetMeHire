import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.services.job_service import JobService
from app.services.early_career_intelligence import EarlyCareerIntelligence
from app.models import Job, Company

def main():
    print("=" * 90)
    print("GETMEHIRE — EARLY CAREER ACCEPTANCE & SEARCH INTELLIGENCE VERIFICATION")
    print("=" * 90)

    db = SessionLocal()
    test_results = {}

    queries = [
        {"id": "Q1", "query": "Fresher Software Developer", "country": "India", "loc": "India"},
        {"id": "Q2", "query": "Graduate Data Analyst", "country": "India", "loc": "India"},
        {"id": "Q3", "query": "Zero Experience AI Engineer", "country": None, "loc": "worldwide"},
        {"id": "Q4", "query": "Junior Accountant", "country": "United Kingdom", "loc": "UK"},
        {"id": "Q5", "query": "Graduate Trainee", "country": "Germany", "loc": "Germany"},
        {"id": "Q6", "query": "Paid Internship", "country": "United States", "loc": "USA"},
        {"id": "Q7", "query": "Fresh Graduate Nurse", "country": "Canada", "loc": "Canada"},
        {"id": "Q8", "query": "Entry-Level Marketing Associate", "country": "Australia", "loc": "Australia"},
        {"id": "Q9", "query": "Apprenticeship", "country": None, "loc": "worldwide"},
        {"id": "Q10", "query": "No Experience Customer Support", "country": "India", "loc": "India"},
    ]

    try:
        print("\n--- 1. RUNNING 10 ACCEPTANCE TEST QUERIES ---")
        for q in queries:
            t0 = time.time()
            res = JobService.search_jobs(
                db=db,
                keyword=q["query"],
                location=q["loc"] if q["loc"] != "worldwide" else None,
                country=q["country"],
                sort_by="relevant",
                page=1,
                page_size=5
            )
            lat = round((time.time() - t0) * 1000, 2)
            
            top_jobs = []
            for item in res.items[:3]:
                top_jobs.append({
                    "id": item.id,
                    "title": item.title,
                    "company": item.company_name,
                    "location": item.location,
                    "category": item.early_career_category,
                    "experience_years": item.min_experience_years,
                })

            test_results[q["id"]] = {
                "query": q["query"],
                "target_location": q["loc"],
                "total_results": res.total,
                "latency_ms": lat,
                "top_jobs": top_jobs,
                "status": "PASS" if res.total > 0 else "ZERO_RESULTS_INVESTIGATE"
            }

            print(f"[{q['id']}] {q['query'].ljust(35)} in {str(q['loc']).ljust(10)} -> Total: {res.total:4d} matches ({lat}ms)")
            for tj in top_jobs[:2]:
                print(f"      • {tj['title']} at {tj['company']} ({tj['location']}) [{tj['category']}]")

        print("\n--- 2. NEGATIVE TESTS: MISLABELLED ENTRY-LEVEL DETECTION ---")
        # Negative Test 1: Entry Level title requiring 5 years
        neg_title = "Entry Level Software Architect"
        neg_desc = "Requirements: Must have 5+ years of enterprise production software development and AWS experience."
        cat1, meta1 = EarlyCareerIntelligence.evaluate_job(neg_title, neg_desc)
        print(f"[NEG-1] 'Entry Level' title + 5 yrs exp -> Category: {cat1}, Fresher Friendly: {meta1['is_fresher_friendly']}")
        assert cat1 == "MISLABELLED_ENTRY_LEVEL"
        assert meta1["is_fresher_friendly"] is False

        # Negative Test 2: Associate with 0 years experience
        assoc_title = "Associate Software Engineer"
        assoc_desc = "Open to recent graduates. No previous professional experience required. Training will be provided."
        cat2, meta2 = EarlyCareerIntelligence.evaluate_job(assoc_title, assoc_desc)
        print(f"[NEG-2] 'Associate' title + 0 yrs exp -> Category: {cat2}, Fresher Friendly: {meta2['is_fresher_friendly']}")
        assert cat2 in ("TRUE_FRESHER", "ENTRY_LEVEL", "GRADUATE")
        assert meta2["is_fresher_friendly"] is True

        # Negative Test 3: Preferred 1 year experience vs mandatory 3 years
        pref_title = "Junior Data Analyst"
        pref_desc = "Requirements:\n- Bachelor's degree in Statistics or Math.\n\nPreferred Qualifications:\n- 1 year of experience in SQL or Tableau is a plus."
        cat3, meta3 = EarlyCareerIntelligence.evaluate_job(pref_title, pref_desc)
        print(f"[NEG-3] 'Junior' title + 1 yr preferred -> Category: {cat3}, Fresher Friendly: {meta3['is_fresher_friendly']}")
        assert meta3["is_fresher_friendly"] is True

        # Save results to json for report artifact
        out_path = os.path.join(os.path.dirname(__file__), "..", "early_career_acceptance_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2)
        print(f"\n[OK] Acceptance results saved to: {out_path}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
