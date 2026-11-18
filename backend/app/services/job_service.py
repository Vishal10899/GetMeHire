import math
import time
import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, asc, func, case
from fastapi import HTTPException, status
from app.models import Job, Company, Source, SavedJob, User, Profile
from app.schemas.job import (
    JobDetailResponse,
    JobListResponseItem,
    JobSearchResponse,
    SimilarJobResponse,
    CompanySummary,
    ProfessionItem,
    ProfessionListResponse,
    CompanyItem,
    CompanyListResponse,
)
from app.ingestion.taxonomy import TAXONOMY_FAMILIES, LEGACY_ALIAS_MAP
from app.ingestion.normalizer import (
    CITY_SEARCH_ALIASES,
    COUNTRY_ALIASES,
    COUNTRY_TO_ISO_CODE,
    get_country_code,
    CANADIAN_PROVINCES,
    AUSTRALIAN_STATES,
)
from app.services.spelling_service import SpellingService
from app.services.matching_service import MatchingService

def _sanitize_logo_url(url: Optional[str]) -> Optional[str]:
    """Ensure stock photos seeded by mistake are never returned as company logos."""
    if not url:
        return None
    if "images.unsplash.com" in url or "placeholder" in url or "stock-photo" in url:
        return None
    return url


COMPANY_ALIASES: Dict[str, str] = {
    # Priority Indian IT Companies
    "tcs": "Tata Consultancy Services",
    "tata consultancy": "Tata Consultancy Services",
    "tata consultancy services": "Tata Consultancy Services",
    "hcl": "HCLTech",
    "hcl tech": "HCLTech",
    "hcltech": "HCLTech",
    "hcl technologies": "HCLTech",
    "wipro": "Wipro",
    "wipro limited": "Wipro",
    "wipro technologies": "Wipro",
    "infosys": "Infosys",
    "infosys limited": "Infosys",
    "tech mahindra": "Tech Mahindra",
    "techmahindra": "Tech Mahindra",
    "ltimindtree": "LTIMindtree",
    "lti mindtree": "LTIMindtree",
    "l&t infotech": "LTIMindtree",
    "mindtree": "LTIMindtree",
    "persistent": "Persistent Systems",
    "persistent systems": "Persistent Systems",
    "coforge": "Coforge",
    "mphasis": "Mphasis",
    "hexaware": "Hexaware",
    "kpit": "KPIT Technologies",
    "kpit technologies": "KPIT Technologies",
    "birlasoft": "Birlasoft",
    "ofss": "Oracle Financial Services Software",
    "oracle financial services": "Oracle Financial Services Software",
    # Global MNCs Hiring in India
    "google": "Google",
    "google india": "Google",
    "alphabet": "Google",
    "microsoft": "Microsoft",
    "microsoft india": "Microsoft",
    "amazon": "Amazon",
    "amazon india": "Amazon",
    "aws": "Amazon",
    "apple": "Apple",
    "meta": "Meta",
    "facebook": "Meta",
    "nvidia": "Nvidia",
    "adobe": "Adobe",
    "salesforce": "Salesforce",
    "ibm": "IBM",
    "cisco": "Cisco",
    "intel": "Intel",
    "qualcomm": "Qualcomm",
    "dell": "Dell Technologies",
    "dell technologies": "Dell Technologies",
    "hp": "HP",
    "sap": "SAP",
    "oracle": "Oracle",
    "servicenow": "ServiceNow",
    "uber": "Uber",
    "airbnb": "Airbnb",
    "linkedin": "LinkedIn",
    # BFSI, Banking and Financial Services
    "amex": "American Express",
    "american express": "American Express",
    "moody's": "Moody's",
    "moodys": "Moody's",
    "jpmorgan": "JPMorgan Chase",
    "jp morgan": "JPMorgan Chase",
    "jpmorgan chase": "JPMorgan Chase",
    "goldman": "Goldman Sachs",
    "goldman sachs": "Goldman Sachs",
    "morgan stanley": "Morgan Stanley",
    "barclays": "Barclays",
    "hsbc": "HSBC",
    "citi": "Citi",
    "citigroup": "Citi",
    "wells fargo": "Wells Fargo",
    "deutsche bank": "Deutsche Bank",
    "standard chartered": "Standard Chartered",
    "mastercard": "Mastercard",
    "visa": "Visa",
    "paypal": "PayPal",
    "fis": "FIS",
    "fidelity": "Fidelity Investments",
    "fidelity investments": "Fidelity Investments",
    "blackrock": "BlackRock",
    "s&p global": "S&P Global",
    "s&p": "S&P Global",
    # Consulting and Professional Services
    "accenture": "Accenture",
    "deloitte": "Deloitte",
    "ey": "EY",
    "ernst & young": "EY",
    "pwc": "PwC",
    "kpmg": "KPMG",
    "capgemini": "Capgemini",
    "cognizant": "Cognizant",
    "genpact": "Genpact",
    "mckinsey": "McKinsey",
    "bcg": "BCG",
    "bain": "Bain & Company",
    "bain & company": "Bain & Company",
    # Indian Startups and High-Growth Tech
    "flipkart": "Flipkart",
    "phonepe": "PhonePe",
    "razorpay": "Razorpay",
    "razorpay software": "Razorpay",
    "cred": "CRED",
    "groww": "Groww",
    "zerodha": "Zerodha",
    "meesho": "Meesho",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "zepto": "Zepto",
    "blinkit": "Blinkit",
    "freshworks": "Freshworks",
    "zoho": "Zoho",
    "postman": "Postman",
    "browserstack": "BrowserStack",
    "dream11": "Dream11",
    "pine labs": "Pine Labs",
    "pinelabs": "Pine Labs",
    "juspay": "Juspay",
    "chargebee": "Chargebee",
    "ofbusiness": "OfBusiness",
    "inmobi": "InMobi",
    "inmobi technologies": "InMobi",
    "ola": "Ola",
    "ather": "Ather Energy",
    "ather energy": "Ather Energy",
    "navi": "Navi",
    "makemytrip": "MakeMyTrip",
    "paytm": "Paytm",
    "thoughtworks": "Thoughtworks",
    "rubrik": "Rubrik",
    # Other verified tech platforms
    "scale": "Scale AI",
    "scaleai": "Scale AI",
    "scale ai, inc.": "Scale AI",
    "mozilla corporation": "Mozilla",
    "mozilla foundation": "Mozilla",
    "canonical ltd": "Canonical",
    "canonical group": "Canonical",
    "canonical uk": "Canonical",
    "stripe inc": "Stripe",
    "stripe, inc.": "Stripe",
    "stripe payments": "Stripe",
    "datadog inc": "Datadog",
    "datadog, inc.": "Datadog",
    "anthropic pbc": "Anthropic",
    "airbnb inc": "Airbnb",
    "airbnb, inc.": "Airbnb",
    "bunq b.v.": "Bunq",
    "linear orbit": "Linear",
    "linear app": "Linear",
    "channable b.v.": "Channable",
    "sweetgreen inc": "Sweetgreen",
    "sweetgreen, inc.": "Sweetgreen",
    "coursera inc": "Coursera",
    "sarvamai": "Sarvam AI",
    "cern laboratory": "CERN",
    "palantir technologies": "Palantir",
    "ramp business": "Ramp",
    "everphone gmbh": "Everphone",
    "on running": "On Running",
    "on-running": "On Running",
    "duolingo inc": "Duolingo",
    "toast tab": "Toast",
    "toast inc": "Toast",
    "monzo bank": "Monzo",
    "komodo health inc": "Komodo Health",
}

