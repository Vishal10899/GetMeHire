"""
Role-Specific Resume Template & Architecture Intelligence Engine.

Provides authoritative recruitment standards, section hierarchies, ATS optimization
guidelines, and styling specifications tailored to 16+ core global professions:
- Software Engineers & DevOps
- AI / Machine Learning & LLM Engineers
- Data Analysts & Analytics Engineers
- Data Scientists & Research Scientists
- Business Analysts & Strategy Specialists
- Product Managers & Group PMs
- Banking & Corporate Finance Professionals
- Accountants, CPAs & Auditors
- Enterprise Sales & Business Development Executives
- Marketing & Growth Directors
- Healthcare, Nursing & Allied Health Specialists
- Doctors, Physicians & Surgeons (Clinical CV structure)
- Human Resources & Talent Leaders
- Legal, Corporate Counsel & Compliance Officers
- Operations, Supply Chain & Logistics Managers
- Executive Leadership (C-Suite, VP, Managing Director)
"""
import re
from typing import Dict, List, Any, Optional

ROLE_TEMPLATE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "fresher_graduate": {
        "id": "fresher_graduate",
        "name": "Fresher & Recent Graduate",
        "profession": "EARLY_CAREER",
        "description": "Optimized for college graduates, freshers, and first-time job seekers. Places Education and Key Academic / Capstone Projects before Work Experience, spotlighting foundational coursework, academic honors, technical skills, and internships.",
        "recommended_sections_order": [
            "contact", "summary", "education", "technical_skills", "projects", "work_experience", "certifications"
        ],
        "section_titles": {
            "summary": "Career Objective & Profile",
            "education": "Education & Academic Honors",
            "technical_skills": "Core Technical Skills",
            "projects": "Academic & Capstone Projects",
            "work_experience": "Internships & Relevant Experience",
            "certifications": "Certifications & Coursework",
        },
        "color_palette": {
            "primary": "#0f172a",    # Slate 900
            "accent": "#0d9488",     # Teal 600
            "divider": "#14b8a6",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Lead with academic achievements, GPA/honors, relevant coursework, and university leadership.",
            "Spotlight capstone and personal projects with architecture details and GitHub repositories.",
            "Present internships and student worker roles with tangible learning outcomes and deliverables.",
        ],
        "power_verbs": [
            "Developed", "Built", "Designed", "Implemented", "Researched",
            "Collaborated", "Presented", "Programmed", "Analyzed", "Authored"
        ],
        "ats_priority_keywords": [
            "Bachelor's Degree", "Computer Science", "Engineering", "Algorithms",
            "Data Structures", "Python", "Java", "SQL", "Git", "Problem Solving"
        ]
    },
    "fresher_internship": {
        "id": "fresher_internship",
        "name": "Student & Internship Discovery",
        "profession": "EARLY_CAREER",
        "description": "Tailored for undergraduate and master's students pursuing summer, semester, or co-op internships. Emphasizes coursework, hackathons, open-source contributions, and university leadership.",
        "recommended_sections_order": [
            "contact", "summary", "education", "technical_skills", "projects", "certifications", "work_experience"
        ],
        "section_titles": {
            "summary": "Student Profile",
            "education": "University Education & Expected Graduation",
            "technical_skills": "Technical Proficiencies",
            "projects": "Software Projects & Hackathons",
            "certifications": "Coursework & Honors",
            "work_experience": "Campus Leadership & Work Experience",
        },
        "color_palette": {
            "primary": "#1e1b4b",    # Indigo 950
            "accent": "#6366f1",     # Indigo 500
            "divider": "#818cf8",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Include your degree program, expected graduation month and year, and major GPA.",
            "Feature hackathon participation, code competition awards, and open-source contributions.",
            "Highlight self-directed learning and foundational technical languages.",
        ],
        "power_verbs": [
            "Constructed", "Engineered", "Created", "Demonstrated", "Participated",
            "Solved", "Calculated", "Tested", "Contributed", "Organized"
        ],
        "ats_priority_keywords": [
            "Internship", "Co-op", "Undergraduate", "Expected Graduation", "Python",
            "JavaScript", "Git", "Object-Oriented Programming", "Teamwork"
        ]
    },
    "software_engineering": {
        "id": "software_engineering",
        "name": "Software & DevOps Engineering",
        "profession": "ENGINEERING",
        "description": "Engineered for Software Developers, Systems Architects, and DevOps engineers. Prioritizes technical stack, architectural impact, scale, and high-impact repositories.",
        "recommended_sections_order": [
            "contact", "summary", "technical_skills", "work_experience", "projects", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Professional Summary",
            "technical_skills": "Technical Skills & Architecture",
            "work_experience": "Engineering Experience",
            "projects": "Technical Projects & Open Source",
            "education": "Education",
            "certifications": "Certifications & Cloud Credentials",
        },
        "color_palette": {
            "primary": "#0f172a",    # Slate 900
            "accent": "#2563eb",     # Royal Blue
            "divider": "#3b82f6",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Lead experience bullets with systems architecture, throughput, latency, or concurrency improvements.",
            "Group technical skills into Languages, Frameworks, Cloud/DevOps, and Databases.",
            "Highlight production scale (e.g. QPS, daily active users, petabytes processed).",
        ],
        "power_verbs": [
            "Architected", "Engineered", "Deployed", "Refactored", "Containerized",
            "Automated", "Orchestrated", "Scaled", "Optimized", "Benchmarked"
        ],
        "ats_priority_keywords": [
            "Python", "Go", "Java", "TypeScript", "React", "Docker", "Kubernetes",
            "AWS", "GCP", "PostgreSQL", "CI/CD", "Distributed Systems", "Microservices"
        ],
    },
    "ai_ml_engineer": {
        "id": "ai_ml_engineer",
        "name": "AI, Machine Learning & LLM Specialist",
        "profession": "DATA_AI",
        "description": "Optimized for AI Researchers, ML Engineers, and LLM Specialists. Focuses on model architectures, fine-tuning, training pipelines, and production inference optimization.",
        "recommended_sections_order": [
            "contact", "summary", "technical_skills", "work_experience", "projects", "education", "certifications"
        ],
        "section_titles": {
            "summary": "AI & Research Summary",
            "technical_skills": "AI/ML Competencies & Frameworks",
            "work_experience": "Applied AI Experience",
            "projects": "Model Research & AI Deployments",
            "education": "Academic Background",
            "certifications": "AI Certifications & Publications",
        },
        "color_palette": {
            "primary": "#1e1b4b",    # Indigo 950
            "accent": "#4f46e5",     # Indigo 600
            "divider": "#6366f1",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Specify model families (e.g. Transformer, Diffusion, LLMs, RAG, LoRA).",
            "Quantify inference latency reductions, throughput gains, or accuracy/F1 score improvements.",
            "List compute frameworks (PyTorch, TensorFlow, vLLM, TensorRT, Triton, CUDA).",
        ],
        "power_verbs": [
            "Trained", "Fine-tuned", "Quantized", "Evaluated", "Synthesized",
            "Engineered", "Prompted", "Distilled", "Benchmarked", "Productionized"
        ],
        "ats_priority_keywords": [
            "PyTorch", "Hugging Face", "LLMs", "RAG", "Generative AI", "Vector Databases",
            "LangChain", "CUDA", "Model Evaluation", "Diffusion Models", "Transformers"
        ],
    },
    "data_analyst": {
        "id": "data_analyst",
        "name": "Data Analytics & Business Intelligence",
        "profession": "DATA_AI",
        "description": "Structured for Data Analysts and BI Specialists. Emphasizes executive dashboards, revenue insights, SQL queries, and stakeholder decision support.",
        "recommended_sections_order": [
            "contact", "summary", "technical_skills", "work_experience", "projects", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Analytics Profile",
            "technical_skills": "Analytics & Visualization Stack",
            "work_experience": "Analytics & Reporting Experience",
            "projects": "Analytics Dashboards & Data Products",
            "education": "Education",
            "certifications": "Certifications",
        },
        "color_palette": {
            "primary": "#042f2e",    # Teal 950
            "accent": "#0d9488",     # Teal 600
            "divider": "#14b8a6",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Highlight business metric outcomes (e.g. identified $1.2M in leakage, increased conversion by 14%).",
            "Emphasize SQL mastery, statistical rigor, and executive dashboard adoption.",
            "Reference data warehouse technologies (Snowflake, BigQuery, dbt, Tableau, Power BI).",
        ],
        "power_verbs": [
            "Analyzed", "Modeled", "Visualized", "Synthesized", "Forecasted",
            "Audited", "Identified", "Dash-boarded", "Automated", "Delivered"
        ],
        "ats_priority_keywords": [
            "SQL", "Tableau", "Power BI", "dbt", "Snowflake", "BigQuery",
            "A/B Testing", "Python", "ETL Pipelines", "Executive Reporting"
        ],
    },
    "data_scientist": {
        "id": "data_scientist",
        "name": "Data Science & Advanced Analytics",
        "profession": "DATA_AI",
        "description": "Tailored for Data Scientists and Applied Researchers. Centers on predictive modeling, causal inference, feature engineering, and statistical experimentation.",
        "recommended_sections_order": [
            "contact", "summary", "technical_skills", "work_experience", "projects", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Data Science Summary",
            "technical_skills": "Statistical & Modeling Stack",
            "work_experience": "Data Science Experience",
            "projects": "Predictive Models & Experimentation",
            "education": "Education & Degrees",
            "certifications": "Certifications & Publications",
        },
        "color_palette": {
            "primary": "#0f172a",
            "accent": "#0284c7",     # Sky Blue
            "divider": "#38bdf8",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Specify algorithmic techniques (XGBoost, Random Forests, Causal Inference, Bayesian).",
            "Document business lift generated through algorithm deployment.",
            "Include sample size, cross-validation methods, and metric benchmarks (AUC-ROC, RMSE, MAPE).",
        ],
        "power_verbs": [
            "Formulated", "Hypothesized", "Engineered", "Predicted", "Clustered",
            "Validated", "Optimized", "Segmented", "Simulated", "Published"
        ],
        "ats_priority_keywords": [
            "Python", "R", "Scikit-Learn", "XGBoost", "Hypothesis Testing", "Causal Inference",
            "Feature Engineering", "Pandas", "Statistical Modeling", "MLOps"
        ],
    },
    "product_manager": {
        "id": "product_manager",
        "name": "Product Management & Ownership",
        "profession": "PRODUCT_MANAGEMENT",
        "description": "Engineered for Product Managers, Technical PMs, and Group PMs. Highlights product vision, roadmap execution, user growth, and cross-functional leadership.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "projects", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Executive Product Profile",
            "work_experience": "Product Leadership Experience",
            "technical_skills": "Product Strategy & Technical Acumen",
            "projects": "Key Product Launches",
            "education": "Education",
            "certifications": "Certifications",
        },
        "color_palette": {
            "primary": "#18181b",    # Zinc 900
            "accent": "#7c3aed",     # Violet 600
            "divider": "#a855f7",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Highlight product discovery, 0-to-1 launches, and scale milestones.",
            "Quantify impact on ARR, GMV, monthly active users (MAU), churn reduction, or NPS.",
            "Demonstrate collaboration across Engineering, UX Design, Data, and Go-to-Market.",
        ],
        "power_verbs": [
            "Spearheaded", "Launched", "Prioritized", "Defined", "Scaled",
            "Navigated", "Unified", "Iterated", "Evangelized", "Championed"
        ],
        "ats_priority_keywords": [
            "Product Strategy", "Roadmapping", "User Stories", "PRDs", "Agile / Scrum",
            "A/B Testing", "Go-To-Market (GTM)", "User Research", "Metrics & KPIs", "Cross-Functional"
        ],
    },
    "business_analyst": {
        "id": "business_analyst",
        "name": "Business Analysis & Operations Strategy",
        "profession": "OPERATIONS_LOGISTICS",
        "description": "Built for Business Analysts, Process Architects, and Strategy Consultants. Focuses on requirements gathering, workflow optimization, and ROI delivery.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Professional Summary",
            "work_experience": "Business & Systems Experience",
            "technical_skills": "Methodologies & Toolsets",
            "education": "Education",
            "certifications": "Certifications (CBAP, PMI-PBA)",
        },
        "color_palette": {
            "primary": "#1e293b",
            "accent": "#059669",     # Emerald 600
            "divider": "#10b981",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Detail business requirements documentation (BRD, FRD, User Acceptance Testing).",
            "Quantify cost reductions, efficiency improvements, and process cycle time decreases.",
            "List enterprise platforms (Salesforce, SAP, Jira, Confluence, Visio).",
        ],
        "power_verbs": [
            "Streamlined", "Elicited", "Mapped", "Facilitated", "Synthesized",
            "Standardized", "Transformed", "Validated", "Reengineered", "Delivered"
        ],
        "ats_priority_keywords": [
            "Business Requirements (BRD)", "Process Mapping", "UAT Testing", "Gap Analysis",
            "Stakeholder Management", "Jira", "SQL", "Agile", "Cost-Benefit Analysis"
        ],
    },
    "banking_finance": {
        "id": "banking_finance",
        "name": "Banking, Investment & Corporate Finance",
        "profession": "FINANCE_ACCOUNTING",
        "description": "Standardized for Investment Bankers, FP&A Managers, and Financial Analysts. Emphasizes financial modeling, P&L management, M&A transactions, and valuation.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Executive Finance Summary",
            "work_experience": "Financial & Transaction Experience",
            "technical_skills": "Financial Modeling & Valuation Stack",
            "education": "Education & Honors",
            "certifications": "Certifications (CFA, Series 7/63)",
        },
        "color_palette": {
            "primary": "#111827",
            "accent": "#b45309",     # Amber 700 / Gold
            "divider": "#d97706",
            "font_family": "Times-Roman",
        },
        "content_guidelines": [
            "Quantify deal sizes, asset volumes, transaction values, and portfolio returns.",
            "Detail DCF, LBO, comps modeling, variance analysis, and capital allocation.",
            "Reference regulatory frameworks (FINRA, SEC, SOX, Basel III).",
        ],
        "power_verbs": [
            "Underwrote", "Structured", "Forecasted", "Executed", "Allocated",
            "Managed", "Negotiated", "Monitored", "Valued", "Advised"
        ],
        "ats_priority_keywords": [
            "Financial Modeling", "DCF", "LBO", "P&L Management", "Variance Analysis",
            "Valuation", "Due Diligence", "Capital Markets", "Bloomberg Terminal", "CFA"
        ],
    },
    "accountant_audit": {
        "id": "accountant_audit",
        "name": "Accounting, Audit & Tax (CPA)",
        "profession": "FINANCE_ACCOUNTING",
        "description": "Designed for Certified Public Accountants, Senior Auditors, and Controllers. Emphasizes GAAP/IFRS adherence, internal controls, audit engagements, and tax compliance.",
        "recommended_sections_order": [
            "contact", "summary", "certifications", "work_experience", "technical_skills", "education"
        ],
        "section_titles": {
            "summary": "Professional Summary",
            "certifications": "Licensure & Certifications (CPA)",
            "work_experience": "Accounting & Audit Experience",
            "technical_skills": "Accounting Software & ERPs",
            "education": "Education",
        },
        "color_palette": {
            "primary": "#0f172a",
            "accent": "#0369a1",     # Sky 700
            "divider": "#0284c7",
            "font_family": "Times-Roman",
        },
        "content_guidelines": [
            "Place active CPA, ACCA, or CA credential directly below contact header.",
            "Document general ledger reconciliation, month-end close acceleration, and tax returns filed.",
            "List ERP platforms (NetSuite, SAP, QuickBooks, Workday Financials).",
        ],
        "power_verbs": [
            "Audited", "Reconciled", "Consolidated", "Complied", "Administered",
            "Prepared", "Formulated", "Verified", "Streamlined", "Resolved"
        ],
        "ats_priority_keywords": [
            "GAAP", "IFRS", "CPA", "General Ledger (GL)", "Month-End Close",
            "SOX 404", "Internal Controls", "Tax Compliance", "NetSuite", "Audit"
        ],
    },
    "enterprise_sales": {
        "id": "enterprise_sales",
        "name": "Enterprise Sales & Business Development",
        "profession": "SALES_BIZDEV",
        "description": "Tailored for Account Executives, Enterprise Sales Leaders, and BDR Managers. Focuses on quota attainment, revenue closed, pipeline generation, and territory growth.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Sales Executive Profile",
            "work_experience": "Sales Performance & Account History",
            "technical_skills": "Sales Methodologies & CRM Stack",
            "education": "Education",
            "certifications": "Sales Certifications",
        },
        "color_palette": {
            "primary": "#0f172a",
            "accent": "#15803d",     # Green 700 (Money / Revenue)
            "divider": "#22c55e",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Every single bullet should report quota achievement percentage (e.g. 142% of FY24 quota, $2.4M ARR).",
            "Specify average contract value (ACV), sales cycle length, and outbound pipeline created.",
            "List sales methodologies (MEDDPICC, Challenger, Command of the Message, Sandler).",
        ],
        "power_verbs": [
            "Exceeded", "Closed", "Prospector", "Negotiated", "Expanded",
            "Surpassed", "Generated", "Accelerated", "Secured", "Transformed"
        ],
        "ats_priority_keywords": [
            "Quota Attainment", "ARR / MRR", "Enterprise Sales", "MEDDPICC", "Salesforce",
            "Pipeline Generation", "Account Management", "Contract Negotiation", "SaaS", "Outbound"
        ],
    },
    "marketing_growth": {
        "id": "marketing_growth",
        "name": "Marketing & Demand Generation",
        "profession": "MARKETING_GROWTH",
        "description": "Built for Growth Marketers, CMOs, and Brand Directors. Emphasizes customer acquisition cost (CAC), LTV, paid campaign ROI, inbound traffic, and conversion funnels.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "projects", "education"
        ],
        "section_titles": {
            "summary": "Marketing Leadership Summary",
            "work_experience": "Campaign & Growth Experience",
            "technical_skills": "MarTech Stack & Acquisition Channels",
            "projects": "Notable Campaigns & Brand Launches",
            "education": "Education",
        },
        "color_palette": {
            "primary": "#18181b",
            "accent": "#c026d3",     # Fuchsia 600
            "divider": "#e879f9",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Quantify customer acquisition cost (CAC) reduction, ROAS, and conversion rate lift.",
            "Highlight multi-channel growth strategies: SEO, SEM, Paid Social, Content, Product-Led.",
            "List MarTech platforms (HubSpot, Marketo, Google Ads, GA4, Braze).",
        ],
        "power_verbs": [
            "Scaled", "Acquired", "Campaign-engineered", "Optimized", "Attributed",
            "Targeted", "Authored", "Accelerated", "Positioned", "Launched"
        ],
        "ats_priority_keywords": [
            "CAC / LTV", "Demand Generation", "SEO / SEM", "HubSpot", "Google Analytics (GA4)",
            "Content Strategy", "Performance Marketing", "Conversion Rate Optimization (CRO)", "Email Funnels"
        ],
    },
    "healthcare_nursing": {
        "id": "healthcare_nursing",
        "name": "Nursing & Clinical Healthcare Specialist",
        "profession": "HEALTHCARE_MEDICAL",
        "description": "Formulated for Registered Nurses (RN), Nurse Practitioners, and Allied Health staff. Emphasizes patient safety, clinical licensure, specialized care units, and triage protocols.",
        "recommended_sections_order": [
            "contact", "summary", "certifications", "work_experience", "technical_skills", "education"
        ],
        "section_titles": {
            "summary": "Clinical Profile",
            "certifications": "Licenses & Clinical Certifications (RN, BLS, ACLS)",
            "work_experience": "Clinical & Hospital Experience",
            "technical_skills": "Clinical Competencies & EHR Systems",
            "education": "Nursing Education & Degrees",
        },
        "color_palette": {
            "primary": "#0c4a6e",    # Sky 900
            "accent": "#0284c7",     # Sky 600
            "divider": "#38bdf8",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "State active state RN/NP nursing license number and compact state privileges prominently.",
            "Detail specialized units (ICU, CCU, ER, Med-Surg, NICU, Telemetry) and patient-to-nurse ratios.",
            "List EHR / EMR platforms (Epic, Cerner, Meditech) and emergency life support credentials (BLS, ACLS, PALS).",
        ],
        "power_verbs": [
            "Administered", "Monitored", "Triaged", "Assessed", "Collaborated",
            "Educated", "Managed", "Stabilized", "Delivered", "Advocated"
        ],
        "ats_priority_keywords": [
            "Registered Nurse (RN)", "BLS / ACLS", "Patient Care", "Epic EHR", "ICU / ER",
            "Medication Administration", "Triage", "Care Planning", "Infection Control", "HIPAA"
        ],
    },
    "doctor_surgeon": {
        "id": "doctor_surgeon",
        "name": "Physician, Doctor & Surgeon Curriculum Vitae (CV)",
        "profession": "HEALTHCARE_MEDICAL",
        "description": "Comprehensive academic CV standard for Attending Physicians, Surgeons, and Medical Specialists. Prioritizes board certifications, residency/fellowship training, clinical appointments, and surgical procedures.",
        "recommended_sections_order": [
            "contact", "summary", "certifications", "education", "work_experience", "technical_skills", "projects"
        ],
        "section_titles": {
            "summary": "Medical Practice Overview",
            "certifications": "Medical Licensure & Board Certifications",
            "education": "Medical Education, Residency & Fellowships",
            "work_experience": "Clinical Appointments & Hospital Practice",
            "technical_skills": "Clinical Specializations & Procedures",
            "projects": "Research, Clinical Trials & Publications",
        },
        "color_palette": {
            "primary": "#0f172a",
            "accent": "#1e3a8a",     # Deep Navy Blue
            "divider": "#3b82f6",
            "font_family": "Times-Roman",
        },
        "content_guidelines": [
            "Prominently display Board Certification (e.g. American Board of Surgery) and active state medical licenses.",
            "List Medical School, Internship, Residency, and Fellowships in reverse chronological order with teaching institutions.",
            "Quantify operative volumes, procedural success rates, clinic patient caseloads, and peer-reviewed citations.",
        ],
        "power_verbs": [
            "Diagnosed", "Performed", "Operated", "Managed", "Consulted",
            "Published", "Investigated", "Mentored", "Pioneered", "Presented"
        ],
        "ats_priority_keywords": [
            "Board Certified", "Medical License", "Fellowship Trained", "Residency", "Clinical Trials",
            "Minimally Invasive Surgery", "Patient Outcomes", "Internal Medicine", "PubMed", "Epic"
        ],
    },
    "human_resources": {
        "id": "human_resources",
        "name": "Human Resources & People Leadership",
        "profession": "HUMAN_RESOURCES",
        "description": "Engineered for HR Business Partners, Talent Acquisition Leaders, and People Directors. Focuses on employee retention, compensation architecture, hiring velocity, and workplace culture.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "certifications"
        ],
        "section_titles": {
            "summary": "People Operations Summary",
            "work_experience": "HR & Talent Leadership Experience",
            "technical_skills": "HRIS Platforms & People Strategy",
            "education": "Education",
            "certifications": "Certifications (SHRM-CP, SPHR)",
        },
        "color_palette": {
            "primary": "#18181b",
            "accent": "#d97706",     # Warm Amber
            "divider": "#f59e0b",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Quantify retention rates, reduction in time-to-hire, and employee net promoter scores (eNPS).",
            "Highlight performance review cycles, DE&I frameworks, and leadership development programs.",
            "List HRIS platforms (Workday, BambooHR, ADP, Greenhouse, Culture Amp).",
        ],
        "power_verbs": [
            "Recruited", "Spearheaded", "Onboarded", "Retained", "Administered",
            "Championed", "Developed", "Navigated", "Mediated", "Fostered"
        ],
        "ats_priority_keywords": [
            "Talent Acquisition", "HRBP", "Performance Management", "Employee Relations",
            "Workday HRIS", "SHRM", "Compensation & Benefits", "Onboarding", "Retention"
        ],
    },
    "legal_compliance": {
        "id": "legal_compliance",
        "name": "Legal Counsel & Regulatory Compliance",
        "profession": "LEGAL_COMPLIANCE",
        "description": "Professional standard for Corporate Counsel, Compliance Officers, and Attorneys. Prioritizes bar admissions, commercial contract negotiation, regulatory defense, and risk mitigation.",
        "recommended_sections_order": [
            "contact", "summary", "certifications", "work_experience", "education", "technical_skills"
        ],
        "section_titles": {
            "summary": "Legal Executive Profile",
            "certifications": "Bar Admissions & Legal Credentials",
            "work_experience": "Legal & Corporate Counsel Experience",
            "education": "Juris Doctor (JD) & Academic Degrees",
            "technical_skills": "Specializations & Regulatory Domains",
        },
        "color_palette": {
            "primary": "#09090b",
            "accent": "#475569",     # Slate / Charcoal
            "divider": "#64748b",
            "font_family": "Times-Roman",
        },
        "content_guidelines": [
            "State active state bar admissions and federal court admissions immediately under header.",
            "Document value of commercial agreements negotiated, intellectual property filings, or regulatory filings.",
            "Specify domains: Corporate Governance, GDPR/Privacy, M&A, Labor Law, Anti-Trust, Export Controls.",
        ],
        "power_verbs": [
            "Drafted", "Negotiated", "Litigated", "Advised", "Mitigated",
            "Interpreted", "Structured", "Complied", "Defended", "Secured"
        ],
        "ats_priority_keywords": [
            "Bar Admission", "Juris Doctor (JD)", "Commercial Contracts", "Compliance",
            "Regulatory Affairs", "Corporate Governance", "GDPR", "Intellectual Property", "Risk Mitigation"
        ],
    },
    "operations_supply_chain": {
        "id": "operations_supply_chain",
        "name": "Operations, Logistics & Supply Chain",
        "profession": "OPERATIONS_LOGISTICS",
        "description": "Built for Operations Directors, Plant Managers, and Supply Chain Executives. Focuses on lean manufacturing, inventory turns, logistics cost reductions, and SLA performance.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "certifications"
        ],
        "section_titles": {
            "summary": "Operations Leadership Profile",
            "work_experience": "Operational & Supply Chain Experience",
            "technical_skills": "Operational Methodologies & ERP Systems",
            "education": "Education",
            "certifications": "Certifications (Six Sigma, APICS)",
        },
        "color_palette": {
            "primary": "#1c1917",
            "accent": "#ea580c",     # Orange 600
            "divider": "#f97316",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "Quantify fulfillment accuracy, cost savings, warehouse throughput, and OTIF (On-Time In-Full) delivery.",
            "Document Six Sigma Black Belt or Kaizen continuous improvement initiatives.",
            "List ERP / WMS software (SAP S/4HANA, Oracle WMS, Manhattan Associates).",
        ],
        "power_verbs": [
            "Streamlined", "Procured", "Dispatched", "Optimized", "Audited",
            "Negotiated", "Expanded", "Standardized", "Delivered", "Coordinated"
        ],
        "ats_priority_keywords": [
            "Supply Chain", "Logistics", "Inventory Management", "Six Sigma", "Lean Manufacturing",
            "SAP", "Procurement", "Warehouse Operations (WMS)", "Vendor Management", "OTIF"
        ],
    },
    "executive_leadership": {
        "id": "executive_leadership",
        "name": "Executive Leadership & General Management",
        "profession": "EXECUTIVE",
        "description": "High-impact format for C-Suite Executives (CEO, COO, CTO, CFO), Presidents, and Board Members. Prioritizes enterprise vision, EBITDA growth, organizational transformation, and market expansion.",
        "recommended_sections_order": [
            "contact", "summary", "work_experience", "technical_skills", "education", "projects"
        ],
        "section_titles": {
            "summary": "Executive Leadership Profile",
            "work_experience": "Executive & General Management Experience",
            "technical_skills": "Core Executive Competencies",
            "education": "Education & Advanced Degrees",
            "projects": "Board Appointments & Strategic Initiatives",
        },
        "color_palette": {
            "primary": "#09090b",
            "accent": "#3f3f46",
            "divider": "#71717a",
            "font_family": "Helvetica",
        },
        "content_guidelines": [
            "State P&L responsibility ($M or $B), headcount managed, and total shareholder return.",
            "Lead with strategic vision, global expansion, acquisitions, and restructuring outcomes.",
            "Emphasize board communication, investor relations, and enterprise culture transformation.",
        ],
        "power_verbs": [
            "Spearheaded", "Transformed", "Steered", "Orchestrated", "Negotiated",
            "Pioneered", "Restructured", "Expanded", "Championed", "Grew"
        ],
        "ats_priority_keywords": [
            "P&L Responsibility", "EBITDA Growth", "Enterprise Strategy", "Mergers & Acquisitions (M&A)",
            "Board Governance", "Organizational Transformation", "Global Expansion", "Executive Leadership"
        ],
    },
}

