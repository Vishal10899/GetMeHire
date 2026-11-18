import pytest
from unittest.mock import MagicMock
from app.models import User, Profile
from app.schemas.resume_studio import JDMatchRequest
from app.services.jd_matching_service import JDMatchingService
from app.services.resume_template_intelligence import (
    ROLE_TEMPLATE_REGISTRY,
    get_all_templates,
    get_template,
    detect_optimal_template_for_role,
)
from app.services.resume_exporter import ResumeExporterService


def test_role_template_registry_completeness():
    templates = get_all_templates()
    assert len(templates) >= 16
    template_ids = {t["id"] for t in templates}

    expected_ids = {
        "software_engineering", "ai_ml_engineer", "data_analyst", "data_scientist",
        "product_manager", "business_analyst", "banking_finance", "accountant_audit",
        "enterprise_sales", "marketing_growth", "healthcare_nursing", "doctor_surgeon",
        "human_resources", "legal_compliance", "operations_supply_chain", "executive_leadership"
    }
    for exp_id in expected_ids:
        assert exp_id in template_ids, f"Expected template {exp_id} missing from registry"

    # Verify template structure
    for t in templates:
        assert "recommended_sections_order" in t
        assert "section_titles" in t
        assert "color_palette" in t
        assert "primary" in t["color_palette"]
        assert "accent" in t["color_palette"]


def test_detect_optimal_template():
    ai_template = detect_optimal_template_for_role("Senior LLM & Generative AI Engineer")
    assert ai_template["id"] == "ai_ml_engineer"

    se_template = detect_optimal_template_for_role("Lead Backend Software Developer")
    assert se_template["id"] == "software_engineering"

    doc_template = detect_optimal_template_for_role("Chief Pediatric Surgeon")
    assert doc_template["id"] == "doctor_surgeon"

    nurse_template = detect_optimal_template_for_role("Registered Nurse (ICU Specialist)")
    assert nurse_template["id"] == "healthcare_nursing"

    sales_template = detect_optimal_template_for_role("Enterprise Account Executive")
    assert sales_template["id"] == "enterprise_sales"

    exec_template = detect_optimal_template_for_role("Chief Executive Officer & VP")
    assert exec_template["id"] == "executive_leadership"


def test_jd_matching_service_with_custom_jd_and_resume():
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "alex.rivera@example.com"
    mock_user.profile = None

    custom_jd_text = """
    We are looking for a Senior AI Engineer to join our core ML team.
    
    Requirements:
    - 5+ years of software development experience with at least 3 years in machine learning.
    - Strong proficiency in Python, PyTorch, and Docker.
    - Experience deploying LLMs or Transformer architectures into production.
    - Master's degree or Bachelor's in Computer Science or related field.
    
    Preferred Qualifications:
    - Experience with Kubernetes and FastAPI.
    - Knowledge of vector databases and LangChain.
    """

    sample_resume = {
        "full_name": "Alex Rivera",
        "headline": "Machine Learning Engineer",
        "email": "alex.rivera@example.com",
        "phone": "+1 (555) 234-5678",
        "location": "San Francisco, CA",
        "summary": "Experienced ML Engineer with 6 years building production systems.",
        "skills": ["Python", "PyTorch", "Docker", "PostgreSQL", "Git"],
        "education": [
            {
                "degree": "Master of Science in Computer Science",
                "institution": "Stanford University",
                "graduation_year": 2018,
            }
        ],
        "work_experience": [
            {
                "title": "Senior ML Engineer",
                "company": "DeepTech AI",
                "start_date": "2020",
                "end_date": "Present",
                "bullets": [
                    "Architected and deployed PyTorch transformer pipelines serving 12M daily requests.",
                    "Reduced inference latency by 35% through model quantization and TensorRT optimization.",
                    "Containerized inference microservices using Docker on AWS cloud infrastructure."
                ]
            },
            {
                "title": "Software Engineer",
                "company": "Cloud Corp",
                "start_date": "2018",
                "end_date": "2020",
                "bullets": [
                    "Developed backend Python microservices handling 5,000 QPS with 99.9% uptime."
                ]
            }
        ]
    }

    req = JDMatchRequest(
        job_title="Senior AI Engineer",
        company_name="InnovateAI Labs",
        job_description_text=custom_jd_text,
        resume_content=sample_resume,
    )

    result = JDMatchingService.match(db=mock_db, user=mock_user, request=req)

    # Assertions
    assert result.target_job_title == "Senior AI Engineer"
    assert result.target_company_name == "InnovateAI Labs"
    assert result.overall_match_score >= 70

    # Skills check
    matched_skills = [s.skill.lower() for s in result.matched_skills]
    assert "python" in matched_skills
    assert "pytorch" in matched_skills
    assert "docker" in matched_skills

    # Experience check (Alex has ~6 years vs 5+ requested)
    assert result.experience_analysis.candidate_years >= 5.0
    assert result.experience_analysis.status in ("MATCHED", "SURPASSED")

    # Education check (Master's matches Master's / Bachelor's)
    assert result.education_analysis.status == "MATCHED"

    # Recommended template
    assert result.recommended_template["id"] == "ai_ml_engineer"


