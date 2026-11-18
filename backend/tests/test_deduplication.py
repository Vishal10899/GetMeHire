import pytest
from app.ingestion.base import NormalizedJob
from app.ingestion.deduplication import compute_content_fingerprint, clean_text_for_fingerprint

def test_clean_text_for_fingerprint():
    dirty = "   <p>Senior <b>Developer</b> &amp; Architect!   </p>   "
    clean = clean_text_for_fingerprint(dirty)
    assert "<" not in clean
    assert ">" not in clean
    assert clean == "senior developer architect"

def test_fingerprint_deterministic_stability():
    job1 = NormalizedJob(
        external_job_id="job-101",
        title="Senior Python Backend Engineer",
        description="We are building large-scale cloud services with Python and PostgreSQL.",
        location="San Francisco, CA",
        remote_type="REMOTE",
        employment_type="FULL_TIME",
        application_url="https://example.com/apply"
    )

    job2 = NormalizedJob(
        external_job_id="job-101",
        title="  Senior   Python Backend Engineer  ",
        description="<p>We are building large-scale cloud services with Python and PostgreSQL.</p>",
        location="San Francisco, CA",
        remote_type="REMOTE",
        employment_type="FULL_TIME",
        application_url="https://example.com/apply"
    )

    fp1 = compute_content_fingerprint(job1, "TechCorp")
    fp2 = compute_content_fingerprint(job2, "TechCorp")
    assert fp1 == fp2, "Fingerprints must be identical despite whitespace or HTML wrapper differences"

def test_fingerprint_changes_on_material_edit():
    job1 = NormalizedJob(
        external_job_id="job-101",
        title="Senior Python Backend Engineer",
        description="Building scalable backend.",
        remote_type="REMOTE",
        application_url="https://example.com/apply"
    )

    job_changed = NormalizedJob(
        external_job_id="job-101",
        title="Principal Infrastructure Lead",
        description="Lead the entire cloud infrastructure team.",
        remote_type="ONSITE",
        application_url="https://example.com/apply"
    )

    fp1 = compute_content_fingerprint(job1, "TechCorp")
    fp2 = compute_content_fingerprint(job_changed, "TechCorp")
    assert fp1 != fp2, "Fingerprints must differ on material title/description/remote changes"
