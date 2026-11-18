"""
Unit tests for Early Career Intelligence Engine.
Validates:
- True Fresher classification
- Graduate program and batch detection
- Entry-level vs Junior vs Trainee vs Internship
- Mislabelled entry-level detection (Negative test)
- Preferred experience handling
- Academic and project equivalence
"""

import pytest
from app.services.early_career_intelligence import EarlyCareerIntelligence


def test_true_fresher_detection():
    title = "Junior Software Developer - Freshers Welcome"
    desc = """
    We are looking for enthusiastic candidates to join our engineering team.
    No prior work experience is required. Freshers are eligible to apply.
    Comprehensive on-the-job training will be provided.
    Candidates should know Python and basic SQL.
    """
    cat, meta = EarlyCareerIntelligence.evaluate_job(title, desc)
    assert cat == "TRUE_FRESHER"
    assert meta["is_fresher_friendly"] is True
    assert meta["training_provided"] is True
    assert meta["min_experience_years"] == 0.0


def test_graduate_program_and_batch_detection():
    title = "Graduate Trainee - Technology (2025 Batch)"
    desc = """
    Welcome to our Global Graduate Development Program.
    Eligibility: Open to 2024 and 2025 batch engineering and science graduates.
    This is a 2-year rotational scheme with mentorship from senior leaders.
    """
    cat, meta = EarlyCareerIntelligence.evaluate_job(title, desc)
    assert cat in ["GRADUATE", "TRAINEE"]
    assert meta["is_fresher_friendly"] is True
    assert 2025 in meta["eligible_graduation_years"] or 2024 in meta["eligible_graduation_years"]
    assert meta["training_provided"] is True


def test_entry_level_and_internships():
    # Test Internship
    t_intern = "Summer Software Engineering Intern"
    d_intern = "Must be currently enrolled in an accredited BS/MS degree in Computer Science."
    cat_intern, meta_intern = EarlyCareerIntelligence.evaluate_job(t_intern, d_intern, employment_type="INTERNSHIP")
    assert cat_intern == "INTERNSHIP"
    assert meta_intern["is_fresher_friendly"] is True

    # Test Entry Level (0-1 years)
    t_entry = "Associate Data Analyst (Entry Level)"
    d_entry = "Requires 0-1 years of experience in data visualization, Excel, and SQL."
    cat_entry, meta_entry = EarlyCareerIntelligence.evaluate_job(t_entry, d_entry)
    assert cat_entry in ["ENTRY_LEVEL", "TRUE_FRESHER"]
    assert meta_entry["is_fresher_friendly"] is True


def test_mislabelled_entry_level_negative_test():
    """
    CRITICAL: A job titled 'Entry Level' or 'Junior' that requires 5 years of mandatory
    experience must NOT be classified as fresher friendly!
    """
    title = "Entry Level Full Stack Developer"
    desc = """
    About the Role:
    We are looking for a developer to lead client implementations.
    
    Minimum Qualifications:
    - 5+ years of software engineering experience in React and Node.js.
    - At least 4 years managing production cloud infrastructure on AWS.
    - Must have proven track record delivering enterprise microservices.
    """
    cat, meta = EarlyCareerIntelligence.evaluate_job(title, desc)
    assert cat == "MISLABELLED_ENTRY_LEVEL"
    assert meta["is_fresher_friendly"] is False
    assert meta["is_mislabelled"] is True
    assert meta["min_experience_years"] is not None and meta["min_experience_years"] >= 4.0
    assert "Title suggests early career" in (meta["mislabelled_warning"] or "")


def test_preferred_experience_does_not_disqualify():
    """
    A job with 0 mandatory years and 1 year preferred experience should remain fresher-friendly.
    """
    title = "Junior Associate"
    desc = """
    Requirements:
    - Bachelor's degree in Business, Finance, or related.
    - Strong communication skills.
    
    Preferred Qualifications:
    - 1 year of experience in corporate settings is a plus.
    """
    cat, meta = EarlyCareerIntelligence.evaluate_job(title, desc)
    assert meta["is_fresher_friendly"] is True
    assert meta["preferred_experience_years"] == 1.0


def test_academic_and_personal_projects_accepted():
    title = "Junior Backend Engineer"
    desc = """
    Qualifications:
    - Proficiency in Go or Python.
    - Academic projects, personal projects, or open source contributions count as experience.
    - We will train you on our specific tech stack.
    """
    cat, meta = EarlyCareerIntelligence.evaluate_job(title, desc)
    assert meta["is_fresher_friendly"] is True
    assert meta["academic_projects_accepted"] is True
    assert meta["training_provided"] is True
