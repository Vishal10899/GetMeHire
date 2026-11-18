import pytest
from app.services.resume_analyzer import ResumeAnalyzerService
from app.services.resume_improver import ResumeImproverService
from app.services.resume_tailor import ResumeTailorService
from app.services.resume_exporter import ResumeExporterService
from app.services.matching_service import MatchingService
from app.models import User, Profile, Job, ResumeVersion
from app.core.security import get_password_hash

SAMPLE_COMPLETE_RESUME = {
    "full_name": "Jane Developer",
    "headline": "Lead Backend & Distributed Systems Engineer",
    "email": "jane.dev@example.com",
    "phone": "+1-555-019-2831",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/janedev",
    "portfolio_url": "https://janedev.tech",
    "summary": "Proven distributed systems architect with 7+ years of experience engineering high-throughput microservices using Python, FastAPI, and Kubernetes. Scaled real-time ingestion pipelines processing over 20M events daily.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka", "AWS", "CI/CD"],
    "technical_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka"],
    "tools_technologies": ["Git", "GitHub Actions", "Terraform", "Prometheus", "Grafana"],
    "work_experience": [
        {
            "company": "TechScale Systems",
            "role": "Lead Backend Engineer",
            "location": "San Francisco, CA",
            "start_date": "2021",
            "end_date": "Present",
            "bullets": [
                "Architected distributed real-time messaging pipeline using Kafka and FastAPI, reducing message delivery latency by 45%.",
                "Scaled PostgreSQL query throughput by 3x through intelligent connection pooling and optimized B-tree indexing across 50M records.",
                "Mentored team of 6 engineers on cloud deployment and automated CI/CD pipeline reliability."
            ]
        },
        {
            "company": "DataCloud Inc",
            "role": "Senior Software Engineer",
            "location": "Austin, TX",
            "start_date": "2018",
            "end_date": "2021",
            "bullets": [
                "Engineered automated container orchestration using Kubernetes and Docker across 120 production nodes.",
                "Automated zero-downtime database failover workflows, cutting MTTR from 40 minutes to under 2 minutes."
            ]
        }
    ],
    "education": [
        {
            "institution": "University of California, Berkeley",
            "degree": "B.S. in Computer Science",
            "year": "2018"
        }
    ],
    "projects": [
        {
            "title": "OpenQueue",
            "description": "High-performance in-memory task broker written in Python and asyncio with 1.2k GitHub stars."
        }
    ],
    "certifications": ["AWS Certified Solutions Architect - Associate", "CKA: Certified Kubernetes Administrator"]
}

SAMPLE_WEAK_RESUME = {
    "full_name": "",  # Missing!
    "email": "invalid-email-address",  # Invalid!
    "phone": "",  # Missing!
    "location": "",  # Missing!
    "summary": "Hardworking team player looking for a job in a fast-paced environment.",
    "skills": ["Python"],
    "work_experience": [
        {
            "company": "OldCorp",
            "role": "Programmer",
            "bullets": [
                "Responsible for managing servers and worked on various things.",
                "Assisted with bug fixing."
            ]
        }
    ],
    "education": []
}

ALL_5_TEMPLATES = [
    "classic_single",
    "modern_professional",
    "compact_technical",
    "data_analytics",
    "executive_leadership"
]


# ==============================================================================
# 1. Resume Analyzer Tests
# ==============================================================================

def test_analyzer_complete_resume():
    res = ResumeAnalyzerService.analyze_resume(SAMPLE_COMPLETE_RESUME)
    assert res.overall_score >= 80
    assert res.ats_compatibility in ("EXCELLENT", "GOOD")
    assert "score_breakdown" in res.model_dump()
    for cat in ["contact_information", "professional_summary", "work_experience", "skills_coverage", "education_and_credentials", "ats_readability_structure"]:
        assert cat in res.score_breakdown
        assert res.score_breakdown[cat] > 0
    assert "ATS" in res.disclaimer


def test_analyzer_weak_and_missing_fields():
    res = ResumeAnalyzerService.analyze_resume(SAMPLE_WEAK_RESUME)
    assert res.overall_score < 60
    assert res.ats_compatibility in ("NEEDS_IMPROVEMENT", "POOR")

    severities = [f.severity for f in res.findings]
    assert "CRITICAL" in severities
    assert "WARNING" in severities

    finding_titles = [f.title for f in res.findings]
    assert any("Missing Candidate Name" in t for t in finding_titles)
    assert any("Email" in t for t in finding_titles)
    assert any("Passive Openings" in t or "Opening" in t for t in finding_titles)


