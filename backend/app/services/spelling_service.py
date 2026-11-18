"""
Intelligent Spelling Correction, Synonym Expansion, and Query Understanding.

Provides typo correction (e.g. "costumer suppot" -> "customer support"),
domain-aware synonym expansion, and related canonical role suggestions
without external paid APIs or latency penalties.
"""
import re
from typing import Dict, List, Optional, Tuple, Set, Any
from app.ingestion.taxonomy import TAXONOMY_FAMILIES

# Common typos mapped directly for microsecond resolution
COMMON_TYPOS: Dict[str, str] = {
    "costumer": "customer",
    "suppot": "support",
    "suport": "support",
    "supprt": "support",
    "softwere": "software",
    "softwaer": "software",
    "enginer": "engineer",
    "engeneer": "engineer",
    "enginier": "engineer",
    "acountent": "accountant",
    "acountant": "accountant",
    "accoutant": "accountant",
    "recruter": "recruiter",
    "recrutier": "recruiter",
    "docter": "doctor",
    "nurs": "nurse",
    "nurce": "nurse",
    "analist": "analyst",
    "anlyst": "analyst",
    "managr": "manager",
    "manger": "manager",
    "finace": "finance",
    "finnace": "finance",
    "markting": "marketing",
    "markiting": "marketing",
    "desiner": "designer",
    "desgner": "designer",
    "devops": "devops",
    "pyton": "python",
    "javascrip": "javascript",
    "postgre": "postgresql",
    "curiculum": "curriculum",
    "logistcs": "logistics",
    "technitian": "technician",
    "hosptal": "hospital",
    "surgen": "surgeon",
    "sergeon": "surgeon",
    "surgon": "surgeon",
}

# Domain synonym & alias maps
ROLE_SYNONYMS: Dict[str, List[str]] = {
    "coder": ["software engineer", "developer"],
    "programmer": ["software engineer", "developer"],
    "dev": ["developer", "software engineer"],
    "sre": ["site reliability engineer", "devops"],
    "devops": ["site reliability engineer", "infrastructure engineer"],
    "web developer": ["software engineer", "frontend developer", "full stack developer", "developer"],
    "python developer": ["python engineer", "backend engineer", "software engineer"],
    "ai engineer": ["machine learning engineer", "applied ai engineer", "generative ai engineer", "llm engineer", "ai research engineer"],
    "data analyst": ["analytics engineer", "business intelligence analyst", "data scientist"],
    "surgeon": ["general surgeon", "senior surgeon", "surgical specialist", "physician", "doctor"],
    "doctor": ["physician", "medical specialist", "surgeon"],
    "rn": ["registered nurse", "nurse"],
    "cpa": ["accountant", "certified public accountant"],
    "bdr": ["business development representative", "sales representative"],
    "sdr": ["sales development representative", "account executive"],
    "ae": ["account executive"],
    "pm": ["product manager"],
    "ux": ["product designer", "ui designer"],
    "ui": ["product designer", "ui designer"],
    "hr": ["human resources", "talent acquisition"],
    "recruiter": ["talent acquisition", "sourcer"],
    "helpdesk": ["customer support", "technical support"],
    "tech support": ["technical support", "customer support"],
    "qa": ["quality assurance", "test engineer"],
    "trainee": ["graduate trainee", "apprentice", "intern", "management trainee", "working student"],
    "graduate trainee": ["management trainee", "graduate program", "trainee program", "junior trainee"],
    "apprenticeship": ["apprentice", "ausbildung", "intern", "trainee"],
    "marketing associate": ["marketing specialist", "growth marketing", "digital marketing", "marketing coordinator"],
    "nurse": ["registered nurse", "clinical nurse", "nurse practitioner"],
}

# Master vocabulary for fuzzy distance comparison
VOCABULARY: Set[str] = set(COMMON_TYPOS.values())
for k, syns in ROLE_SYNONYMS.items():
    for word in re.findall(r"\w+", k.lower()):
        if len(word) > 2:
            VOCABULARY.add(word)
    for s in syns:
        for word in re.findall(r"\w+", s.lower()):
            if len(word) > 2:
                VOCABULARY.add(word)

