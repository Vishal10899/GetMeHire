import io
import uuid
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import User, Profile, Job, ResumeVersion, Order, Entitlement
from app.services.matching_service import MatchingService
from app.services.payment_service import (
    PaymentService,
    DevTestPaymentGateway,
    ProductionPaymentGateway,
    PaymentGatewayInterface,
)
from app.core.security import get_password_hash, create_access_token


SAMPLE_TEST_RESUME = {
    "full_name": "Alex Mercer",
    "headline": "Senior Full Stack & Distributed Systems Engineer",
    "email": "alex.mercer@example.com",
    "phone": "+1-555-014-9988",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/alexmercer",
    "portfolio_url": "https://alexmercer.dev",
    "summary": "Full stack engineer with 6+ years of expertise architecting Python, FastAPI, React, and cloud native services.",
    "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS", "Redis"],
    "technical_skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS"],
    "tools_technologies": ["Git", "Terraform", "GitHub Actions"],
    "work_experience": [
        {
            "company": "Apex Cloud Systems",
            "role": "Senior Software Engineer",
            "location": "San Francisco, CA",
            "start_date": "2021",
            "end_date": "Present",
            "bullets": [
                "Engineered scalable ingestion services processing 10M events daily with Python and FastAPI.",
                "Optimized PostgreSQL query indexes and connection pools, cutting p99 latency by 40%."
            ]
        },
        {
            "company": "NextGen Data",
            "role": "Software Engineer",
            "location": "San Jose, CA",
            "start_date": "2018",
            "end_date": "2021",
            "bullets": [
                "Built React SPA dashboards and REST APIs deployed on Docker containers.",
                "Automated CI/CD workflows reducing deploy cycle from 1 hour to 8 minutes."
            ]
        }
    ],
    "education": [
        {
            "institution": "University of California, Davis",
            "degree": "B.S. in Computer Science",
            "field_of_study": "Computer Science",
            "graduation_year": "2018"
        }
    ],
    "projects": [
        {
            "title": "CloudQueue",
            "description": "Async queueing system written in Python with Redis backing.",
            "technologies": ["Python", "Redis", "FastAPI"],
            "url": "https://github.com/alexmercer/cloudqueue"
        }
    ],
    "certifications": [
        {
            "name": "AWS Certified Solutions Architect",
            "issuing_organization": "Amazon Web Services",
            "issue_date": "2022"
        }
    ]
}


@pytest.fixture
def candidate_b(db_session: Session):
    user = db_session.query(User).filter(User.email == "candidate_b@example.com").first()
    if not user:
        user = User(
            email="candidate_b@example.com",
            hashed_password=get_password_hash("CandidateB@123456"),
            role="USER",
            account_status="ACTIVE",
            is_verified=True
        )
        db_session.add(user)
        db_session.flush()

        profile = Profile(
            user_id=user.id,
            full_name="Bob Builder",
            headline="Junior React Developer",
            skills=["React", "JavaScript", "HTML", "CSS"],
            profile_completion_pct=40
        )
        db_session.add(profile)
        db_session.commit()
    return user


@pytest.fixture
def candidate_b_token(candidate_b):
    return create_access_token(subject=str(candidate_b.id))


# ==============================================================================
# 1. Complete User Profile Experience & In-Page Section CRUD
# ==============================================================================

def test_profile_lifecycle_and_updates(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Fetch current profile
    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    initial_data = get_res.json()
    assert initial_data["full_name"] is not None
    initial_pct = initial_data.get("profile_completion_pct", 0)

    # 2. Update Personal info, headline, summary, and location
    update_payload = {
        "full_name": "Alex Mercer Updated",
        "headline": "Lead Full Stack & Distributed Systems Architect",
        "current_location": "San Francisco, CA",
        "summary": "Experienced architect specializing in distributed real-time systems and cloud computing.",
        "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka", "AWS"],
        "tools_technologies": ["Git", "Terraform", "GitHub Actions", "Prometheus"],
        "work_experience": SAMPLE_TEST_RESUME["work_experience"],
        "education": SAMPLE_TEST_RESUME["education"],
        "projects": SAMPLE_TEST_RESUME["projects"],
        "certifications": SAMPLE_TEST_RESUME["certifications"],
        "preferred_roles": ["Lead Software Engineer", "Backend Architect"],
        "preferred_locations": ["San Francisco, CA", "Remote"],
        "preferred_countries": ["United States"],
        "work_arrangements": ["REMOTE", "HYBRID"],
        "salary_expectation_min": 160000,
        "salary_expectation_max": 190000,
    }

    patch_res = client.patch("/api/v1/profile", json=update_payload, headers=headers)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()

    # Verify all updated fields
    assert updated_data["full_name"] == "Alex Mercer Updated"
    assert updated_data["headline"] == "Lead Full Stack & Distributed Systems Architect"
    assert "Kafka" in updated_data["skills"]
    assert len(updated_data["work_experience"]) == 2
    assert updated_data["work_experience"][0]["company"] == "Apex Cloud Systems"
    assert len(updated_data["education"]) == 1
    assert len(updated_data["projects"]) == 1
    assert len(updated_data["certifications"]) == 1
    assert updated_data["work_arrangements"] == ["REMOTE", "HYBRID"]
    assert float(updated_data["salary_expectation_min"]) == 160000

    # Verify profile completion percentage reflects newly populated sections
    assert updated_data["profile_completion_pct"] >= 80