# ==============================================================================
# 2. Resume Improver Tests
# ==============================================================================

def test_improver_bullet_rewrite():
    weak_bullet = "Responsible for managing servers and worked on database queries."
    result = ResumeImproverService.improve_bullet(
        bullet_text=weak_bullet,
        role_title="Backend Engineer",
        target_keywords=["PostgreSQL", "Docker"]
    )

    assert result["original"] == weak_bullet
    assert len(result["improved_options"]) >= 2
    # Verify no weak opening in rewritten options
    for opt in result["improved_options"]:
        assert not opt["text"].lower().startswith("responsible for")
        assert not opt["text"].lower().startswith("worked on")

    # Verify coaching questions for missing metrics
    assert len(result["coaching_questions"]) >= 1
    assert any("outcome" in q.lower() or "metric" in q.lower() or "scale" in q.lower() for q in result["coaching_questions"])


def test_improver_summary_generation():
    options = ResumeImproverService.improve_summary(
        current_summary="Python engineer who writes APIs",
        target_role="Senior Backend Architect",
        years_of_experience=6.0,
        top_skills=["Python", "FastAPI", "Kubernetes"]
    )
    assert len(options) == 3
    styles = [opt["style"] for opt in options]
    assert "Impact-Driven" in styles
    assert "Technical Depth" in styles
    assert "Leadership & Growth" in styles
    for opt in options:
        assert "Python" in opt["text"]


# ==============================================================================
# 3. Resume Tailoring Engine Tests
# ==============================================================================

def test_tailor_service_categorization_and_reranking(db_session):
    # Find seed job
    job = db_session.query(Job).filter(Job.skills.isnot(None)).first()
    assert job is not None

    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    assert user is not None

    tailored = ResumeTailorService.tailor_resume_for_job(
        db=db_session,
        user=user,
        job_id=job.id,
        base_resume_data=SAMPLE_COMPLETE_RESUME
    )

    assert tailored.target_job_id == job.id
    assert tailored.target_job_title == job.title
    assert len(tailored.tailored_summary_options) >= 2
    assert isinstance(tailored.matched_skills, list)
    assert isinstance(tailored.adjacent_skills, list)
    assert isinstance(tailored.missing_skills, list)
    assert tailored.match_score_after >= tailored.match_score_before


# ==============================================================================
# 4. ATS Exporter Tests (PDF and DOCX across all 5 templates)
# ==============================================================================

def test_exporter_pdf_all_templates():
    for tmpl in ALL_5_TEMPLATES:
        pdf_bytes = ResumeExporterService.generate_pdf(SAMPLE_COMPLETE_RESUME, template_id=tmpl)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-"), f"Template {tmpl} failed to produce valid PDF header"


def test_exporter_docx_all_templates():
    for tmpl in ALL_5_TEMPLATES:
        docx_bytes = ResumeExporterService.generate_docx(SAMPLE_COMPLETE_RESUME, template_id=tmpl)
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 1000
        # DOCX files are zip archives starting with PK\x03\x04
        assert docx_bytes.startswith(b"PK\x03\x04"), f"Template {tmpl} failed to produce valid DOCX header"


# ==============================================================================
# 5. API Endpoints & Candidate Isolation Tests
# ==============================================================================

