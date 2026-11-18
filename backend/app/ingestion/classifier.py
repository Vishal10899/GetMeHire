"""
Intelligent Rule-Based Multi-Profession Job Classifier.

Classifies jobs into canonical job families (all 12 PRD tracks + Product & Design)
with explainable confidence scoring and high precision disambiguation.
"""
import re
from typing import Tuple, Dict, Any, Optional
from app.ingestion.taxonomy import TAXONOMY_FAMILIES, resolve_profession_key

def classify_profession_with_confidence(title: str, department: str = "", description: str = "") -> Tuple[str, float]:
    """
    Deterministic rule-based classification returning (profession_key, confidence_score).
    Prioritizes primary functional role over industry domain modifier.
    """
    t = (title or "").lower().strip()
    d = (department or "").lower().strip()

    # ----------------------------------------------------
    # Priority Tier 1: Functional Roles that frequently carry industry modifiers
    # (e.g. "Frontend Engineer - Billing", "Account Executive - Healthcare", "Recruiter - Tech")
    # ----------------------------------------------------

    # 1. Primary Engineering & Development
    if any(k in t for k in [
        "frontend engineer", "backend engineer", "software engineer", "full stack", "web developer",
        "web engineer", "application developer", "frontend developer", "backend developer",
        "infrastructure engineer", "devops", "site reliability", "sre", "mobile engineer",
        "ios engineer", "android engineer", "systems engineer", "firmware engineer",
        "security engineer", "qa engineer", "test engineer", "cloud engineer", "compiler engineer"
    ]) or re.search(r"\b(swe|sde|devops)\b", t):
        return "ENGINEERING", 0.95

    # 2. Primary Sales & Business Development
    if any(k in t for k in [
        "account executive", "sales manager", "sales representative", "enterprise sales",
        "commercial sales", "solutions engineer", "sales engineer", "account manager",
        "sales lead", "sales director", "business development representative",
        "strategic partnerships", "channel sales", "inside sales", "deal desk"
    ]) or re.search(r"\b(bdr|sdr|ae|gtm lead)\b", t):
        return "SALES_BIZDEV", 0.95

    # 3. Primary Data & Artificial Intelligence
    if any(k in t for k in [
        "data scientist", "data analyst", "data engineer", "machine learning",
        "ai engineer", "generative ai", "genai", "artificial intelligence", "ai/ml", "ai / ml",
        "ai research", "ml engineer", "deep learning", "nlp engineer", "computer vision",
        "analytics engineer", "bi analyst", "business intelligence", "applied ai", "llm engineer",
        "prompt engineer", "ai specialist"
    ]):
        return "DATA_AI", 0.95

    # 4. Primary Product & Design
    if any(k in t for k in [
        "product manager", "product lead", "head of product", "vp of product",
        "director of product", "product design", "ui/ux", "user researcher",
        "creative director", "design systems lead", "visual designer"
    ]) or re.search(r"\b(ux|ui/ux|ui designer)\b", t):
        return "PRODUCT_DESIGN", 0.95

    # 5. Customer Support & Success
    if any(k in t for k in [
        "customer support", "customer service", "helpdesk", "help desk",
        "client support", "client services", "technical support", "tier 2 support",
        "tier 3 support", "call center", "care agent", "escalation manager",
        "support specialist", "customer care", "customer success"
    ]):
        return "CUSTOMER_SUPPORT", 0.95

    # 6. HR & Recruitment
    if any(k in t for k in [
        "recruiter", "recruiting", "talent acquisition", "human resources",
        "people partner", "people operations", "hrbp", "compensation",
        "total rewards", "benefits manager", "benefits program", "employee relations",
        "talent sourcing", "sourcer", "people coordinator"
    ]) or re.search(r"\b(hr|hrbp)\b", t):
        return "HR_RECRUITMENT", 0.95

    # 7. Finance, Accounting & Banking
    if any(k in t for k in [
        "accountant", "accounting", "cpa", "controller", "treasury", "audit",
        "fp&a", "payroll", "billing", "accounts payable", "accounts receivable",
        "ar analyst", "ap analyst", "credit risk", "underwriter", "finops",
        "tax analyst", "tax manager", "financial analyst", "financial planning"
    ]) or ("finance" in t and "engineer" not in t and "sales" not in t):
        return "FINANCE_ACCOUNTING", 0.95

    # 8. Legal, Compliance & Public Policy
    if any(k in t for k in [
        "counsel", "legal", "paralegal", "compliance", "regulatory", "contracts manager",
        "executive assistant", "office administrator", "corporate secretary", "chief of staff",
        "public policy", "policy advocacy", "government affairs", "community engagement"
    ]) or re.search(r"\b(attorney|lawyer)\b", t):
        return "LEGAL_ADMIN", 0.95

    # 9. Education, Training & Content
    if any(k in t for k in [
        "curriculum", "instructional designer", "educator", "teacher", "professor",
        "tutor", "corporate trainer", "learning and development", "academic advisor",
        "faculty", "technical instructor", "course instructor", "field enablement", "sales enablement"
    ]) or ("training" in t and "ai platform" not in t and "model" not in t):
        return "EDUCATION_TRAINING", 0.90

    # 10. Healthcare & Medical
    if any(k in t for k in [
        "surgeon", "surgery", "surgical", "physician", "doctor", "medical director",
        "nurse", "registered nurse", "clinical", "medical", "healthcare", "pharmacist",
        "pharmacy", "medical technologist", "patient care", "health informatics",
        "medical assistant", "therapist", "dietitian", "anesthesiologist", "cardiologist",
        "pediatrician", "radiologist", "oncologist", "dentist", "psychiatrist"
    ]) or re.search(r"\b(rn|lpn|np|pa|md|do)\b", t):
        return "HEALTHCARE_MEDICAL", 0.95

    # 11. Hospitality, Food & Retail
    if any(k in t for k in [
        "store manager", "assistant store manager", "shift supervisor", "assistant coach",
        "barista", "cashier", "hospitality", "restaurant", "hotel", "guest service",
        "food service", "merchandiser", "store associate", "culinary", "chef", "cook",
        "head coach", "general manager"
    ]) and ("swe" not in t and "software" not in t):
        return "HOSPITALITY_RETAIL", 0.95

    # 12. Manufacturing & Skilled Trades
    if any(k in t for k in [
        "machinist", "cnc", "welder", "electrician", "technician", "fabrication",
        "assembly", "plant operations", "hardware engineer", "mechanical engineer",
        "maintenance technician", "quality inspector"
    ]) or ("manufacturing" in t and not any(s in t for s in ["sales", "account executive", "recruiter", "counsel", "marketing"])):
        return "MANUFACTURING_TRADES", 0.90

    # 13. Marketing & Growth
    if any(k in t for k in [
        "marketing", "growth lead", "content writer", "seo", "brand",
        "communications", "demand gen", "copywriter", "public relations", "pr manager"
    ]):
        return "MARKETING_GROWTH", 0.95

    # 14. Operations, Logistics & Supply Chain
    if any(k in t for k in [
        "operations manager", "logistics", "supply chain", "procurement",
        "warehouse", "inventory", "fulfillment", "vendor management", "workplace coordinator",
        "program manager", "project manager"
    ]):
        return "OPERATIONS_LOGISTICS", 0.90

    # ----------------------------------------------------
    # Tier 2: Department-based inference (when title is ambiguous)
    # ----------------------------------------------------
    if "engineering" in d or "dev" in d or "compute" in d:
        return "ENGINEERING", 0.85
    if "sales" in d or "business development" in d:
        return "SALES_BIZDEV", 0.85
    if "recruiting" in d or "talent" in d or "people" in d:
        return "HR_RECRUITMENT", 0.85
    if "finance" in d or "accounting" in d:
        return "FINANCE_ACCOUNTING", 0.85
    if "legal" in d or "compliance" in d or "policy" in d:
        return "LEGAL_ADMIN", 0.85
    if "marketing" in d or "communications" in d:
        return "MARKETING_GROWTH", 0.85
    if "product" in d or "design" in d:
        return "PRODUCT_DESIGN", 0.80
    if "support" in d or "user operations" in d:
        return "CUSTOMER_SUPPORT", 0.80
    if "retail" in d or "restaurant" in d:
        return "HOSPITALITY_RETAIL", 0.85
    if "clinical" in d or "healthcare" in d:
        return "HEALTHCARE_MEDICAL", 0.85

    # General Engineering fallback if "engineer" or "developer" in title
    if "engineer" in t or "developer" in t:
        return "ENGINEERING", 0.85

    # Fallback to OPERATIONS_LOGISTICS with explicit 0.50 score (not disguised as high confidence)
    return "OPERATIONS_LOGISTICS", 0.50

def classify_profession(title: str, department: str = "", description: str = "") -> str:
    """Convenience helper returning just the canonical profession key."""
    prof, _ = classify_profession_with_confidence(title, department, description)
    return prof