# ==============================================================================
# 2. Authentication Enforcement & Candidate-Level Data Isolation
# ==============================================================================

def test_profile_auth_enforcement_and_isolation(client, candidate_token, candidate_b_token, db_session):
    # 1. Unauthenticated requests to /profile return 401
    anon_res = client.get("/api/v1/profile")
    assert anon_res.status_code == 401

    anon_patch = client.patch("/api/v1/profile", json={"full_name": "Hacker"})
    assert anon_patch.status_code == 401

    # 2. User A creates a private resume version
    cand_a_headers = {"Authorization": f"Bearer {candidate_token}"}
    cand_b_headers = {"Authorization": f"Bearer {candidate_b_token}"}

    create_ver = client.post(
        "/api/v1/resume-studio/versions",
        json={
            "version_title": "Alex Mercer Secret Draft",
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "is_master": False,
        },
        headers=cand_a_headers
    )
    assert create_ver.status_code == 201
    ver_id = create_ver.json()["id"]

    # 3. User B attempts to access, update, duplicate, or delete User A's version -> 404 (Not Found / Isolated)
    cross_get = client.get(f"/api/v1/resume-studio/versions/{ver_id}", headers=cand_b_headers)
    assert cross_get.status_code == 404

    cross_update = client.put(
        f"/api/v1/resume-studio/versions/{ver_id}",
        json={"version_title": "Hijacked", "template_id": "classic_single", "content": {}},
        headers=cand_b_headers
    )
    assert cross_update.status_code == 404

    cross_del = client.delete(f"/api/v1/resume-studio/versions/{ver_id}", headers=cand_b_headers)
    assert cross_del.status_code == 404

    # Cleanup version
    del_res = client.delete(f"/api/v1/resume-studio/versions/{ver_id}", headers=cand_a_headers)
    assert del_res.status_code == 200


# ==============================================================================
# 3. Resume Upload, Parsing & Approval Workflow (P2A)
# ==============================================================================

def test_resume_upload_parsing_and_approval_workflow(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Upload mock text-based resume file
    resume_file_content = """
    Alex Mercer
    San Francisco, CA | alex.mercer@example.com | (555) 014-9988
    
    Professional Summary:
    Senior Software Engineer with 6 years of experience in Python, FastAPI, Docker, and Kubernetes.
    
    Skills:
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, Go, AWS
    
    Experience:
    Senior Software Engineer | Apex Cloud Systems | 2021 - Present
    - Architected microservices with Python and FastAPI.
    - Improved database performance across PostgreSQL clusters.
    
    Education:
    B.S. Computer Science | UC Davis | 2018
    """.encode("utf-8")

    upload_file = io.BytesIO(resume_file_content)
    files = {"file": ("alex_mercer_resume.txt", upload_file, "text/plain")}

    upload_res = client.post("/api/v1/profile/resume", files=files, headers=headers)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()

    assert "Resume successfully uploaded" in upload_data["message"]
    assert upload_data["download_url"] is not None
    assert upload_data["extracted_data"] is not None

    # Verify extracted data was discovered by deterministic parser
    extracted = upload_data["extracted_data"]
    assert "Python" in extracted.get("skills", [])

    # 2. Test download of original resume file via safe token
    download_url = upload_data["download_url"]
    dl_res = client.get(download_url)
    assert dl_res.status_code == 200
    assert dl_res.content == resume_file_content

    # 3. Test approval workflow: user approves extracted fields
    approval_payload = {
        "headline": "Lead Python & Cloud Architect",
        "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Go"]
    }
    approve_res = client.post("/api/v1/profile/review-approve", json=approval_payload, headers=headers)
    assert approve_res.status_code == 200
    approved_profile = approve_res.json()
    assert approved_profile["headline"] == "Lead Python & Cloud Architect"
    assert "Go" in approved_profile["skills"]


# ==============================================================================
# 4. Personalized Recommendations (P2B Matching Engine)
# ==============================================================================