class ResumeTemplateIntelligenceService:
    """
    Intelligent role-specific template selector and resume restructuring engine.
    Applies professional recruitment conventions for 16+ global professions.
    """

    @classmethod
    def get_all_templates(cls) -> List[Dict[str, Any]]:
        """Returns the full catalog of role-specific templates."""
        return list(ROLE_TEMPLATE_REGISTRY.values())

    @classmethod
    def get_template(cls, template_id: str) -> Dict[str, Any]:
        """Returns a specific template definition by ID, falling back to software_engineering."""
        clean_id = template_id.lower().strip()
        if clean_id in ROLE_TEMPLATE_REGISTRY:
            return ROLE_TEMPLATE_REGISTRY[clean_id]
        # Match by alias / fallback
        for k, tmpl in ROLE_TEMPLATE_REGISTRY.items():
            if k in clean_id or clean_id in k:
                return tmpl
        return ROLE_TEMPLATE_REGISTRY["software_engineering"]

    @classmethod
    def detect_optimal_template_for_role(
        cls, role_title: str, profession: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically analyzes a target role title and profession taxonomy to select
        the authoritative recruitment structure for that occupation.
        """
        title_lower = (role_title or "").lower().strip()
        prof_upper = (profession or "").upper().strip()

        # 0. Early Career, Internships & Freshers
        if any(w in title_lower for w in ["intern", "internship", "co-op", "coop", "student"]) and not any(w in title_lower for w in ["internal", "international"]):
            return ROLE_TEMPLATE_REGISTRY["fresher_internship"]
        if any(w in title_lower for w in ["fresher", "graduate trainee", "graduate program", "trainee", "apprentice", "apprenticeship", "recent graduate", "new grad"]):
            return ROLE_TEMPLATE_REGISTRY["fresher_graduate"]

        # 1. Exact healthcare & surgical match
        if any(w in title_lower for w in ["surgeon", "physician", "doctor", "cardiologist", "oncologist", "pediatrician", "orthopedic", "anesthesiologist", "attending"]):
            return ROLE_TEMPLATE_REGISTRY["doctor_surgeon"]

        if any(w in title_lower for w in ["nurse", "registered nurse", "rn", "np", "clinical", "allied health", "physical therapist"]):
            return ROLE_TEMPLATE_REGISTRY["healthcare_nursing"]

        # 2. Executive C-suite
        if any(w in title_lower for w in ["chief executive", "ceo", "chief operating", "coo", "chief financial", "cfo", "chief technology", "cto", "president", "vice president", "managing director", "general manager"]):
            return ROLE_TEMPLATE_REGISTRY["executive_leadership"]

        # 3. AI & Data specializations
        if any(w in title_lower for w in ["ai engineer", "machine learning", "deep learning", "llm", "generative ai", "computer vision", "nlp engineer"]):
            return ROLE_TEMPLATE_REGISTRY["ai_ml_engineer"]

        if any(w in title_lower for w in ["data scientist", "research scientist", "statistician", "applied scientist"]):
            return ROLE_TEMPLATE_REGISTRY["data_scientist"]

        if any(w in title_lower for w in ["data analyst", "bi analyst", "business intelligence", "analytics engineer", "tableau"]):
            return ROLE_TEMPLATE_REGISTRY["data_analyst"]

        # 4. Product & Business Analysis
        if any(w in title_lower for w in ["product manager", "product owner", "group product", "head of product"]):
            return ROLE_TEMPLATE_REGISTRY["product_manager"]

        if any(w in title_lower for w in ["business analyst", "systems analyst", "strategy consultant", "process analyst"]):
            return ROLE_TEMPLATE_REGISTRY["business_analyst"]

        # 5. Finance & Accounting
        if any(w in title_lower for w in ["accountant", "cpa", "auditor", "audit senior", "controller", "bookkeeper"]):
            return ROLE_TEMPLATE_REGISTRY["accountant_audit"]

        if any(w in title_lower for w in ["investment bank", "financial analyst", "fp&a", "portfolio manager", "private equity", "wealth management"]):
            return ROLE_TEMPLATE_REGISTRY["banking_finance"]

        # 6. Sales & Marketing
        if any(w in title_lower for w in ["account executive", "sales manager", "business development", "bdr", "sdr", "sales director"]):
            return ROLE_TEMPLATE_REGISTRY["enterprise_sales"]

        if any(w in title_lower for w in ["marketing", "demand gen", "growth marketing", "content manager", "brand manager"]):
            return ROLE_TEMPLATE_REGISTRY["marketing_growth"]

        # 7. HR & Legal
        if any(w in title_lower for w in ["hr", "human resources", "talent acquisition", "recruiter", "people operations", "people partner"]):
            return ROLE_TEMPLATE_REGISTRY["human_resources"]

        if any(w in title_lower for w in ["counsel", "attorney", "lawyer", "legal", "compliance", "regulatory"]):
            return ROLE_TEMPLATE_REGISTRY["legal_compliance"]

        # 8. Operations
        if any(w in title_lower for w in ["supply chain", "logistics", "warehouse", "operations manager", "plant manager"]):
            return ROLE_TEMPLATE_REGISTRY["operations_supply_chain"]

        # 9. Fallback by profession taxonomy
        if prof_upper == "HEALTHCARE_MEDICAL":
            return ROLE_TEMPLATE_REGISTRY["doctor_surgeon"]
        elif prof_upper == "DATA_AI":
            return ROLE_TEMPLATE_REGISTRY["ai_ml_engineer"]
        elif prof_upper == "FINANCE_ACCOUNTING":
            return ROLE_TEMPLATE_REGISTRY["banking_finance"]
        elif prof_upper == "SALES_BIZDEV":
            return ROLE_TEMPLATE_REGISTRY["enterprise_sales"]
        elif prof_upper == "MARKETING_GROWTH":
            return ROLE_TEMPLATE_REGISTRY["marketing_growth"]
        elif prof_upper == "HUMAN_RESOURCES":
            return ROLE_TEMPLATE_REGISTRY["human_resources"]
        elif prof_upper == "LEGAL_COMPLIANCE":
            return ROLE_TEMPLATE_REGISTRY["legal_compliance"]
        elif prof_upper == "OPERATIONS_LOGISTICS":
            return ROLE_TEMPLATE_REGISTRY["operations_supply_chain"]

        return ROLE_TEMPLATE_REGISTRY["software_engineering"]

    @classmethod
    def reorder_resume_sections(
        cls, content: Dict[str, Any], template_id: str
    ) -> Dict[str, Any]:
        """
        Structures the candidate's resume sections and titles according to
        the target profession's authoritative ATS standards.
        """
        tmpl = cls.get_template(template_id)
        ordered_keys = tmpl.get("recommended_sections_order", [])
        section_titles = tmpl.get("section_titles", {})

        restructured = dict(content)
        restructured["applied_template_id"] = tmpl["id"]
        restructured["applied_template_name"] = tmpl["name"]
        restructured["section_ordering"] = ordered_keys
        restructured["custom_section_titles"] = section_titles

        return restructured


# Module-level convenience functions
get_all_templates = ResumeTemplateIntelligenceService.get_all_templates
get_template = ResumeTemplateIntelligenceService.get_template
detect_optimal_template_for_role = ResumeTemplateIntelligenceService.detect_optimal_template_for_role
reorder_resume_sections = ResumeTemplateIntelligenceService.reorder_resume_sections

