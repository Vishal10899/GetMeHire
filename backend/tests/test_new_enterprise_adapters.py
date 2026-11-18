import pytest
from app.ingestion.runner import IngestionRunner, ADAPTER_MAP
from app.ingestion.adapters.icims import ICIMSAdapter
from app.ingestion.adapters.jobvite import JobviteAdapter
from app.ingestion.adapters.oracle_recruiting import OracleRecruitingAdapter
from app.ingestion.adapters.successfactors import SuccessFactorsAdapter
from app.ingestion.adapters.healthcare_careers import HealthcareCareersAdapter
from app.ingestion.adapters.university_careers import UniversityCareersAdapter

def test_enterprise_adapters_registered():
    """Verify all new enterprise ATS adapters are properly registered."""
    expected = [
        "ICIMS", "JOBVITE", "ORACLE", "ORACLE_RECRUITING",
        "SUCCESSFACTORS", "SAP_SUCCESSFACTORS",
        "HEALTHCARE", "HEALTHCARE_CAREERS",
        "UNIVERSITY", "UNIVERSITY_CAREERS"
    ]
    for key in expected:
        assert key in ADAPTER_MAP, f"{key} missing from ADAPTER_MAP"
        adapter = IngestionRunner.get_adapter(key)
        assert adapter is not None

def test_icims_adapter_normalization():
    adapter = ICIMSAdapter()
    raw = {
        "id": "req-10294",
        "title": "Lead Clinical Systems Analyst",
        "location": "Boston, MA",
        "description": "<p>Implement clinical healthcare workflows with HL7 and SQL.</p>",
        "url": "https://careers-hospital.icims.com/jobs/10294/job"
    }
    norm = adapter.normalize(raw, company_name="Mass General", source_id=99)
    assert norm.title == "Lead Clinical Systems Analyst"
    assert norm.company_name == "Mass General"
    assert norm.external_job_id == "req-10294"
    assert "Boston" in norm.city or "Boston" in norm.location
    assert norm.application_url == "https://careers-hospital.icims.com/jobs/10294/job"

def test_jobvite_adapter_normalization():
    adapter = JobviteAdapter()
    raw = {
        "eId": "jv-8831",
        "title": "Senior AI Infrastructure Engineer",
        "cityState": "San Francisco, CA",
        "jobDescription": "<p>Deploy LLM clusters using Kubernetes, Docker, and Python.</p>",
        "jobType": "Full-Time",
        "detailUrl": "https://jobs.jobvite.com/ai-corp/job/jv-8831"
    }
    norm = adapter.normalize(raw, company_name="AI Corp", source_id=101)
    assert norm.title == "Senior AI Infrastructure Engineer"
    assert norm.employment_type == "FULL_TIME"
    assert norm.external_job_id == "jv-8831"
    assert norm.application_url == "https://jobs.jobvite.com/ai-corp/job/jv-8831"

def test_oracle_recruiting_adapter_normalization():
    adapter = OracleRecruitingAdapter()
    raw = {
        "Id": "orc-55410",
        "Title": "Staff Cloud Security Architect",
        "PrimaryLocation": "London, United Kingdom",
        "ShortDescriptionStr": "Architect AWS and Azure cloud defense architecture.",
        "ExternalURL": "https://enterprise.oraclecloud.com/hcmUI/job/55410"
    }
    norm = adapter.normalize(raw, company_name="Fintech Global", source_id=102)
    assert norm.title == "Staff Cloud Security Architect"
    assert norm.country == "United Kingdom"
    assert norm.external_job_id == "orc-55410"

def test_successfactors_adapter_normalization():
    adapter = SuccessFactorsAdapter()
    raw = {
        "id": "sf-9923",
        "title": "Global Supply Chain Director",
        "location": "Munich, Germany",
        "url": "https://career4.successfactors.com/career?company=siemens&career_job_req_id=9923"
    }
    norm = adapter.normalize(raw, company_name="Siemens", source_id=103)
    assert norm.title == "Global Supply Chain Director"
    assert norm.country == "Germany"
    assert norm.external_job_id == "sf-9923"

def test_healthcare_careers_adapter_normalization():
    adapter = HealthcareCareersAdapter()
    raw = {
        "id": "med-771",
        "title": "Attending Cardiologist & Surgeon",
        "facility": "New York, NY",
        "description": "Cardiovascular surgery and cardiology consultations. Board certified MD required.",
        "employment_type": "FULL_TIME",
        "url": "https://hospital.org/careers/med-771"
    }
    norm = adapter.normalize(raw, company_name="Metropolitan Hospital", source_id=104)
    assert norm.title == "Attending Cardiologist & Surgeon"
    assert norm.employment_type == "FULL_TIME"
    assert norm.work_arrangement == "ONSITE"

def test_university_careers_adapter_normalization():
    adapter = UniversityCareersAdapter()
    raw = {
        "id": "uni-402",
        "title": "Postdoctoral Research Fellow in Machine Learning",
        "campus": "Cambridge, MA",
        "description": "Postdoctoral research on neural architectures and deep learning models.",
        "url": "https://harvard.edu/careers/uni-402"
    }
    norm = adapter.normalize(raw, company_name="Harvard University", source_id=105)
    assert norm.title == "Postdoctoral Research Fellow in Machine Learning"
    assert norm.employment_type == "FIXED_TERM"