COUNTRY_CITIES_MAP: Dict[str, List[str]] = {
    "india": [
        "India", "Bengaluru", "Bangalore", "Mumbai", "Bombay", "Navi Mumbai",
        "Delhi", "New Delhi", "Gurugram", "Gurgaon", "Noida", "Greater Noida",
        "Hyderabad", "Secunderabad", "Pune", "Chennai", "Madras", "Kolkata",
        "Calcutta", "Ahmedabad", "Kochi", "Cochin", "Coimbatore", "Chandigarh",
        "Mohali", "Jaipur", "Indore", "Thiruvananthapuram", "Trivandrum"
    ],
    "canada": [
        "Canada", "Toronto", "Vancouver", "Montreal", "Ottawa", "Waterloo",
        "Calgary", "Edmonton", "Quebec City", "Halifax", "Victoria", "Winnipeg"
    ],
    "germany": [
        "Germany", "Berlin", "Munich", "Frankfurt", "Hamburg", "Cologne",
        "Köln", "Stuttgart", "Dusseldorf", "Düsseldorf", "Leipzig", "Dortmund", "Essen"
    ],
    "united kingdom": [
        "United Kingdom", "London", "Manchester", "Edinburgh", "Bristol",
        "Birmingham", "Leeds", "Glasgow", "Oxford", "Cambridge"
    ],
    "australia": [
        "Australia", "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
        "Canberra", "Hobart"
    ],
    "united states": [
        "United States", "New York", "San Francisco", "Seattle", "Los Angeles",
        "Chicago", "Boston", "Austin", "Denver", "Atlanta", "Dallas", "Houston"
    ],
    "ireland": ["Ireland", "Dublin", "Cork", "Galway"],
    "singapore": ["Singapore"],
    "japan": ["Japan", "Tokyo", "Osaka", "Kyoto"],
    "france": ["France", "Paris", "Lyon", "Marseille"],
    "netherlands": ["Netherlands", "Amsterdam", "Rotterdam", "Utrecht"],
}


