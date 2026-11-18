import pytest
from app.services.spelling_service import SpellingService
from app.ingestion.normalizer import generate_normalized_title, generate_system_summary
from app.ingestion.classifier import classify_profession_with_confidence

def test_spelling_correction_engine():
    # 1. "costumer suppot" -> "customer support"
    res1 = SpellingService.correct_and_expand_query("costumer suppot")
    assert res1["is_corrected"] is True
    assert res1["corrected_query"] == "customer support"
    assert res1["detected_profession"] == "CUSTOMER_SUPPORT"
    assert len(res1["suggested_roles"]) > 0

    # 2. "softwere enginer" -> "software engineer"
    res2 = SpellingService.correct_and_expand_query("softwere enginer")
    assert res2["is_corrected"] is True
    assert res2["corrected_query"] == "software engineer"
    assert res2["detected_profession"] == "ENGINEERING"

    # 3. "acountent" -> "accountant"
    res3 = SpellingService.correct_and_expand_query("acountent")
    assert res3["is_corrected"] is True
    assert res3["corrected_query"] == "accountant"
    assert res3["detected_profession"] == "FINANCE_ACCOUNTING"

    # 4. Correct word without typo
    res4 = SpellingService.correct_and_expand_query("python engineer")
    assert res4["is_corrected"] is False
    assert res4["corrected_query"] == "python engineer"

def test_synonym_expansion():
    res = SpellingService.correct_and_expand_query("coder")
    assert "software engineer" in res["synonyms"] or "developer" in res["synonyms"]

    res_rn = SpellingService.correct_and_expand_query("rn")
    assert any("nurse" in s for s in res_rn["synonyms"])

def test_search_api_with_typo_correction(client):
    # Query with typo "costumer suppot" should return results and did_you_mean metadata
    res = client.get("/api/v1/jobs?keyword=costumer+suppot")
    assert res.status_code == 200
    data = res.json()
    assert data["is_corrected"] is True
    assert data["did_you_mean"] == "customer support"
    assert "suggested_roles" in data
    assert data["query_latency_ms"] < 500.0

def test_title_and_description_normalization():
    # Strip Req ID
    raw1 = "Senior Backend Engineer (Req #8921)"
    clean1 = generate_normalized_title(raw1)
    assert clean1 == "Senior Backend Engineer"

    # Strip trailing location and level
    raw2 = "Account Executive - Remote (US) - Level 4"
    clean2 = generate_normalized_title(raw2)
    assert "Account Executive" in clean2
    assert "Remote (US)" not in clean2

    # HTML Summary generation
    html_desc = "<p>Stripe is a financial infrastructure platform for businesses. Millions of companies use Stripe to accept payments and grow their revenue online. We are looking for an experienced operations specialist.</p>"
    summary = generate_system_summary(html_desc)
    assert summary is not None
    assert summary.startswith("System-generated summary:")
    assert "financial infrastructure platform" in summary

def test_classification_with_confidence():
    prof, conf = classify_profession_with_confidence("Customer Success Manager", "User Operations")
    assert prof == "CUSTOMER_SUPPORT"
    assert conf >= 0.85

    prof2, conf2 = classify_profession_with_confidence("Staff Registered Nurse", "Clinical Health")
    assert prof2 == "HEALTHCARE_MEDICAL"
    assert conf2 >= 0.85

    prof3, conf3 = classify_profession_with_confidence("Store Manager", "Retail Operations")
    assert prof3 == "HOSPITALITY_RETAIL"
    assert conf3 >= 0.85

def test_all_12_taxonomy_families_in_api(client):
    res = client.get("/api/v1/jobs/professions")
    assert res.status_code == 200
    data = res.json()
    keys = {p["key"] for p in data["professions"]}

    required_families = [
        "CUSTOMER_SUPPORT",
        "ENGINEERING",
        "HEALTHCARE_MEDICAL",
        "SALES_BIZDEV",
        "FINANCE_ACCOUNTING",
        "DATA_AI",
        "HR_RECRUITMENT",
        "OPERATIONS_LOGISTICS",
        "EDUCATION_TRAINING",
        "MANUFACTURING_TRADES",
        "HOSPITALITY_RETAIL",
        "LEGAL_ADMIN"
    ]
    for fam in required_families:
        assert fam in keys, f"Expected {fam} in professions taxonomy endpoint"

def test_multi_interest_profile_persistence(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    # Update profile with multi-career interests
    payload = {
        "full_name": "Multi-Track Professional",
        "headline": "Versatile Support & Technical Operations Specialist",
        "career_interests": [
            {
                "profession": "CUSTOMER_SUPPORT",
                "preferred_roles": ["Customer Success Manager", "Technical Support Lead"],
                "skills": ["Zendesk", "Intercom", "SLA Management"],
                "experience_years": 4.0
            },
            {
                "profession": "ENGINEERING",
                "preferred_roles": ["Frontend Engineer"],
                "skills": ["React", "TypeScript", "Tailwind CSS"],
                "experience_years": 2.5
            }
        ]
    }
    update_res = client.patch("/api/v1/profile", json=payload, headers=headers)
    assert update_res.status_code == 200
    pdata = update_res.json()
    assert len(pdata["career_interests"]) == 2
    assert pdata["career_interests"][0]["profession"] == "CUSTOMER_SUPPORT"
    assert pdata["career_interests"][1]["profession"] == "ENGINEERING"

    # Verify recommendations scoped by profession
    rec_res = client.get("/api/v1/recommendations?profession=CUSTOMER_SUPPORT", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "items" in rec_data
    if rec_data["items"]:
        first_item = rec_data["items"][0]
        assert "match_breakdown" in first_item
        assert len(first_item["match_breakdown"]["reasons"]) > 0
