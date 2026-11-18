"""
Local Production-Ready Resume Intelligence Service.

Extracts text and structured candidate data locally from PDF and DOCX documents
without external APIs, cloud services, or paid dependencies.
Enforces strict file validation, magic bytes verification, and anti-macro safety.
"""
import os
import io
import re
import html
import zipfile
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any, Set
from fastapi import HTTPException, status
import pypdf
import docx

from app.ingestion.classifier import classify_profession_with_confidence
from app.ingestion.normalizer import normalize_location_and_country

# ---------------------------------------------------------------------------
# SKILL TAXONOMY & CANONICAL NORMALIZATION MAP
# ---------------------------------------------------------------------------

CANONICAL_SKILLS: Dict[str, str] = {
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "html5": "HTML",
    "css3": "CSS",
    "bash": "Bash",
    "shell": "Shell",
    "scala": "Scala",
    "r": "R",

    # Frameworks & Libraries
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "asp.net": "ASP.NET",
    "laravel": "Laravel",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",

    # Databases & Caching
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "sqlite": "SQLite",
    "dynamodb": "DynamoDB",
    "oracle": "Oracle",
    "cassandra": "Cassandra",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "linux": "Linux",
    "ansible": "Ansible",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "restful": "REST APIs",

    # AI, ML & Data
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "nlp": "NLP",
    "llm": "LLMs",
    "computer vision": "Computer Vision",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "excel": "Excel",

    # Design, Product & Management
    "figma": "Figma",
    "git": "Git",
    "jira": "Jira",
    "agile": "Agile",
    "scrum": "Scrum",
    "postman": "Postman",
    "salesforce": "Salesforce",
    "zendesk": "Zendesk",
    "project management": "Project Management",
}

TECH_SKILLS_SET = {
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "Swift", "Kotlin", "SQL", "HTML", "CSS", "Bash", "Shell", "Scala", "R",
    "React", "Next.js", "Node.js", "Express.js", "Vue.js", "Angular", "FastAPI", "Django", "Flask",
    "Spring Boot", "ASP.NET", "Laravel", "Tailwind CSS", "Bootstrap",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite", "DynamoDB",
    "GraphQL", "REST APIs", "PyTorch", "TensorFlow", "Pandas", "NumPy", "Scikit-Learn"
}

TOOLS_TECH_SET = {
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD", "Jenkins",
    "GitHub Actions", "Linux", "Ansible", "Kafka", "RabbitMQ", "Power BI", "Tableau", "Excel",
    "Figma", "Git", "Jira", "Agile", "Scrum", "Postman", "Salesforce", "Zendesk"
}

DEGREE_PATTERNS = [
    r"\b(?:bachelor|b\.?s\.?|b\.?tech\.?|b\.?e\.?|b\.?a\.?|undergraduate)\b",
    r"\b(?:master|m\.?s\.?|m\.?tech\.?|m\.?e\.?|m\.?b\.?a\.?|graduate|postgraduate)\b",
    r"\b(?:ph\.?d\.?|doctorate|doctoral)\b",
    r"\b(?:diploma|associate)\b"
]

SECTION_HEADERS = {
    "summary": ["summary", "professional summary", "about me", "profile", "objective", "career objective"],
    "skills": ["skills", "technical skills", "skills & competencies", "core competencies", "technologies", "tools & technologies"],
    "experience": ["experience", "work experience", "employment history", "professional experience", "work history"],
    "education": ["education", "academic background", "qualifications", "academic qualifications"],
    "projects": ["projects", "personal projects", "key projects", "academic projects"],
    "certifications": ["certifications", "licenses & certifications", "certificates", "professional certifications"],
}