class JobService:
    @staticmethod
    def search_jobs(
        db: Session,
        current_user: Optional[User] = None,
        keyword: Optional[str] = None,
        company: Optional[str] = None,
        company_id: Optional[int] = None,
        profession: Optional[str] = None,
        category: Optional[str] = None,
        location: Optional[str] = None,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
        city: Optional[str] = None,
        remote_type: Optional[str] = None,  # REMOTE, HYBRID, ONSITE
        work_arrangement: Optional[str] = None,  # ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED
        remote_eligibility: Optional[str] = None,  # WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED
        employment_type: Optional[str] = None,  # FULL_TIME, PART_TIME, CONTRACT, FREELANCE, INTERNSHIP, etc.
        experience_level: Optional[str] = None,  # ENTRY, MID, SENIOR, LEAD, EXECUTIVE
        experience_range: Optional[str] = None,  # internship, entry, 0-1, 1-3, 3-5, 5-8, 8+, unspecified
        early_career_category: Optional[str] = None,  # TRUE_FRESHER, GRADUATE, ENTRY_LEVEL, EARLY_CAREER, JUNIOR, TRAINEE, INTERNSHIP, APPRENTICESHIP, etc.
        is_fresher_friendly: Optional[bool] = None,
        max_experience_years: Optional[float] = None,
        graduation_year: Optional[int] = None,
        skills: Optional[List[str]] = None,
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None,
        currency: Optional[str] = None,
        date_posted: Optional[str] = None,  # 24h, 3d, 7d, 30d
        status_filter: Optional[str] = "ACTIVE",
        sort_by: str = "newest",  # newest, relevant, oldest, company, salary_high
        page: int = 1,
        page_size: int = 20,
        include_demo: bool = False,
    ) -> JobSearchResponse:
        start_time = time.time()
        # Bounded pagination safety
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        did_you_mean = None
        is_corrected = False
        suggested_roles = []
        detected_profession = None
        intent_clean_role = None

        if keyword and keyword.strip():
            raw_keyword = keyword.strip()
            # 1. Parse natural language search intent (e.g. "React Engineer in Germany")
            search_intent = SpellingService.parse_search_intent(raw_keyword)
            if not location and search_intent["extracted_location"]:
                location = search_intent["extracted_location"]
            if min_salary is None and search_intent["min_salary"]:
                min_salary = search_intent["min_salary"]
            intent_ec_cat = search_intent.get("early_career_category")
            if is_fresher_friendly is None and search_intent.get("is_early_career"):
                is_fresher_friendly = True
            if not employment_type and search_intent.get("employment_type"):
                employment_type = search_intent["employment_type"]

            intent_clean_role = search_intent["clean_keyword"]
            analysis_target = intent_clean_role if (intent_clean_role and len(intent_clean_role) >= 2) else raw_keyword

            analysis = SpellingService.correct_and_expand_query(analysis_target)
            if analysis["is_corrected"]:
                did_you_mean = analysis["corrected_query"]
                is_corrected = True
            suggested_roles = analysis["suggested_roles"]
            detected_profession = analysis["detected_profession"]

        query = db.query(Job)
        has_company_joined = False

        # Exclude synthetic/seed demo listings from candidate-facing discovery
        if not include_demo:
            query = query.filter(
                or_(
                    Job.raw_source_data.is_(None),
                    Job.raw_source_data['seed'].astext.is_(None),
                    Job.raw_source_data['seed'].astext != 'true'
                )
            )

        # Status filter
        if status_filter:
            if status_filter == "ACTIVE":
                query = query.filter(Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]))
            else:
                query = query.filter(Job.status == status_filter)

        # Keyword filter on title, department, description & company (with typo tolerance & synonym expansion)
        clean_kw = None
        if keyword and keyword.strip():
            clean_kw = keyword.strip()
            terms_to_match = [clean_kw]
            if intent_clean_role and intent_clean_role != clean_kw and len(intent_clean_role) >= 2:
                terms_to_match.append(intent_clean_role)
            if did_you_mean and did_you_mean not in terms_to_match:
                terms_to_match.append(did_you_mean)

            # Check verified company aliases
            alias_target = COMPANY_ALIASES.get(clean_kw.lower())
            if alias_target and alias_target not in terms_to_match:
                terms_to_match.append(alias_target)

            # Synonyms from spelling service
            analysis_synonyms = analysis.get("synonyms", []) if 'analysis' in locals() else []
            for syn in analysis_synonyms:
                if syn not in terms_to_match:
                    terms_to_match.append(syn)

            if not has_company_joined:
                query = query.join(Job.company)
                has_company_joined = True

            keyword_conditions = []
            for term in terms_to_match:
                term_clean = term.strip()
                if not term_clean:
                    continue
                if len(term_clean) <= 3:
                    # Enforce exact word boundary matching for short acronyms/terms (e.g. 'rn', 'ai', 'qa', 'pm')
                    # to prevent 'rn' matching 'Intern' or 'Learning'
                    keyword_conditions.extend([
                        func.lower(Job.title).op("~")(rf"\y{re.escape(term_clean.lower())}\y"),
                        func.lower(Job.normalized_title).op("~")(rf"\y{re.escape(term_clean.lower())}\y"),
                        func.lower(Job.department).op("~")(rf"\y{re.escape(term_clean.lower())}\y"),
                    ])
                else:
                    pat = f"%{term_clean}%"
                    keyword_conditions.extend([
                        Job.title.ilike(pat),
                        Job.normalized_title.ilike(pat),
                        Job.department.ilike(pat),
                        Company.canonical_name.ilike(pat),
                    ])

            # Domain-aware description search:
            # Constrained to the relevant profession so generic terms don't cause false cross-profession matches
            ts_conditions = []
            for term in terms_to_match[:2]:
                term_clean = term.strip()
                if len(term_clean) > 2:
                    ts_cond = Job.search_vector.op("@@")(func.plainto_tsquery("english", term_clean))
                    if detected_profession:
                        ts_conditions.append(and_(ts_cond, Job.profession == detected_profession))
                    else:
                        ts_conditions.append(ts_cond)

            query = query.filter(or_(*keyword_conditions, *ts_conditions))

            # PRIORITY 1 & 2: Hard Profession Exclusion
            # When a specific profession is requested (e.g. Nurse -> HEALTHCARE_MEDICAL, AI -> DATA_AI),
            # strictly exclude any job categorized under an unrelated explicit profession (e.g. PRODUCT_DESIGN).
            if detected_profession:
                query = query.filter(
                    or_(
                        Job.profession == detected_profession,
                        Job.profession.is_(None),
                        Job.profession == "GENERAL"
                    )
                )

        # Company filter with canonical name & alias resolution
        if company_id is not None:
            query = query.filter(Job.company_id == company_id)
        elif company and company.strip():
            raw_c = company.strip()
            norm_c = COMPANY_ALIASES.get(raw_c.lower(), raw_c)
            if not has_company_joined:
                query = query.join(Job.company)
                has_company_joined = True
            query = query.filter(
                or_(
                    Company.canonical_name.ilike(f"%{raw_c}%"),
                    Company.canonical_name.ilike(f"%{norm_c}%")
                )
            )

        # Category / Industry filter
        if category and category.strip():
            cat_clean = category.strip().lower()
            matched_professions = []
            for fk, fdata in TAXONOMY_FAMILIES.items():
                if (
                    fk.lower() == cat_clean
                    or fdata.get("category", "").lower() == cat_clean
                    or cat_clean in fdata.get("category", "").lower()
                    or cat_clean in fdata.get("label", "").lower()
                ):
                    matched_professions.append(fk)
                    matched_professions.extend(fdata.get("legacy_aliases", []))
            if matched_professions:
                query = query.filter(Job.profession.in_(list(set(matched_professions))))
            else:
                query = query.filter(
                    or_(
                        Job.profession.ilike(f"%{category.strip()}%"),
                        Job.department.ilike(f"%{category.strip()}%")
                    )
                )

        # Profession filter (supporting canonical keys and legacy aliases)
        if profession and profession.strip():
            p_clean = profession.strip().upper()
            match_professions = [p_clean]
            if p_clean in TAXONOMY_FAMILIES:
                match_professions.extend(TAXONOMY_FAMILIES[p_clean].get("legacy_aliases", []))
            for fk, fdata in TAXONOMY_FAMILIES.items():
                if p_clean in fdata.get("legacy_aliases", []):
                    match_professions.append(fk)
            query = query.filter(Job.profession.in_(list(set(match_professions))))

        # Location filter with universal country, city, and regional normalization
        if location and location.strip():
            raw_loc = location.strip()
            loc_lower = raw_loc.lower()

            canon_country = COUNTRY_ALIASES.get(loc_lower)
            if canon_country:
                iso = COUNTRY_TO_ISO_CODE.get(canon_country)
                country_cities = COUNTRY_CITIES_MAP.get(loc_lower, [canon_country])
                conds = [
                    Job.country.ilike(f"%{canon_country}%"),
                    Job.location.ilike(f"%{canon_country}%"),
                ]
                if iso:
                    conds.append(Job.country_code == iso)
                for ccity in country_cities:
                    conds.extend([
                        Job.city.ilike(f"%{ccity}%"),
                        Job.location.ilike(f"%{ccity}%")
                    ])
                query = query.filter(or_(*conds))
            else:
                # Specific city or regional search
                aliases = [raw_loc]
                if loc_lower in CITY_SEARCH_ALIASES:
                    aliases.extend([a.title() for a in CITY_SEARCH_ALIASES[loc_lower]])
                loc_conds = []
                for alias in set(aliases):
                    pat = f"%{alias}%"
                    loc_conds.extend([
                        Job.location.ilike(pat),
                        Job.city.ilike(pat),
                        Job.region.ilike(pat),
                    ])
                query = query.filter(or_(*loc_conds))

        if country and country.strip():
            c_clean = country.strip()
            canon_c = COUNTRY_ALIASES.get(c_clean.lower(), c_clean)
            iso = COUNTRY_TO_ISO_CODE.get(canon_c)
            country_cities = COUNTRY_CITIES_MAP.get(c_clean.lower(), [canon_c])
            c_conds = [
                Job.country.ilike(f"%{canon_c}%"),
            ]
            if iso:
                c_conds.append(Job.country_code == iso)
            for ccity in country_cities:
                c_conds.append(
                    and_(
                        or_(Job.country.is_(None), Job.country == ""),
                        or_(Job.city.ilike(f"%{ccity}%"), Job.location.ilike(f"%{ccity}%"))
                    )
                )
            query = query.filter(or_(*c_conds))

        if country_code and country_code.strip():
            query = query.filter(Job.country_code.ilike(country_code.strip()))

        if city and city.strip():
            raw_city = city.strip()
            city_lower = raw_city.lower()
            city_matches = [raw_city]
            if city_lower in CITY_SEARCH_ALIASES:
                city_matches.extend([a.title() for a in CITY_SEARCH_ALIASES[city_lower]])
            city_conds = [Job.city.ilike(f"%{cm}%") for cm in set(city_matches)]
            query = query.filter(or_(*city_conds))

        # Work arrangement & remote filter
        if remote_type and remote_type.strip():
            rt = remote_type.strip().upper()
            if rt in ("REMOTE", "WFH"):
                query = query.filter(Job.remote_type == "REMOTE")
            elif rt in ("HYBRID",):
                query = query.filter(Job.remote_type == "HYBRID")
            elif rt in ("ONSITE", "ON-SITE", "WFO"):
                query = query.filter(Job.remote_type == "ONSITE")
            else:
                query = query.filter(Job.remote_type == rt)

        if work_arrangement and work_arrangement.strip():
            wa = work_arrangement.strip().upper()
            if wa in ("REMOTE", "WFH"):
                query = query.filter(
                    or_(
                        Job.work_arrangement.in_(["REMOTE", "FLEXIBLE"]),
                        Job.remote_type == "REMOTE"
                    )
                )
            elif wa in ("HYBRID",):
                query = query.filter(
                    or_(
                        Job.work_arrangement == "HYBRID",
                        Job.remote_type == "HYBRID"
                    )
                )
            elif wa in ("ONSITE", "ON-SITE", "WFO"):
                query = query.filter(
                    or_(
                        Job.work_arrangement.in_(["ONSITE", "FIELD_BASED"]),
                        Job.remote_type == "ONSITE"
                    )
                )
            elif wa in ("FIELD_BASED", "FIELD"):
                query = query.filter(Job.work_arrangement == "FIELD_BASED")
            elif wa in ("FLEXIBLE",):
                query = query.filter(Job.work_arrangement == "FLEXIBLE")
            else:
                query = query.filter(
                    or_(Job.work_arrangement == wa, Job.remote_type == wa)
                )

        if remote_eligibility and remote_eligibility.strip():
            rel = remote_eligibility.strip().upper()
            query = query.filter(Job.remote_eligibility == rel)

        # Employment type filter (supporting all PRD types)
        if employment_type and employment_type.strip():
            ef = employment_type.strip().upper()
            if ef in ("CONTRACT", "CONTRACTOR", "FREELANCE"):
                query = query.filter(
                    or_(
                        Job.employment_type.in_(["CONTRACT", "FREELANCE", "FIXED_TERM"]),
                        Job.title.ilike("%contract%"),
                        Job.title.ilike("%freelance%")
                    )
                )
            elif ef in ("INTERN", "INTERNSHIP", "CO-OP", "COOP"):
                query = query.filter(
                    or_(
                        Job.employment_type == "INTERNSHIP",
                        Job.title.ilike("%internship%"),
                        Job.title.ilike("% intern"),
                        Job.title.ilike("% intern %"),
                        Job.title.ilike("intern %"),
                        Job.title.ilike("%co-op%"),
                        Job.title.ilike("%coop%")
                    )
                )
            elif ef in ("PART_TIME", "PART-TIME", "PART TIME"):
                query = query.filter(
                    or_(
                        Job.employment_type.in_(["PART_TIME", "CASUAL", "SHIFT_BASED"]),
                        Job.title.ilike("%part-time%"),
                        Job.title.ilike("%part time%")
                    )
                )
            elif ef in ("FULL_TIME", "FULL-TIME", "FULL TIME"):
                query = query.filter(Job.employment_type.in_(["FULL_TIME", "PERMANENT"]))
            elif ef in ("FIXED_TERM", "FIXED-TERM", "FTC"):
                query = query.filter(
                    or_(
                        Job.employment_type == "FIXED_TERM",
                        Job.title.ilike("%ftc%"),
                        Job.title.ilike("%fixed-term%")
                    )
                )
            else:
                query = query.filter(Job.employment_type == ef)

        # Experience level
        if experience_level and experience_level.strip():
            query = query.filter(Job.experience_level == experience_level.strip().upper())

        # Experience range (internship, entry, 0-1, 1-3, 3-5, 5-8, 8+, unspecified)
        if experience_range and experience_range.strip():
            er = experience_range.strip().lower()
            if er == "internship":
                query = query.filter(
                    or_(
                        Job.employment_type == "INTERNSHIP",
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years == 0),
                        Job.title.ilike("%internship%"),
                        Job.title.ilike("% intern"),
                        Job.title.ilike("% intern %"),
                        Job.title.ilike("intern %")
                    )
                )
            elif er == "entry":
                query = query.filter(
                    or_(
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years >= 0, Job.min_experience_years <= 2),
                        and_(Job.min_experience_years.is_(None), Job.experience_level == "ENTRY")
                    )
                )
            elif er == "0-1":
                query = query.filter(
                    or_(
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years >= 0, Job.min_experience_years <= 1),
                        and_(Job.min_experience_years.is_(None), Job.experience_level == "ENTRY", Job.employment_type != "INTERNSHIP")
                    )
                )
            elif er == "1-3":
                query = query.filter(
                    and_(Job.min_experience_years.isnot(None), Job.min_experience_years > 1, Job.min_experience_years <= 3)
                )
            elif er == "3-5":
                query = query.filter(
                    or_(
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years > 3, Job.min_experience_years <= 5),
                        and_(Job.min_experience_years.is_(None), Job.experience_level == "MID")
                    )
                )
            elif er == "5-8":
                query = query.filter(
                    or_(
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years > 5, Job.min_experience_years <= 8),
                        and_(Job.min_experience_years.is_(None), Job.experience_level == "SENIOR")
                    )
                )
            elif er in ("8+", "8-plus", "8plus"):
                query = query.filter(
                    or_(
                        and_(Job.min_experience_years.isnot(None), Job.min_experience_years > 8),
                        and_(Job.min_experience_years.is_(None), Job.experience_level.in_(["LEAD", "EXECUTIVE"]))
                    )
                )
            elif er in ("unspecified", "not_specified", "none"):
                query = query.filter(
                    and_(
                        Job.min_experience_years.is_(None),
                        Job.experience_level.is_(None),
                        Job.employment_type != "INTERNSHIP"
                    )
                )

        # Early Career & Fresher Filters
        if early_career_category and early_career_category.strip():
            ecc = early_career_category.strip().upper()
            if ecc == "TRUE_FRESHER":
                query = query.filter(
                    or_(
                        Job.early_career_category == "TRUE_FRESHER",
                        and_(
                            Job.early_career_category.in_(["GRADUATE", "ENTRY_LEVEL", "EARLY_CAREER", "EXPERIENCE_FLEXIBLE"]),
                            or_(Job.min_experience_years == 0, Job.min_experience_years.is_(None))
                        )
                    ),
                    Job.early_career_category != "MISLABELLED_ENTRY_LEVEL"
                )
            else:
                query = query.filter(Job.early_career_category == ecc)

        if is_fresher_friendly is True:
            query = query.filter(
                Job.early_career_category.in_([
                    "TRUE_FRESHER", "GRADUATE", "ENTRY_LEVEL", "EARLY_CAREER",
                    "JUNIOR", "TRAINEE", "INTERNSHIP", "APPRENTICESHIP", "EXPERIENCE_FLEXIBLE"
                ]),
                Job.early_career_category != "MISLABELLED_ENTRY_LEVEL"
            )
        elif is_fresher_friendly is False:
            query = query.filter(Job.early_career_category.in_(["EXPERIENCED", "MISLABELLED_ENTRY_LEVEL"]))

        if max_experience_years is not None:
            query = query.filter(
                or_(
                    and_(Job.min_experience_years.isnot(None), Job.min_experience_years <= max_experience_years),
                    and_(
                        Job.min_experience_years.is_(None),
                        Job.early_career_category.in_(["TRUE_FRESHER", "GRADUATE", "INTERNSHIP", "TRAINEE", "APPRENTICESHIP", "ENTRY_LEVEL", "EARLY_CAREER", "EXPERIENCE_FLEXIBLE"])
                    )
                ),
                Job.early_career_category != "MISLABELLED_ENTRY_LEVEL"
            )

        if graduation_year is not None:
            query = query.filter(
                or_(
                    Job.early_career_metadata["eligible_graduation_years"].contains([graduation_year]),
                    Job.description.ilike(f"%{graduation_year}%")
                )
            )

        # Date posted filter (24h, 3d, 7d, 30d)
        if date_posted and date_posted.strip():
            dp = date_posted.strip().lower()
            days = None
            if dp in ("24h", "1d", "1"):
                days = 1
            elif dp in ("3d", "3"):
                days = 3
            elif dp in ("7d", "7"):
                days = 7
            elif dp in ("30d", "30"):
                days = 30
            if days:
                cutoff_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
                query = query.filter(func.coalesce(Job.posting_date, Job.first_seen_at) >= cutoff_dt)

        # Skills overlap
        if skills and len(skills) > 0:
            # Match if any requested skill is in job skills
            skill_filters = [Job.skills.contains([s.strip()]) for s in skills if s.strip()]
            if skill_filters:
                query = query.filter(or_(*skill_filters))

        # Salary filter (preserving null semantics - do not treat missing as 0)
        if min_salary is not None:
            query = query.filter(
                and_(
                    Job.salary_max.isnot(None),
                    Job.salary_max >= min_salary
                )
            )
        if max_salary is not None:
            query = query.filter(
                and_(
                    Job.salary_min.isnot(None),
                    Job.salary_min <= max_salary
                )
            )
        if currency and currency.strip():
            query = query.filter(Job.salary_currency == currency.strip().upper())

        # Total count
        total = query.count()

        # Deterministic sorting
        if sort_by == "oldest":
            query = query.order_by(Job.posting_date.asc().nullslast(), Job.id.asc())
        elif sort_by in ("salary_high", "salary"):
            query = query.order_by(Job.salary_max.desc().nullslast(), Job.salary_min.desc().nullslast(), Job.id.desc())
        elif sort_by == "company":
            query = query.join(Job.company).order_by(Company.canonical_name.asc(), Job.posting_date.desc().nullslast(), Job.id.desc())
        elif sort_by in ("relevant", "relevance") or clean_kw:
            rank_cases = []
            if is_fresher_friendly or early_career_category:
                # Rank true freshers, graduates, entry level, and undergraduate/general internships at the top (before PhD-specific)
                rank_cases.append((and_(Job.early_career_category == "TRUE_FRESHER", func.coalesce(Job.early_career_metadata['is_phd_required'].astext, 'false') == 'false'), 0))
                rank_cases.append((and_(Job.early_career_category == "GRADUATE", func.coalesce(Job.early_career_metadata['is_phd_required'].astext, 'false') == 'false'), 1))
                rank_cases.append((and_(Job.early_career_category == "ENTRY_LEVEL", func.coalesce(Job.early_career_metadata['is_phd_required'].astext, 'false') == 'false'), 2))
                rank_cases.append((and_(Job.early_career_category.in_(["INTERNSHIP", "TRAINEE", "APPRENTICESHIP"]), func.coalesce(Job.early_career_metadata['is_phd_required'].astext, 'false') == 'false'), 3))
                rank_cases.append((Job.early_career_category == "EARLY_CAREER", 4))
                rank_cases.append((Job.early_career_category == "EXPERIENCE_FLEXIBLE", 5))
            if clean_kw:
                target_terms = [clean_kw]
                if intent_clean_role and intent_clean_role != clean_kw:
                    target_terms.insert(0, intent_clean_role)
                if did_you_mean and did_you_mean not in target_terms:
                    target_terms.insert(0, did_you_mean)
                for t in target_terms:
                    # 1. Exact title match
                    rank_cases.append((func.lower(Job.title) == t.lower(), 6))
                    # 2. Substring in title or normalized title
                    rank_cases.append((or_(Job.title.ilike(f"%{t}%"), Job.normalized_title.ilike(f"%{t}%")), 7))
                # 3. Synonyms in title
                for syn in analysis_synonyms:
                    rank_cases.append((or_(Job.title.ilike(f"%{syn}%"), Job.normalized_title.ilike(f"%{syn}%")), 8))
            if detected_profession:
                rank_cases.append((Job.profession == detected_profession, 9))
            if rank_cases:
                query = query.order_by(
                    case(*rank_cases, else_=10).asc(),
                    Job.posting_date.desc().nullslast(),
                    Job.created_at.desc(),
                    Job.id.desc()
                )
            else:
                query = query.order_by(Job.posting_date.desc().nullslast(), Job.created_at.desc(), Job.id.desc())
        else:  # "newest" or "recent" default
            query = query.order_by(Job.posting_date.desc().nullslast(), Job.created_at.desc(), Job.id.desc())

        # Pagination slice
        offset = (page - 1) * page_size
        jobs = query.options(joinedload(Job.company), joinedload(Job.source)).offset(offset).limit(page_size).all()

        # Fetch saved job IDs and user profile for current user if authenticated
        saved_job_ids = set()
        user_profile = None
        if current_user:
            user_saved = db.query(SavedJob.job_id).filter(SavedJob.user_id == current_user.id).all()
            saved_job_ids = {s[0] for s in user_saved}
            user_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

        items = []
        for job in jobs:
            match_score = None
            match_reasons = []
            match_breakdown_dict = None
            if user_profile:
                breakdown = MatchingService.calculate_match(user_profile, job)
                if breakdown.has_sufficient_data and breakdown.total_score > 0 and (breakdown.matched_skills or breakdown.role_score > 0 or breakdown.skill_score > 0):
                    match_score = breakdown.total_score
                    match_reasons = breakdown.reasons
                    match_breakdown_dict = breakdown.model_dump()

            # PRIORITY 2: Two-Dimensional Scoring for Profession Relevance and Early-Career Suitability
            j_title_lower = (job.title or "").lower()
            j_meta = job.early_career_metadata or {}
            target_kw = (intent_clean_role or clean_kw or "").lower()
            syn_list = analysis_synonyms if 'analysis_synonyms' in locals() else []

            # 1. Profession Relevance Score (0-100)
            if target_kw and target_kw in j_title_lower:
                prof_score = 100.0
                prof_note = f"Direct occupational role match ('{target_kw}')."
            elif detected_profession and job.profession == detected_profession:
                prof_score = 85.0
                prof_note = f"Verified under target profession '{detected_profession}'."
            elif any(s.lower() in j_title_lower for s in syn_list if len(s) > 2):
                prof_score = 80.0
                prof_note = "Matches recognized occupational role synonym."
            elif not detected_profession:
                prof_score = 70.0
                prof_note = "General career vacancy."
            else:
                prof_score = 30.0
                prof_note = "Secondary profession match."

            # 2. Early-Career Suitability Score (0-100)
            ec_cat = job.early_career_category or "UNCERTAIN"
            is_phd = j_meta.get("is_phd_required", False)
            if ec_cat == "TRUE_FRESHER":
                ec_score = 100.0
                ec_note = "True Fresher eligible (0 mandatory years experience)."
            elif ec_cat == "GRADUATE":
                ec_score = 95.0
                batches = j_meta.get("eligible_graduation_years", [])
                batch_str = f" for {batches} batch" if batches else ""
                ec_note = f"Structured university graduate entry program{batch_str}."
            elif ec_cat == "ENTRY_LEVEL":
                ec_score = 90.0
                ec_note = "Verified Entry-Level opportunity (0-1 years experience)."
            elif ec_cat in ("INTERNSHIP", "APPRENTICESHIP", "TRAINEE"):
                if is_phd:
                    ec_score = 45.0
                    ec_note = "Doctoral Ph.D. research internship position."
                else:
                    ec_score = 85.0
                    ec_note = "Dedicated student, trainee, or internship placement."
            elif ec_cat == "EARLY_CAREER":
                ec_score = 75.0
                ec_note = "Early career role (1-2 years experience)."
            elif ec_cat == "EXPERIENCE_FLEXIBLE":
                ec_score = 70.0
                ec_note = "Experience flexible; capstone and personal projects accepted."
            elif ec_cat == "UNCERTAIN":
                ec_score = 40.0
                ec_note = "Experience threshold unstated in employer posting."
            else:
                ec_score = 0.0
                ec_note = "Experienced role."

            item_rec_reasons = [prof_note, ec_note]

            item = JobListResponseItem(
                id=job.id,
                title=job.title,
                normalized_title=job.normalized_title or job.title,
                department=job.department,
                profession=job.profession,
                classification_confidence=job.classification_confidence or 1.0,
                system_summary=job.system_summary,
                location=job.location,
                city=job.city,
                region=job.region,
                country=job.country,
                country_code=job.country_code,
                remote_type=job.remote_type,
                work_arrangement=getattr(job, "work_arrangement", None) or job.remote_type or "ONSITE",
                remote_eligibility=getattr(job, "remote_eligibility", None) or "UNSPECIFIED",
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                min_experience_years=job.min_experience_years,
                early_career_category=job.early_career_category,
                early_career_metadata=job.early_career_metadata,
                profession_score=prof_score,
                early_career_score=ec_score,
                recommendation_reasons=item_rec_reasons,
                skills=job.skills or [],
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_period=job.salary_period,
                posting_date=job.posting_date,
                status=job.status,
                application_url=job.application_url,
                company_id=job.company_id,
                company_name=job.company.canonical_name,
                company_logo=_sanitize_logo_url(job.company.logo_url),
                source_name=job.source.source_name,
                first_seen_at=job.first_seen_at,
                last_verified_at=job.last_verified_at,
                is_saved=(job.id in saved_job_ids),
                is_demo=bool((job.raw_source_data and isinstance(job.raw_source_data, dict) and job.raw_source_data.get("seed") is True) or job.id <= 7),
                match_score=match_score,
                match_reasons=match_reasons,
                match_breakdown=match_breakdown_dict
            )
            items.append(item)

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        latency_ms = round((time.time() - start_time) * 1000, 2)

        return JobSearchResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            did_you_mean=did_you_mean,
            is_corrected=is_corrected,
            suggested_roles=suggested_roles,
            detected_profession=detected_profession,
            query_latency_ms=latency_ms
        )

    @staticmethod
    def get_job_by_id(db: Session, job_id: int, current_user: Optional[User] = None) -> JobDetailResponse:
        job = db.query(Job).options(
            joinedload(Job.company),
            joinedload(Job.source)
        ).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found")

        is_saved = False
        if current_user:
            is_saved = db.query(SavedJob).filter(
                SavedJob.user_id == current_user.id,
                SavedJob.job_id == job.id
            ).first() is not None

        from app.services.job_activity_service import JobActivityService
        link_status, is_safe = JobActivityService.determine_link_status(job)

        return JobDetailResponse(
            id=job.id,
            company_id=job.company_id,
            source_id=job.source_id,
            external_job_id=job.external_job_id,
            title=job.title,
            normalized_title=job.normalized_title or job.title,
            description=job.description,
            system_summary=job.system_summary,
            department=job.department,
            profession=job.profession,
            classification_confidence=job.classification_confidence or 1.0,
            location=job.location,
            city=job.city,
            region=job.region,
            country=job.country,
            country_code=job.country_code,
            remote_type=job.remote_type,
            work_arrangement=getattr(job, "work_arrangement", None) or job.remote_type or "ONSITE",
            remote_eligibility=getattr(job, "remote_eligibility", None) or "UNSPECIFIED",
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            min_experience_years=job.min_experience_years,
            early_career_category=job.early_career_category,
            early_career_metadata=job.early_career_metadata,
            skills=job.skills or [],
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            posting_date=job.posting_date,
            status=job.status,
            application_url=job.application_url,
            source_name=job.source.source_name,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            last_verified_at=job.last_verified_at,
            company=CompanySummary(
                id=job.company.id,
                canonical_name=job.company.canonical_name,
                website=job.company.website,
                logo_url=_sanitize_logo_url(job.company.logo_url),
                identity_status=job.company.identity_status
            ),
            is_saved=is_saved,
            application_link_status=link_status,
            is_application_link_safe=is_safe,
            is_demo=bool((job.raw_source_data and isinstance(job.raw_source_data, dict) and job.raw_source_data.get("seed") is True) or job.id <= 7)
        )

    @staticmethod
    def get_similar_jobs(db: Session, job_id: int, limit: int = 5) -> SimilarJobResponse:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Find jobs in same company or same remote_type or overlapping title
        query = db.query(Job).join(Job.company).join(Job.source).options(
            joinedload(Job.company),
            joinedload(Job.source)
        ).filter(
            Job.id != job_id,
            Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]),
            or_(
                Job.raw_source_data.is_(None),
                Job.raw_source_data['seed'].astext.is_(None),
                Job.raw_source_data['seed'].astext != 'true'
            )
        )

        similar = query.filter(
            or_(
                Job.company_id == job.company_id,
                Job.remote_type == job.remote_type,
                Job.employment_type == job.employment_type
            )
        ).order_by(Job.posting_date.desc().nullslast(), Job.id.desc()).limit(limit).all()

        items = [
            JobListResponseItem(
                id=j.id,
                title=j.title,
                department=j.department,
                location=j.location,
                city=j.city,
                region=j.region,
                country=j.country,
                country_code=j.country_code,
                remote_type=j.remote_type,
                employment_type=j.employment_type,
                experience_level=j.experience_level,
                min_experience_years=j.min_experience_years,
                early_career_category=j.early_career_category,
                early_career_metadata=j.early_career_metadata,
                skills=j.skills or [],
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                salary_currency=j.salary_currency,
                salary_period=j.salary_period,
                posting_date=j.posting_date,
                status=j.status,
                application_url=j.application_url,
                company_id=j.company_id,
                company_name=j.company.canonical_name,
                company_logo=_sanitize_logo_url(j.company.logo_url),
                source_name=j.source.source_name,
                first_seen_at=j.first_seen_at,
                last_verified_at=j.last_verified_at,
                is_saved=False,
                is_demo=bool((j.raw_source_data and isinstance(j.raw_source_data, dict) and j.raw_source_data.get("seed") is True) or j.id <= 7)
            )
            for j in similar
        ]
        return SimilarJobResponse(jobs=items)

    @staticmethod
    def save_job(db: Session, user: User, job_id: int, notes: Optional[str] = None) -> SavedJob:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job listing not found")

        existing = db.query(SavedJob).filter(
            SavedJob.user_id == user.id,
            SavedJob.job_id == job_id
        ).first()

        if existing:
            if notes is not None:
                existing.notes = notes
                db.commit()
                db.refresh(existing)
            return existing

        saved = SavedJob(
            user_id=user.id,
            job_id=job_id,
            notes=notes
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)
        return saved

    @staticmethod
    def unsave_job(db: Session, user: User, job_id: int) -> bool:
        saved = db.query(SavedJob).filter(
            SavedJob.user_id == user.id,
            SavedJob.job_id == job_id
        ).first()
        if saved:
            db.delete(saved)
            db.commit()
            return True
        return False

    @staticmethod
    def get_saved_jobs(db: Session, user: User) -> List[SavedJob]:
        return db.query(SavedJob).options(
            joinedload(SavedJob.job).joinedload(Job.company),
            joinedload(SavedJob.job).joinedload(Job.source)
        ).filter(SavedJob.user_id == user.id).order_by(desc(SavedJob.created_at)).all()

    @staticmethod
    def get_profession_counts(db: Session) -> ProfessionListResponse:
        rows = db.query(Job.profession, func.count(Job.id)).filter(
            Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]),
            or_(
                Job.raw_source_data.is_(None),
                Job.raw_source_data['seed'].astext.is_(None),
                Job.raw_source_data['seed'].astext != 'true'
            )
        ).group_by(Job.profession).all()

        counts_map = {r[0]: r[1] for r in rows if r[0]}
        items = []

        for key, fam in TAXONOMY_FAMILIES.items():
            # Count canonical key plus legacy aliases
            cnt = counts_map.get(key, 0)
            for alias in fam.get("legacy_aliases", []):
                cnt += counts_map.get(alias, 0)

            items.append(ProfessionItem(
                key=key,
                label=fam["label"],
                category=fam.get("category"),
                count=cnt,
                description=fam["description"],
                icon=fam.get("icon"),
                canonical_roles=fam.get("canonical_roles", []),
                core_skills=fam.get("core_skills", [])
            ))

        # Backward compatibility alias for existing clients/tests
        if "ENGINEERING" not in [i.key for i in items]:
            sw_item = next((i for i in items if i.key == "SOFTWARE_IT"), None)
            if sw_item:
                items.append(ProfessionItem(
                    key="ENGINEERING",
                    label="Software & Engineering",
                    category="Software Engineering and IT",
                    count=sw_item.count,
                    description=sw_item.description,
                    icon="Code2",
                    canonical_roles=sw_item.canonical_roles,
                    core_skills=sw_item.core_skills
                ))

        items.sort(key=lambda x: x.count, reverse=True)
        total = sum(counts_map.values())
        return ProfessionListResponse(professions=items, total_jobs=total)

    @staticmethod
    def get_companies_summary(
        db: Session,
        query: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        ats_provider: Optional[str] = None,
        verification_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> CompanyListResponse:
        """
        Retrieves all verified companies with active job counts, career page URLs,
        and linked source counts without suppressing individual job records.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        comp_query = db.query(Company)
        if query and query.strip():
            raw_q = query.strip()
            norm_q = COMPANY_ALIASES.get(raw_q.lower(), raw_q)
            comp_query = comp_query.filter(
                or_(
                    Company.canonical_name.ilike(f"%{raw_q}%"),
                    Company.canonical_name.ilike(f"%{norm_q}%")
                )
            )
        if industry and industry.strip():
            ind_clean = industry.strip().replace("&", "%").replace("and", "%")
            # Collapse multiple consecutive % characters
            import re
            ind_clean = re.sub(r"%+", "%", ind_clean)
            comp_query = comp_query.filter(Company.industry.ilike(f"%{ind_clean}%"))
        if country and country.strip():
            comp_query = comp_query.filter(
                or_(
                    Company.country.ilike(f"%{country.strip()}%"),
                    Company.operating_region.ilike(f"%{country.strip()}%")
                )
            )
        if ats_provider and ats_provider.strip():
            comp_query = comp_query.filter(Company.ats_provider.ilike(f"%{ats_provider.strip()}%"))
        if verification_status and verification_status.strip():
            comp_query = comp_query.filter(Company.verification_status == verification_status.strip().upper())

        total = comp_query.count()
        offset = (page - 1) * page_size
        comps = comp_query.order_by(Company.canonical_name.asc()).offset(offset).limit(page_size).all()

        job_counts = dict(
            db.query(Job.company_id, func.count(Job.id))
            .filter(
                Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]),
                or_(
                    Job.raw_source_data.is_(None),
                    Job.raw_source_data['seed'].astext.is_(None),
                    Job.raw_source_data['seed'].astext != 'true'
                )
            )
            .group_by(Job.company_id)
            .all()
        )
        source_counts = dict(
            db.query(Source.company_id, func.count(Source.id))
            .group_by(Source.company_id)
            .all()
        )

        items = []
        for c in comps:
            items.append(CompanyItem(
                id=c.id,
                canonical_name=c.canonical_name,
                website=c.website,
                domain=c.domain,
                career_page_url=c.career_page_url,
                logo_url=_sanitize_logo_url(c.logo_url),
                identity_status=c.identity_status,
                verification_status=c.verification_status or "DISCOVERED",
                last_verified_at=c.last_verified_at,
                verification_notes=c.verification_notes,
                aliases=c.aliases or [],
                industry=c.industry,
                country=c.country,
                operating_region=c.operating_region,
                ats_provider=c.ats_provider,
                ats_board_id=c.ats_board_id,
                discovery_source=c.discovery_source,
                active_jobs_count=job_counts.get(c.id, 0),
                sources_count=source_counts.get(c.id, 0),
                last_successful_crawl=c.last_successful_crawl,
                source_health=c.source_health
            ))

        return CompanyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )

    @staticmethod
    def get_categories_summary(db: Session) -> Dict[str, Any]:
        """
        Returns available job categories and industries with active job counts.
        """
        counts_by_prof = dict(
            db.query(Job.profession, func.count(Job.id))
            .filter(
                Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]),
                or_(
                    Job.raw_source_data.is_(None),
                    Job.raw_source_data['seed'].astext.is_(None),
                    Job.raw_source_data['seed'].astext != 'true'
                )
            )
            .group_by(Job.profession)
            .all()
        )
        categories = []
        for fk, fdata in TAXONOMY_FAMILIES.items():
            count = counts_by_prof.get(fk, 0)
            for legacy in fdata.get("legacy_aliases", []):
                count += counts_by_prof.get(legacy, 0)
            categories.append({
                "key": fk,
                "label": fdata.get("label", fk),
                "category": fdata.get("category", fdata.get("label", fk)),
                "description": fdata.get("description", ""),
                "icon": fdata.get("icon", "Briefcase"),
                "active_jobs_count": count
            })
        categories.sort(key=lambda x: x["active_jobs_count"], reverse=True)
        total_active = sum(c["active_jobs_count"] for c in categories)
        return {
            "categories": categories,
            "total_active_jobs": total_active
        }