for fam in TAXONOMY_FAMILIES.values():
    for role in fam["canonical_roles"]:
        for word in re.findall(r"\w+", role.lower()):
            if len(word) > 2:
                VOCABULARY.add(word)
    for skill in fam["core_skills"]:
        for word in re.findall(r"\w+", skill.lower()):
            if len(word) > 2:
                VOCABULARY.add(word)
    for syn in fam["synonyms"]:
        for word in re.findall(r"\w+", syn.lower()):
            if len(word) > 2:
                VOCABULARY.add(word)

def _damerau_levenshtein(s1: str, s2: str) -> int:
    """Calculates edit distance between two words."""
    d = {}
    len1 = len(s1)
    len2 = len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,        # deletion
                d[(i, j - 1)] + 1,        # insertion
                d[(i - 1, j - 1)] + cost  # substitution
            )
            if i and j and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost) # transposition

    return d[(len1 - 1, len2 - 1)]

class SpellingService:
    @classmethod
    def correct_and_expand_query(cls, query: str) -> Dict[str, Any]:
        """
        Analyzes search query, corrects typos, suggests synonyms,
        identifies matching career track, and recommends related canonical roles.
        """
        if not query or not query.strip():
            return {
                "original_query": "",
                "corrected_query": "",
                "is_corrected": False,
                "suggested_roles": [],
                "detected_profession": None,
                "synonyms": []
            }

        cleaned = query.strip()
        words = re.findall(r"\w+", cleaned.lower())
        corrected_words = []
        has_typo = False

        for w in words:
            # 1. Exact lookup in known typos
            if w in COMMON_TYPOS:
                corrected_words.append(COMMON_TYPOS[w])
                has_typo = True
                continue

            # 2. Check if already valid in vocabulary
            if w in VOCABULARY or len(w) <= 3:
                corrected_words.append(w)
                continue

            # 3. Fuzzy match against vocabulary if distance <= 2
            best_match = None
            best_dist = 3  # threshold
            for cand in VOCABULARY:
                if abs(len(cand) - len(w)) > 2:
                    continue
                dist = _damerau_levenshtein(w, cand)
                if dist < best_dist:
                    best_dist = dist
                    best_match = cand

            if best_match and best_dist <= 2:
                corrected_words.append(best_match)
                has_typo = True
            else:
                corrected_words.append(w)

        corrected_query = " ".join(corrected_words) if has_typo else cleaned

        # Identify synonyms
        synonyms = []
        low_q = corrected_query.lower()
        for k, syn_list in ROLE_SYNONYMS.items():
            if k == low_q or re.search(rf"\b{k}\b", low_q):
                synonyms.extend(syn_list)

        # Detect matching profession family using authoritative taxonomy classifier
        from app.ingestion.classifier import classify_profession_with_confidence
        detected_profession, confidence = classify_profession_with_confidence(low_q)
        suggested_roles = []
        if confidence >= 0.80 and detected_profession in TAXONOMY_FAMILIES:
            suggested_roles = TAXONOMY_FAMILIES[detected_profession]["canonical_roles"][:5]
        else:
            detected_profession = None
            for fam_key, fam in TAXONOMY_FAMILIES.items():
                for syn in fam["synonyms"]:
                    if re.search(r"\b" + re.escape(syn.lower()) + r"\b", low_q):
                        detected_profession = fam_key
                        suggested_roles = fam["canonical_roles"][:5]
                        break
                if detected_profession:
                    break

        return {
            "original_query": cleaned,
            "corrected_query": corrected_query,
            "is_corrected": has_typo,
            "suggested_roles": suggested_roles,
            "detected_profession": detected_profession,
            "synonyms": list(set(synonyms))
        }

    @classmethod
    def parse_search_intent(cls, query: str) -> Dict[str, Any]:
        """
        Parses complex natural language search expressions (e.g., 'Senior Remote React Engineer in Germany >$120k')
        into structured intent components:
        - clean_keyword: 'React Engineer'
        - work_arrangement: 'REMOTE'
        - experience_level: 'SENIOR'
        - employment_type: None or 'CONTRACT', etc.
        - extracted_location: 'Germany'
        - min_salary: 120000
        """
        if not query or not query.strip():
            return {
                "clean_keyword": "",
                "work_arrangement": None,
                "experience_level": None,
                "employment_type": None,
                "extracted_location": None,
                "min_salary": None,
            }

        text = query.strip()
        extracted_location = None
        work_arrangement = None
        experience_level = None
        employment_type = None
        min_salary = None
        is_early_career = False
        early_career_category = None

        # 0. Early Career & Fresher Intent Detection
        if re.search(r"\b(?:zero\s*experience|no\s*experience|fresher|freshers)\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "TRUE_FRESHER"
            experience_level = "ENTRY"
            text = re.sub(r"\b(?:zero\s*experience|no\s*experience|fresher|freshers)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:graduate\s*trainee|management\s*trainee|trainee)\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "TRAINEE"
            experience_level = "ENTRY"
            text = re.sub(r"\b(?:graduate\s*trainee|management\s*trainee|trainee)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:fresh\s*graduate|recent\s*graduate|graduate\s*program|new\s*grad|graduate)\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "GRADUATE"
            experience_level = "ENTRY"
            text = re.sub(r"\b(?:fresh\s*graduate|recent\s*graduate|graduate\s*program|new\s*grad|graduate)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:apprenticeship|apprentice)\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "APPRENTICESHIP"
            employment_type = "APPRENTICESHIP"
            text = re.sub(r"\b(?:apprenticeship|apprentice)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:paid\s*internship|internship|intern)\b", text, re.IGNORECASE) and not re.search(r"\binternist\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "INTERNSHIP"
            employment_type = "INTERNSHIP"
            experience_level = "ENTRY"
            text = re.sub(r"\b(?:paid\s*internship|internship|intern)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:entry\s*level|entry-level|junior|jr)\b", text, re.IGNORECASE):
            is_early_career = True
            early_career_category = "ENTRY_LEVEL"
            experience_level = "ENTRY"
            text = re.sub(r"\b(?:entry\s*level|entry-level|junior|jr)\b", " ", text, flags=re.IGNORECASE)

        # 1. Salary Extraction (e.g. >$120k, >100000, $150k+, 80k)
        sal_match = re.search(r"(?:>|>=)?\s*[\$€£]?\s*(\d+)(k|\+)?\b", text, re.IGNORECASE)
        if sal_match and (">" in text or any(sym in text for sym in ["$", "€", "£"]) or "k" in sal_match.group(0).lower()):
            try:
                base = float(sal_match.group(1))
                suffix = sal_match.group(2) or ""
                if "k" in suffix.lower() or base < 1000:
                    min_salary = base * 1000.0
                else:
                    min_salary = base
                text = text[:sal_match.start()] + " " + text[sal_match.end():]
            except (ValueError, IndexError):
                pass

        # 2. Location Extraction via preposition "in / at / near <Location>" or matching known countries/cities
        from app.ingestion.normalizer import COUNTRY_ALIASES, CITY_SEARCH_ALIASES
        text_for_loc = text.strip()
        loc_prep_match = re.search(r"\b(?:in|at|near)\s+([A-Za-z\s]+)$", text_for_loc, flags=re.IGNORECASE)
        if loc_prep_match:
            candidate_loc = loc_prep_match.group(1).strip()
            c_low = candidate_loc.lower()
            if c_low in COUNTRY_ALIASES or c_low in CITY_SEARCH_ALIASES or any(c_low == k.lower() for k in COUNTRY_ALIASES.values()):
                extracted_location = candidate_loc
                text = text_for_loc[:loc_prep_match.start()].strip()
            elif len(candidate_loc.split()) <= 3:
                extracted_location = candidate_loc
                text = text_for_loc[:loc_prep_match.start()].strip()

        # 3. Work Arrangement Extraction
        if re.search(r"\b(?:remote|work\s+from\s+home|wfh|telecommute)\b", text, re.IGNORECASE):
            work_arrangement = "REMOTE"
            text = re.sub(r"\b(?:remote|work\s+from\s+home|wfh|telecommute)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:hybrid)\b", text, re.IGNORECASE):
            work_arrangement = "HYBRID"
            text = re.sub(r"\b(?:hybrid)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:onsite|on-site|in-office)\b", text, re.IGNORECASE):
            work_arrangement = "ONSITE"
            text = re.sub(r"\b(?:onsite|on-site|in-office)\b", " ", text, flags=re.IGNORECASE)

        # 4. Employment Type Extraction
        if re.search(r"\b(?:contract|contractor|freelance|freelancer)\b", text, re.IGNORECASE):
            employment_type = "CONTRACT"
            text = re.sub(r"\b(?:contract|contractor|freelance|freelancer)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:part-time|part\s+time)\b", text, re.IGNORECASE):
            employment_type = "PART_TIME"
            text = re.sub(r"\b(?:part-time|part\s+time)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:full-time|full\s+time)\b", text, re.IGNORECASE):
            employment_type = "FULL_TIME"
            text = re.sub(r"\b(?:full-time|full\s+time)\b", " ", text, flags=re.IGNORECASE)
        elif re.search(r"\b(?:internship|intern)\b", text, re.IGNORECASE) and not re.search(r"\binternist\b", text, re.IGNORECASE):
            employment_type = "INTERNSHIP"
            experience_level = "INTERN"
            text = re.sub(r"\b(?:internship|intern)\b", " ", text, flags=re.IGNORECASE)

        # 5. Seniority / Experience Level Extraction
        if not experience_level:
            if re.search(r"\b(?:senior|sr|staff)\b", text, re.IGNORECASE):
                experience_level = "SENIOR"
                text = re.sub(r"\b(?:senior|sr|staff)\b", " ", text, flags=re.IGNORECASE)
            elif re.search(r"\b(?:lead|principal|head\s+of)\b", text, re.IGNORECASE):
                experience_level = "LEAD"
                text = re.sub(r"\b(?:lead|principal|head\s+of)\b", " ", text, flags=re.IGNORECASE)
            elif re.search(r"\b(?:junior|jr|entry\s+level|associate)\b", text, re.IGNORECASE):
                experience_level = "ENTRY"
                text = re.sub(r"\b(?:junior|jr|entry\s+level|associate)\b", " ", text, flags=re.IGNORECASE)
            elif re.search(r"\b(?:executive|director|vp|vice\s+president|c-level)\b", text, re.IGNORECASE):
                experience_level = "EXECUTIVE"
                text = re.sub(r"\b(?:executive|director|vp|vice\s+president|c-level)\b", " ", text, flags=re.IGNORECASE)

        # Clean remaining whitespace and stray punctuation
        clean_keyword = re.sub(r"[^\w\s\.\+#/]", " ", text)
        clean_keyword = re.sub(r"\s+", " ", clean_keyword).strip()

        if not clean_keyword and early_career_category:
            if early_career_category == "TRAINEE":
                clean_keyword = "Trainee"
            elif early_career_category == "APPRENTICESHIP":
                clean_keyword = "Apprentice"
            elif early_career_category == "INTERNSHIP":
                clean_keyword = "Intern"

        return {
            "clean_keyword": clean_keyword,
            "work_arrangement": work_arrangement,
            "experience_level": experience_level,
            "employment_type": employment_type,
            "extracted_location": extracted_location,
            "min_salary": min_salary,
            "is_early_career": is_early_career,
            "early_career_category": early_career_category,
        }