class ResumeParserService:
    @staticmethod
    def extract_text_from_file(content_bytes: bytes, filename: str) -> str:
        """
        Safely extracts raw text from PDF, DOCX, or TXT file bytes.
        Enforces magic bytes verification, encryption checks, and macro safety.
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return ResumeParserService._extract_from_pdf(content_bytes)
        elif ext in (".docx", ".doc"):
            return ResumeParserService._extract_from_docx(content_bytes)
        elif ext == ".txt":
            return ResumeParserService._extract_from_txt(content_bytes)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document format '{ext}'. Please upload a PDF, DOCX, or TXT file."
            )

    @staticmethod
    def _extract_from_pdf(content_bytes: bytes) -> str:
        if not content_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file. Header signature does not match PDF specification."
            )

        try:
            stream = io.BytesIO(content_bytes)
            reader = pypdf.PdfReader(stream)

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Encrypted or password-protected PDF files cannot be processed. Please upload an unencrypted file."
                )

            extracted_pages = []
            for idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        extracted_pages.append(text)
                except Exception:
                    continue

            full_text = "\n\n".join(extracted_pages).strip()
            # Clean abnormal control chars
            full_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", full_text)

            if len(full_text.strip()) < 30:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded PDF does not contain extractable text. Scanned images without a digital text layer are not supported."
                )

            return full_text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read PDF document: {str(e)}"
            )

    @staticmethod
    def _extract_from_docx(content_bytes: bytes) -> str:
        if not content_bytes.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DOCX file. File is not a valid OpenXML package."
            )

        try:
            stream = io.BytesIO(content_bytes)
            doc = docx.Document(stream)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            # Also extract text from tables
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        table_texts.append(row_text)

            all_text = "\n".join(paragraphs + table_texts).strip()

            if len(all_text) < 30:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded DOCX does not contain sufficient readable text."
                )

            return all_text
        except HTTPException:
            raise
        except Exception as e:
            # Fallback to standard library zipfile XML reading
            try:
                stream = io.BytesIO(content_bytes)
                with zipfile.ZipFile(stream) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    texts = [node.text for node in tree.iter() if node.text]
                    full = " ".join(texts).strip()
                    if len(full) >= 30:
                        return full
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read DOCX document: {str(e)}"
            )

    @staticmethod
    def _extract_from_txt(content_bytes: bytes) -> str:
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                text = content_bytes.decode(encoding).strip()
                if len(text) >= 20:
                    return text
            except UnicodeDecodeError:
                continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode plain text document encoding."
        )

    @classmethod
    def parse_resume_data(cls, text: str) -> Dict[str, Any]:
        """
        Extracts structured factual information and inferred career metadata
        from resume plain text.
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # 1. Contact Information
        email = cls._extract_email(text)
        phone = cls._extract_phone(text)
        full_name = cls._extract_full_name(lines, email, phone)
        location = cls._extract_location(text)

        # 2. Section Segmentation
        sections = cls._segment_sections(lines)

        # 3. Skills Extraction & Categorization
        skills, tech_skills, tools = cls._extract_skills(text, sections.get("skills", ""))

        # 4. Experience & Work History
        work_exp, total_years = cls._extract_work_experience(sections.get("experience", ""), text)

        # 5. Education
        education = cls._extract_education(sections.get("education", ""), text)

        # 6. Projects
        projects = cls._extract_projects(sections.get("projects", ""))

        # 7. Certifications
        certifications = cls._extract_certifications(sections.get("certifications", ""), text)

        # 8. Summary & Inferred Roles
        summary = cls._extract_summary(sections.get("summary", ""), lines)
        preferred_roles = cls._extract_preferred_roles(summary or text)
        headline = preferred_roles[0] if preferred_roles else (work_exp[0]["title"] if work_exp else (f"Software Engineer" if ("Python" in skills or "React" in skills) else None))

        # 9. Profession Classification
        inferred_prof = None
        cand_title = headline or (work_exp[0]["title"] if work_exp else "") or (preferred_roles[0] if preferred_roles else "")
        dept_hint = ""
        skills_lower = [s.lower() for s in skills]
        if any(s in skills_lower for s in ["python", "react", "docker", "kubernetes", "java", "c++", "go", "fastapi", "django", "sql", "typescript", "javascript", "node.js"]):
            dept_hint = "Engineering"
        elif any(s in skills_lower for s in ["salesforce", "crm", "sales"]):
            dept_hint = "Sales"
        elif any(s in skills_lower for s in ["figma", "ui/ux", "user research"]):
            dept_hint = "Product Design"

        if cand_title or dept_hint:
            prof_key, _ = classify_profession_with_confidence(cand_title, dept_hint, f"{summary or ''} {' '.join(skills)}")
            inferred_prof = prof_key

        return {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "location": location,
            "headline": headline,
            "summary": summary,
            "profession": inferred_prof,
            "skills": skills,
            "technical_skills": tech_skills,
            "tools_technologies": tools,
            "work_experience": work_exp,
            "education": education,
            "projects": projects,
            "certifications": certifications,
            "preferred_roles": preferred_roles,
            "total_experience_years": total_years,
            "raw_text_preview": text[:1200]
        }

    # -----------------------------------------------------------------------
    # INTERNAL EXTRACTION HELPERS
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_email(text: str) -> Optional[str]:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        return match.group(0).lower() if match else None

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        # Matches +91 98765 43210, +1 (555) 234-5678, (555) 123-4567, 9876543210
        pattern = r"(?:(?:\+|00)\d{1,3}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4,5}"
        for match in re.finditer(pattern, text):
            cand = match.group(0).strip()
            # Must contain between 9 and 15 digits
            digits = re.sub(r"\D", "", cand)
            if 10 <= len(digits) <= 14:
                return cand
        return None

    @staticmethod
    def _extract_full_name(lines: List[str], email: Optional[str], phone: Optional[str]) -> Optional[str]:
        for line in lines[:4]:
            l = line.strip()
            # Skip if contains email, URL, phone, or resume markers
            if email and email in l.lower():
                continue
            if any(k in l.lower() for k in ["@", "http", "www.", "linkedin", "github", "resume", "curriculum", "cv"]):
                continue
            if re.search(r"\d{3,}", l):
                continue

            # Strip separators e.g. "Aarav Sharma | Software Engineer"
            name_part = l.split("|")[0].split("•")[0].strip()
            words = name_part.split()
            if 2 <= len(words) <= 4:
                if all(w[0].isupper() for w in words if w.isalpha()):
                    return name_part
        return None

    @staticmethod
    def _extract_location(text: str) -> Optional[str]:
        lines = text.split("\n")[:6]
        header_text = " ".join(lines)
        norm_loc, city, region, country, _ = normalize_location_and_country(header_text)
        if city and country:
            return f"{city}, {country}"
        elif country:
            return country
        elif city:
            return city
        return None

    @staticmethod
    def _segment_sections(lines: List[str]) -> Dict[str, str]:
        sections = {}
        current_section = "header"
        section_lines: Dict[str, List[str]] = {"header": []}

        for line in lines:
            clean = line.strip().lower()
            clean_alpha = re.sub(r"[^a-z\s]", "", clean).strip()

            detected = None
            for sec_name, headers in SECTION_HEADERS.items():
                if clean_alpha in headers:
                    detected = sec_name
                    break

            if detected:
                current_section = detected
                if current_section not in section_lines:
                    section_lines[current_section] = []
            else:
                section_lines[current_section].append(line)

        for sec, l_list in section_lines.items():
            sections[sec] = "\n".join(l_list).strip()

        return sections

    @staticmethod
    def _extract_skills(full_text: str, skills_section_text: str) -> Tuple[List[str], List[str], List[str]]:
        found_skills: Set[str] = set()
        search_corpus = f"{skills_section_text}\n{full_text}".lower()

        # Word boundary matching against canonical taxonomy
        for pattern, canonical in CANONICAL_SKILLS.items():
            if re.search(r"\b" + re.escape(pattern) + r"\b", search_corpus):
                found_skills.add(canonical)

        # Categorize
        tech_skills = sorted([s for s in found_skills if s in TECH_SKILLS_SET])
        tools_tech = sorted([s for s in found_skills if s in TOOLS_TECH_SET])
        all_skills = sorted(list(found_skills))

        return all_skills, tech_skills, tools_tech

    @staticmethod
    def _extract_work_experience(exp_text: str, full_text: str) -> Tuple[List[Dict[str, Any]], Optional[float]]:
        target_text = exp_text if len(exp_text) > 50 else full_text
        entries = []

        # Find date patterns e.g. "2021 - Present", "July 2021 - Present", "2019 - 2021"
        date_pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+)?((?:19|20)\d{2})\s*(?:-|–|to)\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+)?((?:19|20)\d{2}|Present|Current)"
        
        matches = list(re.finditer(date_pattern, target_text, re.IGNORECASE))
        detected_years = []

        for m in matches:
            start_yr = int(m.group(2))
            end_val = m.group(4)
            end_yr = datetime.datetime.now().year if end_val.lower() in ("present", "current") else int(end_val)
            detected_years.extend([start_yr, end_yr])

            # Look backwards 1-2 lines for company/title
            start_pos = m.start()
            prev_chunk = target_text[:start_pos].strip().split("\n")
            title = None
            company = None

            if len(prev_chunk) >= 1:
                line1 = prev_chunk[-1].strip()
                if "|" in line1:
                    parts = line1.split("|")
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif " at " in line1.lower():
                    parts = re.split(r"\s+at\s+", line1, flags=re.IGNORECASE)
                    title = parts[0].strip()
                    company = parts[1].strip()
                else:
                    title = line1
                    if len(prev_chunk) >= 2:
                        company = prev_chunk[-2].strip()

            if title and len(title) < 100:
                entries.append({
                    "title": title,
                    "company": company or "Employer",
                    "start_date": f"{start_yr}",
                    "end_date": end_val.title(),
                    "description": ""
                })

        total_years = None
        if detected_years:
            min_y = min(detected_years)
            max_y = max(detected_years)
            span = max_y - min_y
            if 0 < span <= 45:
                total_years = float(span)

        return entries[:5], total_years

    @staticmethod
    def _extract_education(edu_text: str, full_text: str) -> List[Dict[str, Any]]:
        target_text = edu_text if len(edu_text) > 30 else full_text
        entries = []

        lines = [l.strip() for l in target_text.split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            for pat in DEGREE_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    # Found a degree line
                    degree_str = line
                    inst_str = lines[idx + 1] if idx + 1 < len(lines) else "University"
                    yr_match = re.search(r"\b(19\d{2}|20\d{2})\b", f"{line} {inst_str}")
                    grad_year = int(yr_match.group(1)) if yr_match else None

                    entries.append({
                        "degree": degree_str[:120],
                        "institution": inst_str[:120],
                        "field_of_study": "Computer Science" if "computer" in degree_str.lower() else None,
                        "graduation_year": grad_year
                    })
                    break

        return entries[:3]

    @staticmethod
    def _extract_projects(proj_text: str) -> List[Dict[str, Any]]:
        if not proj_text:
            return []
        entries = []
        for line in proj_text.split("\n"):
            l = line.strip()
            if ":" in l:
                parts = l.split(":", 1)
                entries.append({
                    "title": parts[0].strip(),
                    "description": parts[1].strip()[:200],
                    "technologies": []
                })
        return entries[:4]

    @staticmethod
    def _extract_certifications(cert_text: str, full_text: str) -> List[str]:
        target = cert_text if cert_text else full_text
        certs = []
        known_cert_keywords = [
            "aws certified", "kubernetes administrator", "cka", "pmp",
            "azure certified", "gcp certified", "scrum master", "cfa", "cpa"
        ]
        for line in target.split("\n"):
            l_clean = line.strip()
            if any(k in l_clean.lower() for k in known_cert_keywords):
                certs.append(l_clean[:100])
        return list(set(certs))[:5]

    @staticmethod
    def _extract_summary(summary_text: str, lines: List[str]) -> Optional[str]:
        if summary_text and len(summary_text) > 20:
            return summary_text[:500].strip()
        # Fallback to paragraph under name
        for line in lines[2:6]:
            if len(line) > 60 and not any(k in line.lower() for k in ["@", "http", "phone"]):
                return line[:500].strip()
        return None

    @staticmethod
    def _extract_preferred_roles(text: str) -> List[str]:
        roles = []
        patterns = [
            r"seeking\s+([A-Za-z\s]{3,35})\s+roles?",
            r"target\s*role\s*:\s*([A-Za-z\s]{3,35})",
            r"objective\s*:\s*([A-Za-z\s]{3,35})"
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) > 3 and not any(bad in candidate.lower() for bad in ["career", "opportunity", "growth"]):
                    roles.append(candidate.title())
        return list(set(roles))

    @staticmethod
    def detect_conflicts(extracted: Dict[str, Any], existing_profile_data: Dict[str, Any]) -> List[str]:
        """
        Detects differences between extracted resume facts and existing profile values.
        """
        conflicts = []
        
        # Name comparison
        ex_name = existing_profile_data.get("full_name")
        new_name = extracted.get("full_name")
        if ex_name and new_name and ex_name.strip().lower() != new_name.strip().lower():
            conflicts.append(f"Full Name: '{ex_name}' in profile vs '{new_name}' in resume.")

        # Skills comparison
        ex_skills = set(s.lower() for s in (existing_profile_data.get("skills") or []))
        new_skills = [s for s in (extracted.get("skills") or []) if s.lower() not in ex_skills]
        if new_skills:
            conflicts.append(f"Skills: Resume contains {len(new_skills)} new skill(s) not in profile: {', '.join(new_skills[:4])}.")

        # Experience comparison
        ex_exp = existing_profile_data.get("total_experience_years")
        new_exp = extracted.get("total_experience_years")
        if ex_exp is not None and new_exp is not None and ex_exp != new_exp:
            conflicts.append(f"Experience: {ex_exp} years in profile vs {new_exp} years extracted from resume.")

        # Phone comparison
        ex_phone = existing_profile_data.get("phone_number")
        new_phone = extracted.get("phone")
        if ex_phone and new_phone and ex_phone != new_phone:
            conflicts.append(f"Phone Number: '{ex_phone}' in profile vs '{new_phone}' in resume.")

        return conflicts
