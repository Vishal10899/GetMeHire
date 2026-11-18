"""
Canonical Multi-Profession Job Taxonomy for Global Job Discovery Platform.

Defines canonical job families, roles, skills, search synonyms, and aliases.
"""
from typing import Dict, List, Any, Optional

TAXONOMY_FAMILIES: Dict[str, Dict[str, Any]] = {
    "CUSTOMER_SUPPORT": {
        "key": "CUSTOMER_SUPPORT",
        "label": "Customer Support & BPO",
        "category": "Customer Support, Customer Service, and BPO",
        "description": "Customer care, technical support, help desk, client success & escalation operations",
        "icon": "Headphones",
        "canonical_roles": [
            "Customer Support Specialist",
            "Technical Support Engineer",
            "Customer Success Manager",
            "Help Desk Technician",
            "Tier 2 Support Specialist",
            "Client Services Representative",
            "Call Center Agent",
            "Incident & Escalation Manager",
            "Support Operations Lead"
        ],
        "core_skills": [
            "Zendesk", "Intercom", "Salesforce Service Cloud", "Freshdesk", "Jira Service Desk",
            "Customer Retention", "Troubleshooting", "SLA Management", "Ticket Resolution", "Omnichannel Support"
        ],
        "synonyms": ["customer support", "customer service", "helpdesk", "tech support", "client support", "bpo", "call center", "client success"],
        "legacy_aliases": []
    },
    "ENGINEERING": {
        "key": "ENGINEERING",
        "label": "Software & IT",
        "category": "Software Engineering and IT",
        "description": "Backend, frontend, full stack, cloud infrastructure, DevOps, systems & QA engineering",
        "icon": "Code2",
        "canonical_roles": [
            "Software Engineer",
            "Backend Engineer",
            "Frontend Engineer",
            "Full Stack Developer",
            "DevOps / SRE Engineer",
            "Cloud Infrastructure Architect",
            "Systems Engineer",
            "QA / Test Automation Engineer",
            "Security Engineer"
        ],
        "core_skills": [
            "Python", "FastAPI", "React", "TypeScript", "Node.js", "Docker", "Kubernetes", "PostgreSQL",
            "AWS", "Go", "Java", "C++", "Terraform", "CI/CD", "GraphQL", "REST APIs"
        ],
        "synonyms": ["software engineer", "software developer", "coder", "programmer", "devops", "sre", "web developer", "systems engineer", "it"],
        "legacy_aliases": ["SOFTWARE_IT"]
    },
    "HEALTHCARE_MEDICAL": {
        "key": "HEALTHCARE_MEDICAL",
        "label": "Healthcare & Medical",
        "category": "Healthcare and Medical",
        "description": "Clinical care, surgery, nursing, medical research, pharmacy, healthcare operations & health informatics",
        "icon": "HeartPulse",
        "canonical_roles": [
            "Surgeon",
            "Senior Surgeon",
            "General Surgeon",
            "Orthopedic Surgeon",
            "Physician / Doctor",
            "Registered Nurse (RN)",
            "Clinical Specialist",
            "Medical Assistant",
            "Healthcare Administrator",
            "Health Informatics Specialist",
            "Clinical Research Coordinator",
            "Pharmacist",
            "Medical Technologist",
            "Physician Assistant"
        ],
        "core_skills": [
            "Patient Care", "Surgery", "Clinical Documentation", "EHR / EMR", "Epic Systems", "HIPAA Compliance",
            "Triage", "Medical Billing", "Pharmacology", "Phlebotomy", "Healthcare Quality"
        ],
        "synonyms": ["surgeon", "surgery", "surgical", "doctor", "physician", "nurse", "rn", "healthcare", "medical", "clinical", "hospital", "pharma", "pediatrician", "cardiologist", "oncologist", "anesthesiologist", "radiologist"],
        "legacy_aliases": []
    },
    "SALES_BIZDEV": {
        "key": "SALES_BIZDEV",
        "label": "Sales & Business Dev",
        "category": "Sales, Marketing, and Business Development",
        "description": "Account executives, SDR/BDR, sales leadership, partnerships & enterprise solutions",
        "icon": "TrendingUp",
        "canonical_roles": [
            "Account Executive",
            "Business Development Representative (BDR/SDR)",
            "Sales Manager",
            "Enterprise Account Director",
            "Partnership Manager",
            "Solutions Engineer"
        ],
        "core_skills": [
            "Salesforce", "B2B SaaS Sales", "Pipeline Generation", "Cold Outreach",
            "Contract Negotiation", "Lead Qualification", "HubSpot", "CRM"
        ],
        "synonyms": ["sales", "account executive", "bdr", "sdr", "business development", "partnerships", "sales manager"],
        "legacy_aliases": ["SALES_MARKETING_BIZDEV"]
    },
    "MARKETING_GROWTH": {
        "key": "MARKETING_GROWTH",
        "label": "Marketing & Growth",
        "category": "Sales, Marketing, and Business Development",
        "description": "Growth marketing, SEO, content strategy, brand marketing & demand generation",
        "icon": "Megaphone",
        "canonical_roles": [
            "Marketing Manager",
            "Growth Marketing Lead",
            "Content Strategist",
            "SEO / SEM Specialist",
            "Brand Marketing Lead",
            "Demand Generation Manager"
        ],
        "core_skills": [
            "SEO", "Google Analytics", "Content Marketing", "Paid Acquisition", "Copywriting",
            "Email Marketing", "Brand Strategy", "Growth Loops"
        ],
        "synonyms": ["marketing", "growth", "seo", "content", "brand", "communications", "advertising"],
        "legacy_aliases": []
    },
    "FINANCE_ACCOUNTING": {
        "key": "FINANCE_ACCOUNTING",
        "label": "Finance & Banking",
        "category": "Finance, Accounting, and Banking",
        "description": "Corporate finance, FP&A, accounting, auditing, treasury, tax & investment banking",
        "icon": "Landmark",
        "canonical_roles": [
            "Financial Analyst",
            "Senior Accountant",
            "FP&A Manager",
            "Controller",
            "Tax Specialist",
            "Internal Auditor",
            "Treasury Analyst",
            "Payroll Administrator",
            "Accounts Payable / Receivable Lead"
        ],
        "core_skills": [
            "Financial Modeling", "FP&A", "GAAP", "QuickBooks", "Excel / Financial Sheets",
            "Tax Compliance", "NetSuite", "General Ledger", "Audit Preparation", "Cash Flow Forecasting"
        ],
        "synonyms": ["finance", "accountant", "cpa", "accounting", "banking", "tax", "treasury", "audit", "fp&a", "payroll"],
        "legacy_aliases": ["FINANCE_LEGAL"]
    },
    "DATA_AI": {
        "key": "DATA_AI",
        "label": "Data & AI",
        "category": "Data Analytics, Data Science, and AI",
        "description": "Machine learning, AI engineering, data science, business intelligence & data pipelines",
        "icon": "Brain",
        "canonical_roles": [
            "AI Engineer",
            "Senior AI Engineer",
            "Applied AI Engineer",
            "Generative AI Engineer",
            "LLM Engineer",
            "Data Scientist",
            "Machine Learning Engineer",
            "AI Research Engineer",
            "Data Analyst",
            "Data Engineer",
            "Business Intelligence (BI) Analyst",
            "Analytics Engineer",
            "MLOps Engineer"
        ],
        "core_skills": [
            "Python", "SQL", "PyTorch", "TensorFlow", "Pandas", "Scikit-Learn",
            "Snowflake", "dbt", "Spark", "Tableau", "Power BI", "LLMs", "Vector DBs"
        ],
        "synonyms": ["ai engineer", "data science", "data analyst", "data engineer", "machine learning", "ai", "artificial intelligence", "deep learning", "nlp", "llm", "generative ai", "ml engineer"],
        "legacy_aliases": []
    },
    "HR_RECRUITMENT": {
        "key": "HR_RECRUITMENT",
        "label": "HR & Talent",
        "category": "HR and Recruitment",
        "description": "Talent acquisition, technical recruiting, people operations, HR business partners & compensation",
        "icon": "Users",
        "canonical_roles": [
            "Technical Recruiter",
            "HR Business Partner (HRBP)",
            "People Operations Manager",
            "Talent Acquisition Lead",
            "Compensation & Benefits Analyst",
            "Employee Experience Specialist",
            "HR Generalist"
        ],
        "core_skills": [
            "Talent Sourcing", "Interviewing", "Workday", "Greenhouse ATS", "Lever",
            "Employee Relations", "Onboarding", "Performance Management", "HR Compliance", "HRIS"
        ],
        "synonyms": ["recruiter", "recruiting", "talent acquisition", "human resources", "hr", "people ops", "headhunter"],
        "legacy_aliases": []
    },
    "OPERATIONS_LOGISTICS": {
        "key": "OPERATIONS_LOGISTICS",
        "label": "Operations & Logistics",
        "category": "Operations, Logistics, and Supply Chain",
        "description": "Supply chain, procurement, logistics, fulfillment, facilities & business operations",
        "icon": "Truck",
        "canonical_roles": [
            "Operations Manager",
            "Supply Chain Planner",
            "Procurement Specialist",
            "Logistics Coordinator",
            "Warehouse Supervisor",
            "Inventory Control Specialist",
            "Facilities Manager",
            "Fulfillment Lead"
        ],
        "core_skills": [
            "Supply Chain Management", "Procurement", "Inventory Control", "Vendor Management",
            "Logistics Planning", "ERP Systems", "SAP", "Process Optimization", "Lean / Six Sigma"
        ],
        "synonyms": ["operations", "logistics", "supply chain", "warehouse", "procurement", "inventory", "fulfillment", "facilities"],
        "legacy_aliases": ["OPERATIONS_PEOPLE"]
    },
    "EDUCATION_TRAINING": {
        "key": "EDUCATION_TRAINING",
        "label": "Education & Training",
        "category": "Education and Training",
        "description": "Instructional design, corporate training, teaching, curriculum development & academic advising",
        "icon": "GraduationCap",
        "canonical_roles": [
            "Instructional Designer",
            "Corporate Trainer",
            "Curriculum Developer",
            "Teacher / Educator",
            "Learning & Development (L&D) Specialist",
            "Academic Advisor",
            "E-Learning Specialist"
        ],
        "core_skills": [
            "Curriculum Design", "Adult Learning Theory", "LMS (Canvas/Blackboard)", "Instructional Design",
            "Workshop Facilitation", "Articulate 360", "Student Assessment", "E-Learning Development"
        ],
        "synonyms": ["teacher", "educator", "trainer", "training", "curriculum", "instructional design", "professor", "tutor"],
        "legacy_aliases": []
    },
    "MANUFACTURING_TRADES": {
        "key": "MANUFACTURING_TRADES",
        "label": "Manufacturing & Trades",
        "category": "Engineering, Manufacturing, and Skilled Trades",
        "description": "Mechanical/electrical engineering, CNC machining, assembly, fabrication & field maintenance",
        "icon": "Hammer",
        "canonical_roles": [
            "Manufacturing Engineer",
            "Maintenance Technician",
            "CNC Machinist",
            "Quality Control Inspector",
            "Industrial Electrician",
            "Plant Operations Specialist",
            "Assembly Technician",
            "Field Service Engineer"
        ],
        "core_skills": [
            "CAD / SolidWorks", "CNC Programming", "Quality Assurance / SPC", "PLC Programming",
            "Blueprint Reading", "OSHA Safety", "Preventative Maintenance", "Welding / Fabrication"
        ],
        "synonyms": ["manufacturing", "machinist", "technician", "electrician", "mechanic", "trades", "plant", "fabrication", "hardware"],
        "legacy_aliases": []
    },
    "HOSPITALITY_RETAIL": {
        "key": "HOSPITALITY_RETAIL",
        "label": "Hospitality & Retail",
        "category": "Hospitality, Retail, and Customer-facing services",
        "description": "Retail management, restaurant operations, guest experience, merchandising & store leadership",
        "icon": "Store",
        "canonical_roles": [
            "Store Manager",
            "Assistant Store Manager",
            "Shift Supervisor",
            "Guest Services Associate",
            "Retail Merchandiser",
            "Restaurant General Manager",
            "Hospitality Coordinator",
            "Front Desk Agent"
        ],
        "core_skills": [
            "Retail Operations", "POS Systems", "Inventory Management", "Customer Satisfaction",
            "Cash Handling", "Visual Merchandising", "Staff Scheduling", "Loss Prevention", "Food Safety (ServSafe)"
        ],
        "synonyms": ["retail", "store manager", "cashier", "hospitality", "restaurant", "hotel", "guest service", "merchandising"],
        "legacy_aliases": []
    },
    "LEGAL_ADMIN": {
        "key": "LEGAL_ADMIN",
        "label": "Legal & Administration",
        "category": "Legal, Administration, and other professional roles",
        "description": "Corporate counsel, paralegal services, regulatory compliance, executive assistance & office administration",
        "icon": "Scale",
        "canonical_roles": [
            "Corporate Counsel / Legal Counsel",
            "Paralegal",
            "Compliance Officer",
            "Contracts Specialist",
            "Executive Assistant",
            "Office Administrator",
            "Legal Operations Manager"
        ],
        "core_skills": [
            "Contract Review", "Regulatory Compliance", "Legal Drafting", "Due Diligence",
            "Corporate Governance", "Executive Scheduling", "Document Management", "Records Management"
        ],
        "synonyms": ["legal", "paralegal", "counsel", "compliance", "admin", "executive assistant", "contracts", "law"],
        "legacy_aliases": []
    },
    "PRODUCT_DESIGN": {
        "key": "PRODUCT_DESIGN",
        "label": "Product & Design",
        "category": "Product Management and UX/UI Design",
        "description": "Product management, UI/UX design, visual design, user research & design systems",
        "icon": "Palette",
        "canonical_roles": [
            "Product Manager",
            "Senior Product Manager",
            "Product Designer (UI/UX)",
            "User Researcher",
            "Design Systems Lead",
            "Visual / Brand Designer"
        ],
        "core_skills": [
            "Figma", "User Research", "Wireframing", "Product Strategy", "Design Systems",
            "Prototyping", "Roadmapping", "Agile/Scrum", "A/B Testing", "User Story Mapping"
        ],
        "synonyms": ["product manager", "pm", "product design", "ux", "ui", "designer", "user research"],
        "legacy_aliases": []
    }
}

LEGACY_ALIAS_MAP: Dict[str, str] = {
    "SOFTWARE_IT": "ENGINEERING",
    "FINANCE_LEGAL": "FINANCE_ACCOUNTING",
    "OPERATIONS_PEOPLE": "OPERATIONS_LOGISTICS",
    "SALES_MARKETING_BIZDEV": "SALES_BIZDEV",
}

def resolve_profession_key(key: Optional[str]) -> Optional[str]:
    """Resolve a profession key, supporting canonical keys and legacy aliases."""
    if not key:
        return None
    k = key.strip().upper()
    if k in TAXONOMY_FAMILIES:
        return k
    if k in LEGACY_ALIAS_MAP:
        return LEGACY_ALIAS_MAP[k]
    return k

def get_all_profession_keys() -> List[str]:
    """Returns list of canonical profession keys."""
    return list(TAXONOMY_FAMILIES.keys())