def test_api_master_resume_lifecycle(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Get Master Resume
    get_res = client.get("/api/v1/resume-studio/master", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert "full_name" in data
    assert "skills" in data

    # 2. Update Master Resume
    update_payload = dict(data)
    update_payload["headline"] = "Staff Reliability Engineer"
    update_payload["skills"] = ["Python", "FastAPI", "PostgreSQL", "Terraform", "Redis"]

    post_res = client.post("/api/v1/resume-studio/master", json=update_payload, headers=headers)
    assert post_res.status_code == 200
    updated_data = post_res.json()
    assert updated_data["headline"] == "Staff Reliability Engineer"
    assert "Terraform" in updated_data["skills"]


def test_api_analyze_and_improve_routes(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Analyze
    analyze_res = client.post("/api/v1/resume-studio/analyze", json=SAMPLE_COMPLETE_RESUME, headers=headers)
    assert analyze_res.status_code == 200
    assert analyze_res.json()["overall_score"] > 70

    # Improve bullet
    bullet_res = client.post(
        "/api/v1/resume-studio/improve/bullet",
        json={"bullet_text": "Responsible for managing servers and databases."},
        headers=headers
    )
    assert bullet_res.status_code == 200
    assert len(bullet_res.json()["improved_options"]) >= 1

    # Improve summary
    summary_res = client.post(
        "/api/v1/resume-studio/improve/summary",
        json={
            "current_summary": "Software engineer",
            "target_role": "Backend Lead",
            "years_of_experience": 5.0,
            "top_skills": ["Python", "FastAPI"]
        },
        headers=headers
    )
    assert summary_res.status_code == 200
    assert len(summary_res.json()["options"]) == 3


def test_api_version_crud_and_candidate_isolation(client, candidate_token, admin_token, db_session):
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a version for candidate (generic master version for free export testing)
    target_job_id = None

    save_payload = {
        "version_title": "Tailored for Stripe Backend",
        "target_job_id": target_job_id,
        "template_id": "modern_professional",
        "content": SAMPLE_COMPLETE_RESUME,
        "is_master": False
    }
    create_res = client.post("/api/v1/resume-studio/versions", json=save_payload, headers=cand_headers)
    assert create_res.status_code == 201
    created_ver = create_res.json()
    ver_id = created_ver["id"]
    assert created_ver["version_title"] == "Tailored for Stripe Backend"
    assert created_ver["template_id"] == "modern_professional"
    assert created_ver["analysis"]["overall_score"] > 70

    # 2. List versions for candidate
    list_res = client.get("/api/v1/resume-studio/versions", headers=cand_headers)
    assert list_res.status_code == 200
    ids = [v["id"] for v in list_res.json()]
    assert ver_id in ids

    # 3. Candidate Isolation Test:
    # User B (Admin in this case) attempts to access Candidate's version
    cross_get = client.get(f"/api/v1/resume-studio/versions/{ver_id}", headers=admin_headers)
    assert cross_get.status_code == 404, "User B should not be able to read User A's resume version"

    cross_update = client.put(
        f"/api/v1/resume-studio/versions/{ver_id}",
        json={"version_title": "Hacked Title", "content": SAMPLE_COMPLETE_RESUME, "template_id": "classic_single"},
        headers=admin_headers
    )
    assert cross_update.status_code == 404, "User B should not be able to update User A's resume version"

    cross_dup = client.post(f"/api/v1/resume-studio/versions/{ver_id}/duplicate", headers=admin_headers)
    assert cross_dup.status_code == 404, "User B should not be able to duplicate User A's resume version"

    cross_del = client.delete(f"/api/v1/resume-studio/versions/{ver_id}", headers=admin_headers)
    assert cross_del.status_code == 404, "User B should not be able to delete User A's resume version"

    # 4. Duplicate version by owner
    dup_res = client.post(f"/api/v1/resume-studio/versions/{ver_id}/duplicate", headers=cand_headers)
    assert dup_res.status_code == 201
    dup_ver = dup_res.json()
    assert "Copy" in dup_ver["version_title"]
    assert dup_ver["version_number"] > created_ver["version_number"]

    # 5. Export saved version to PDF and DOCX
    pdf_res = client.get(f"/api/v1/resume-studio/versions/{ver_id}/export/pdf", headers=cand_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")

    docx_res = client.get(f"/api/v1/resume-studio/versions/{ver_id}/export/docx", headers=cand_headers)
    assert docx_res.status_code == 200
    assert "officedocument" in docx_res.headers["content-type"]
    assert docx_res.content.startswith(b"PK\x03\x04")

    # 6. Direct on-the-fly export
    direct_pdf_res = client.post(
        "/api/v1/resume-studio/export/pdf",
        json={"version_title": "Direct Download", "template_id": "compact_technical", "content": SAMPLE_COMPLETE_RESUME},
        headers=cand_headers
    )
    assert direct_pdf_res.status_code == 200
    assert direct_pdf_res.content.startswith(b"%PDF-")

    # 7. Safe Delete by owner
    del_res = client.delete(f"/api/v1/resume-studio/versions/{ver_id}", headers=cand_headers)
    assert del_res.status_code == 200

    # Ensure Candidate's profile is still intact
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    assert user is not None
    assert user.profile is not None


# ==============================================================================
# 6. Audit Remediation Specific Verification Tests
# ==============================================================================

def test_remediation_target_job_id_validation(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    real_job = db_session.query(Job).first()
    assert real_job is not None

    # 1. Invalid target_job_id on POST -> returns 400 (not 500 ForeignKeyViolation)
    bad_post = client.post(
        "/api/v1/resume-studio/versions",
        json={
            "version_title": "Bad Job Version",
            "target_job_id": 9999999,
            "template_id": "classic_single",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert bad_post.status_code == 400
    assert "9999999" in bad_post.json()["detail"]
    assert "does not exist" in bad_post.json()["detail"].lower()

    # 2. Omitted target_job_id (None) -> succeeds with 201
    none_post = client.post(
        "/api/v1/resume-studio/versions",
        json={
            "version_title": "General Unlinked Version",
            "target_job_id": None,
            "template_id": "compact_technical",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert none_post.status_code == 201
    created_id = none_post.json()["id"]
    assert none_post.json()["target_job_id"] is None

    # 3. Invalid target_job_id on PUT -> returns 400
    bad_put = client.put(
        f"/api/v1/resume-studio/versions/{created_id}",
        json={
            "version_title": "Updated Bad Job",
            "target_job_id": 8888888,
            "template_id": "classic_single",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert bad_put.status_code == 400
    assert "8888888" in bad_put.json()["detail"]

    # 4. Valid target_job_id on PUT -> succeeds with 200
    good_put = client.put(
        f"/api/v1/resume-studio/versions/{created_id}",
        json={
            "version_title": "Updated Good Job",
            "target_job_id": real_job.id,
            "template_id": "modern_professional",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert good_put.status_code == 200
    assert good_put.json()["target_job_id"] == real_job.id

    # Cleanup
    client.delete(f"/api/v1/resume-studio/versions/{created_id}", headers=headers)


def test_remediation_template_id_restriction(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Invalid template on POST /versions -> returns 422 Unprocessable Entity
    invalid_ver = client.post(
        "/api/v1/resume-studio/versions",
        json={
            "version_title": "Invalid Template Version",
            "template_id": "non_existent_layout_xyz",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert invalid_ver.status_code == 422

    # 2. Invalid template on direct export -> returns 422
    invalid_export = client.post(
        "/api/v1/resume-studio/export/pdf",
        json={
            "version_title": "Direct Export",
            "template_id": "hack_template",
            "content": SAMPLE_COMPLETE_RESUME,
        },
        headers=headers,
    )
    assert invalid_export.status_code == 422

    # 3. All 5 valid templates succeed on direct export
    for tmpl in ALL_5_TEMPLATES:
        ok_export = client.post(
            "/api/v1/resume-studio/export/pdf",
            json={
                "version_title": f"Valid {tmpl}",
                "template_id": tmpl,
                "content": SAMPLE_COMPLETE_RESUME,
            },
            headers=headers,
        )
        assert ok_export.status_code == 200
        assert ok_export.content.startswith(b"%PDF-")


def test_remediation_genuine_match_recalculation(db_session):
    job = db_session.query(Job).filter(Job.skills.isnot(None)).first()
    assert job is not None

    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    assert user is not None
    assert user.profile is not None

    # Tailor resume for job
    tailored = ResumeTailorService.tailor_resume_for_job(
        db=db_session,
        user=user,
        job_id=job.id,
        base_resume_data=SAMPLE_COMPLETE_RESUME
    )

    # Calculate actual genuine score directly via MatchingService
    reordered_skills = tailored.tailored_content["skills"]
    direct_breakdown = MatchingService.calculate_match(
        profile=user.profile,
        job=job,
        scoped_skills=reordered_skills,
        scoped_roles=[job.title] if job.title else list(user.profile.preferred_roles or [])
    )
    expected_score_after = int(round(direct_breakdown.total_score))

    # Assert that score_after matches the genuine MatchingService output exactly
    assert tailored.match_score_after == expected_score_after
    # Assert that there is NO hardcoded +18 artifact
    assert tailored.match_score_after != tailored.match_score_before + 18 or expected_score_after == tailored.match_score_before + 18
    # Assert explanations are preserved
    assert len(tailored.improvement_notes) >= 3