def test_personalized_recommendations_scoring_and_explainability(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Ensure profile has skills
    client.patch(
        "/api/v1/profile",
        json={
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Linux"],
            "preferred_roles": ["Software Engineer", "Backend Engineer"],
            "work_arrangements": ["REMOTE"],
            "preferred_countries": ["United States", "United Kingdom"],
        },
        headers=headers
    )

    rec_res = client.get("/api/v1/recommendations?min_score=10", headers=headers)
    assert rec_res.status_code == 200
    data = rec_res.json()

    assert "items" in data
    assert "total" in data
    recs = data["items"]

    if len(recs) > 0:
        first_rec = recs[0]
        assert "job" in first_rec
        assert "match_score" in first_rec
        assert "match_breakdown" in first_rec

        breakdown = first_rec["match_breakdown"]
        assert "total_score" in breakdown
        assert "skill_score" in breakdown
        assert "matched_skills" in breakdown
        assert "missing_skills" in breakdown
        assert breakdown["total_score"] >= 10.0


# ==============================================================================
# 5. Job-Specific Tailoring & ATS Analysis (P2C Resume Studio)
# ==============================================================================

def test_job_specific_tailoring_real_jd(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Find a real active job
    job = db_session.query(Job).filter(Job.skills.isnot(None)).first()
    assert job is not None

    tailor_res = client.post(
        "/api/v1/resume-studio/tailor",
        json={"job_id": job.id},
        headers=headers
    )
    assert tailor_res.status_code == 200
    res_data = tailor_res.json()

    assert "match_score_before" in res_data
    assert "match_score_after" in res_data
    assert "matched_skills" in res_data
    assert "missing_skills" in res_data
    assert "adjacent_skills" in res_data
    assert "tailored_content" in res_data

    # Truthfulness Guarantee: Ensure missing skills were NOT hallucinated onto tailored_content["skills"]
    missing = res_data["missing_skills"]
    tailored_skills = res_data["tailored_content"].get("skills", [])
    for m in missing:
        assert m not in tailored_skills, f"Truthfulness violation: Missing skill '{m}' was fabricated onto resume!"


# ==============================================================================
# 6. Free vs Premium Entitlement & Payment Architecture
# ==============================================================================

def test_free_tier_export_master_resume_unrestricted(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Direct PDF export of master resume (target_job_id is None) is 100% Free
    direct_pdf = client.post(
        "/api/v1/resume-studio/export/pdf",
        json={
            "version_title": "Master Resume Free Export",
            "template_id": "modern_professional",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": None,
        },
        headers=headers
    )
    assert direct_pdf.status_code == 200
    assert direct_pdf.headers["content-type"] == "application/pdf"
    assert direct_pdf.content.startswith(b"%PDF-")

    # 2. Direct DOCX export of master resume (target_job_id is None) is 100% Free
    direct_docx = client.post(
        "/api/v1/resume-studio/export/docx",
        json={
            "version_title": "Master Resume Free Export",
            "template_id": "modern_professional",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": None,
        },
        headers=headers
    )
    assert direct_docx.status_code == 200
    assert direct_docx.content.startswith(b"PK\x03\x04")


def test_premium_export_gating_and_checkout_flow(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Clean up any existing entitlements and orders for candidate to ensure clean test state
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    assert user is not None
    db_session.query(Entitlement).filter(Entitlement.user_id == user.id).delete()
    db_session.query(Order).filter(Order.user_id == user.id).delete()
    db_session.commit()

    # Select an active job
    job = db_session.query(Job).first()
    assert job is not None

    # 1. Verify user does NOT have entitlement yet
    check_res = client.get(
        f"/api/v1/resume-studio/entitlements/check?job_id={job.id}",
        headers=headers
    )
    assert check_res.status_code == 200
    assert check_res.json()["has_entitlement"] is False

    # 2. Direct PDF export with target_job_id fails with HTTP 402 Payment Required
    unpaid_pdf = client.post(
        "/api/v1/resume-studio/export/pdf",
        json={
            "version_title": "Tailored Resume",
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": job.id,
        },
        headers=headers
    )
    assert unpaid_pdf.status_code == 402
    assert "entitlement required" in unpaid_pdf.json()["detail"].lower()

    # 3. Direct DOCX export with target_job_id also fails with HTTP 402
    unpaid_docx = client.post(
        "/api/v1/resume-studio/export/docx",
        json={
            "version_title": "Tailored Resume",
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": job.id,
        },
        headers=headers
    )
    assert unpaid_docx.status_code == 402

    # 4. Create a saved tailored version
    create_ver = client.post(
        "/api/v1/resume-studio/versions",
        json={
            "version_title": f"Tailored for {job.title}",
            "target_job_id": job.id,
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "is_master": False,
        },
        headers=headers
    )
    assert create_ver.status_code == 201
    ver_id = create_ver.json()["id"]

    # Version export without entitlement also fails with HTTP 402
    ver_unpaid_pdf = client.get(
        f"/api/v1/resume-studio/versions/{ver_id}/export/pdf",
        headers=headers
    )
    assert ver_unpaid_pdf.status_code == 402

    # 5. Perform Checkout via DevTestPaymentGateway
    idempotency_key = f"test_idemp_{uuid.uuid4().hex[:12]}"
    checkout_res = client.post(
        "/api/v1/resume-studio/checkout",
        json={
            "target_job_id": job.id,
            "resume_version_id": ver_id,
            "idempotency_key": idempotency_key,
        },
        headers=headers
    )
    assert checkout_res.status_code == 200
    checkout_data = checkout_res.json()

    assert checkout_data["is_unlocked"] is True
    assert checkout_data["order"]["status"] == "COMPLETED"
    assert checkout_data["entitlement"] is not None
    assert checkout_data["entitlement"]["is_active"] is True
    assert checkout_data["order"]["provider"] in ("TEST_GATEWAY", "dev_test_gateway")
    assert "test_tx_" in checkout_data["order"]["transaction_id"]

    # 6. Check entitlement endpoint now returns has_entitlement: True
    check_res_after = client.get(
        f"/api/v1/resume-studio/entitlements/check?job_id={job.id}",
        headers=headers
    )
    assert check_res_after.status_code == 200
    assert check_res_after.json()["has_entitlement"] is True

    # 7. List user entitlements
    list_ent = client.get("/api/v1/resume-studio/entitlements", headers=headers)
    assert list_ent.status_code == 200
    ents = list_ent.json()
    assert any(e["target_job_id"] == job.id for e in ents)

    # 8. Now Tailored PDF & DOCX exports SUCCEED with HTTP 200!
    paid_pdf = client.post(
        "/api/v1/resume-studio/export/pdf",
        json={
            "version_title": "Tailored Resume Paid",
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": job.id,
        },
        headers=headers
    )
    assert paid_pdf.status_code == 200
    assert paid_pdf.headers["content-type"] == "application/pdf"
    assert paid_pdf.content.startswith(b"%PDF-")

    paid_docx = client.post(
        "/api/v1/resume-studio/export/docx",
        json={
            "version_title": "Tailored Resume Paid",
            "template_id": "compact_technical",
            "content": SAMPLE_TEST_RESUME,
            "target_job_id": job.id,
        },
        headers=headers
    )
    assert paid_docx.status_code == 200
    assert paid_docx.content.startswith(b"PK\x03\x04")

    # Version export also succeeds with HTTP 200
    ver_paid_pdf = client.get(
        f"/api/v1/resume-studio/versions/{ver_id}/export/pdf",
        headers=headers
    )
    assert ver_paid_pdf.status_code == 200
    assert ver_paid_pdf.content.startswith(b"%PDF-")


# ==============================================================================
# 7. Payment Gateway Safety & Idempotency
# ==============================================================================

def test_payment_gateway_safety_and_idempotency(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = db_session.query(Job).first()
    assert job is not None

    # Test idempotency: Calling checkout again with the same idempotency key
    # returns the existing completed order rather than creating a duplicate
    fixed_key = f"fixed_idemp_{uuid.uuid4().hex[:10]}"
    res1 = client.post(
        "/api/v1/resume-studio/checkout",
        json={"target_job_id": job.id, "idempotency_key": fixed_key},
        headers=headers
    )
    assert res1.status_code == 200
    order1_id = res1.json()["order"]["id"]

    res2 = client.post(
        "/api/v1/resume-studio/checkout",
        json={"target_job_id": job.id, "idempotency_key": fixed_key},
        headers=headers
    )
    assert res2.status_code == 200
    order2_id = res2.json()["order"]["id"]
    assert order1_id == order2_id, "Idempotency failed: duplicate order created for identical key!"

    # Verify DevTestPaymentGateway sandbox attributes
    dev_gw = DevTestPaymentGateway()
    assert dev_gw.mode == "TEST_SANDBOX"

    # Verify ProductionPaymentGateway rejects unconfigured live payments
    from fastapi import HTTPException
    prod_gw = ProductionPaymentGateway()
    order = db_session.query(Order).filter(Order.id == order1_id).first()

    with pytest.raises(HTTPException) as exc_info:
        prod_gw.create_order_payload(order)
    assert exc_info.value.status_code == 503
    assert "awaiting API credential configuration" in str(exc_info.value.detail)