def test_exporter_handles_all_role_templates():
    sample = {
        "full_name": "Test Candidate",
        "headline": "Specialist",
        "email": "test@example.com",
        "phone": "+1-555-0100",
        "location": "New York, NY",
        "summary": "Specialist summary text.",
        "skills": ["Analysis", "Communication"],
        "education": [{"degree": "BS", "institution": "State University", "graduation_year": 2020}],
        "work_experience": [{"title": "Analyst", "company": "Global Inc", "start_date": "2020", "bullets": ["Improved workflow by 20%."]}]
    }

    test_ids = ["software_engineering", "ai_ml_engineer", "doctor_surgeon", "banking_finance", "classic_single"]
    for tid in test_ids:
        pdf_bytes = ResumeExporterService.generate_pdf(sample, template_id=tid)
        docx_bytes = ResumeExporterService.generate_docx(sample, template_id=tid)
        assert len(pdf_bytes) > 1000, f"PDF generation failed for template {tid}"
        assert len(docx_bytes) > 5000, f"DOCX generation failed for template {tid}"


def test_api_list_role_templates(client):
    res = client.get("/api/v1/resume-studio/templates")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 16
    assert len(data["templates"]) >= 16


def test_api_recommended_template(client):
    res = client.get("/api/v1/resume-studio/templates/recommended?role_title=Cardiac%20Surgeon")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "doctor_surgeon"


def test_api_jd_match_endpoint(client, candidate_token):
    payload = {
        "job_title": "Senior Data Scientist",
        "company_name": "Health Analytics Corp",
        "job_description_text": """
        Requirements:
        - 4+ years of data science and statistical modeling experience.
        - Proficiency in Python, SQL, and Pandas.
        - Degree in Computer Science, Statistics, or related discipline.
        """,
        "resume_content": {
            "full_name": "Test User",
            "email": "candidate@example.com",
            "skills": ["Python", "SQL", "Machine Learning"],
            "education": [{"degree": "BS in Mathematics", "institution": "City College", "graduation_year": 2019}],
            "work_experience": [
                {
                    "title": "Data Scientist",
                    "company": "Alpha Corp",
                    "start_date": "2019",
                    "end_date": "Present",
                    "bullets": ["Trained XGBoost models improving churn prediction by 18%."]
                }
            ]
        }
    }
    res = client.post(
        "/api/v1/resume-studio/jd-match",
        json=payload,
        headers={"Authorization": f"Bearer {candidate_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_job_title"] == "Senior Data Scientist"
    assert data["overall_match_score"] > 50
    assert "skills" in data["score_breakdown"]
    assert "experience" in data["score_breakdown"]
    assert len(data["matched_skills"]) > 0
    assert data["recommended_template"]["id"] in ("data_scientist", "data_analyst", "ai_ml_engineer")

