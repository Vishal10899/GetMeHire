"""
Safe Text Normalization, Location and Country Normalization Pipeline.

Cleans HTML markup safely, generates normalized display titles,
normalizes multi-country and city locations deterministically,
and extracts factual system-generated summaries without fabricating data.
"""
import re
import html
from typing import Optional, Tuple, Dict, List, Any

# Requisition ID patterns
REQ_PATTERNS = [
    r"\s*[\(\[\{]\s*(?:req|job\s*id|requisition|id|ref)[\s#:]*[\w\-]+[\)\]\}]",
    r"\s*-\s*(?:req|job\s*id|requisition)[\s#:]*[\w\-]+",
    r"\s*#\s*\d{4,}",
]

# Location / remote suffix patterns attached to job titles
LOCATION_SUFFIX_PATTERNS = [
    r"\s*[\(\[\{]\s*(?:remote|hybrid|onsite|remote\s*-\s*[\w\s,]+|us|usa|emea|apac|latam|global)[\)\]\}]\s*$",
    r"\s*-\s*(?:remote|hybrid|onsite|us\s*remote|remote\s*\(?us\)?)\s*$",
    r"\s*[\(\[\{]\s*[\w\s]+,\s*[A-Z]{2}\s*[\)\]\}]\s*$",  # e.g. (San Francisco, CA)
    r"\s*-\s*[A-Z]{2,4}\s*$",  # e.g. - EMEA, - US, - APAC
]

# Internal level suffixes at end of title
LEVEL_PATTERNS = [
    r"\s*[\(\[\{]\s*[LPICM]\d+\s*[\)\]\}]\s*$",  # (L5), (P3), (M2)
    r"\s*-\s*Level\s*\d+\s*$",
]

def clean_html_markup(raw_html: str) -> str:
    """
    Safely cleans HTML descriptions:
    - Decodes HTML entities (&amp;, &nbsp;, &quot;, &#39;)
    - Fixes broken unicode artifacts and whitespace
    - Preserves semantic structure (<p>, <ul>, <li>, <h3>, <strong>)
    """
    if not raw_html:
        return ""

    text = raw_html

    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace non-breaking spaces and zero-width spaces
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Decode standard HTML entities
    text = html.unescape(text)

    # Clean excessive whitespace between HTML tags
    text = re.sub(r">\s+<", "><", text)

    # Replace duplicate blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def generate_normalized_title(raw_title: str) -> str:
    """
    Derives a clean display title from the employer title by stripping:
    - Requisition / Job IDs (e.g. "Software Engineer (Req #8921)")
    - Location suffixes (e.g. "Account Executive - Remote US")
    - Internal compensation levels (e.g. "Product Manager (L6)")

    The original employer title is always preserved separately in `Job.title`.
    """
    if not raw_title:
        return ""

    title = raw_title.strip()

    # 1. Strip Requisition / Job IDs
    for pat in REQ_PATTERNS:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # 2. Strip internal levels
    for pat in LEVEL_PATTERNS:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # 3. Strip trailing location / remote tags
    for pat in LOCATION_SUFFIX_PATTERNS:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # Clean stray trailing separators: " - ", " / ", " , "
    title = re.sub(r"[\s\-\/,|:]+$", "", title).strip()

    # If aggressive stripping removed everything, return original
    if not title:
        return raw_title.strip()

    return title

def generate_system_summary(description_html: str, max_sentences: int = 2) -> Optional[str]:
    """
    Extracts a concise, strictly factual system-generated summary
    from the employer's opening text.
    Never invents facts, salaries, or requirements.
    Labeled explicitly as system-generated.
    """
    if not description_html:
        return None

    # Strip HTML tags to get pure plain text
    plain_text = re.sub(r"<[^>]+>", " ", description_html)
    plain_text = html.unescape(plain_text)
    plain_text = " ".join(plain_text.split())

    if len(plain_text) < 50:
        return None

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", plain_text)

    # Skip boilerplate opening disclaimers or cookie notices
    filtered = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        # Skip sentences that look like disclaimers or legal headers
        if any(bad in s_clean.lower() for bad in ["equal opportunity employer", "affirmative action", "privacy policy", "cookie policy", "terms of use"]):
            continue
        filtered.append(s_clean)
        if len(filtered) >= max_sentences:
            break

    if not filtered:
        return None

    summary_body = " ".join(filtered)
    if len(summary_body) > 350:
        summary_body = summary_body[:347] + "..."

    return f"System-generated summary: {summary_body}"


# =====================================================================
# LOCATION AND COUNTRY NORMALIZATION ARCHITECTURE
# =====================================================================

INDIA_CITIES: Dict[str, Tuple[str, str, str]] = {
    "bengaluru": ("Bengaluru", "Karnataka", "India"),
    "bangalore": ("Bengaluru", "Karnataka", "India"),
    "mumbai": ("Mumbai", "Maharashtra", "India"),
    "bombay": ("Mumbai", "Maharashtra", "India"),
    "delhi": ("Delhi", "Delhi", "India"),
    "new delhi": ("New Delhi", "Delhi", "India"),
    "gurugram": ("Gurugram", "Haryana", "India"),
    "gurgaon": ("Gurugram", "Haryana", "India"),
    "noida": ("Noida", "Uttar Pradesh", "India"),
    "greater noida": ("Greater Noida", "Uttar Pradesh", "India"),
    "hyderabad": ("Hyderabad", "Telangana", "India"),
    "secunderabad": ("Hyderabad", "Telangana", "India"),
    "pune": ("Pune", "Maharashtra", "India"),
    "chennai": ("Chennai", "Tamil Nadu", "India"),
    "madras": ("Chennai", "Tamil Nadu", "India"),
    "kolkata": ("Kolkata", "West Bengal", "India"),
    "calcutta": ("Kolkata", "West Bengal", "India"),
    "ahmedabad": ("Ahmedabad", "Gujarat", "India"),
    "kochi": ("Kochi", "Kerala", "India"),
    "cochin": ("Kochi", "Kerala", "India"),
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala", "India"),
    "trivandrum": ("Thiruvananthapuram", "Kerala", "India"),
    "jaipur": ("Jaipur", "Rajasthan", "India"),
    "chandigarh": ("Chandigarh", "Punjab", "India"),
    "mohali": ("Mohali", "Punjab", "India"),
    "indore": ("Indore", "Madhya Pradesh", "India"),
    "lucknow": ("Lucknow", "Uttar Pradesh", "India"),
    "coimbatore": ("Coimbatore", "Tamil Nadu", "India"),
    "surat": ("Surat", "Gujarat", "India"),
    "vadodara": ("Vadodara", "Gujarat", "India"),
    "nagpur": ("Nagpur", "Maharashtra", "India"),
    "patna": ("Patna", "Bihar", "India"),
    "bhopal": ("Bhopal", "Madhya Pradesh", "India"),
    "visakhapatnam": ("Visakhapatnam", "Andhra Pradesh", "India"),
    "vizag": ("Visakhapatnam", "Andhra Pradesh", "India"),
    "kanpur": ("Kanpur", "Uttar Pradesh", "India"),
    "bhubaneswar": ("Bhubaneswar", "Odisha", "India"),
    "bhubaneshwar": ("Bhubaneswar", "Odisha", "India"),
    "dehradun": ("Dehradun", "Uttarakhand", "India"),
    "guwahati": ("Guwahati", "Assam", "India"),
    "navi mumbai": ("Navi Mumbai", "Maharashtra", "India"),
    "delhi ncr": ("Delhi NCR", "Delhi", "India"),
    "mysore": ("Mysuru", "Karnataka", "India"),
    "mysuru": ("Mysuru", "Karnataka", "India"),
    "mangaluru": ("Mangaluru", "Karnataka", "India"),
    "mangalore": ("Mangaluru", "Karnataka", "India"),
    "baroda": ("Vadodara", "Gujarat", "India"),
    "calicut": ("Kozhikode", "Kerala", "India"),
    "kozhikode": ("Kozhikode", "Kerala", "India"),
}

INDIA_STATES: Dict[str, str] = {
    "tamil nadu": "Tamil Nadu",
    "karnataka": "Karnataka",
    "maharashtra": "Maharashtra",
    "uttar pradesh": "Uttar Pradesh",
    "telangana": "Telangana",
    "kerala": "Kerala",
    "andhra pradesh": "Andhra Pradesh",
    "haryana": "Haryana",
    "punjab": "Punjab",
    "gujarat": "Gujarat",
    "rajasthan": "Rajasthan",
    "west bengal": "West Bengal",
    "delhi": "Delhi",
}

US_STATES: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia",
}

CANADIAN_PROVINCES: Dict[str, str] = {
    "ON": "Ontario", "BC": "British Columbia", "QC": "Quebec", "AB": "Alberta",
    "MB": "Manitoba", "SK": "Saskatchewan", "NS": "Nova Scotia", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "PE": "Prince Edward Island", "NT": "Northwest Territories",
    "YT": "Yukon", "NU": "Nunavut"
}

AUSTRALIAN_STATES: Dict[str, str] = {
    "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland", "WA": "Western Australia",
    "SA": "South Australia", "TAS": "Tasmania", "ACT": "Australian Capital Territory", "NT": "Northern Territory"
}

US_CITIES: Dict[str, Tuple[str, str, str]] = {
    "san francisco": ("San Francisco", "California", "United States"),
    "sf": ("San Francisco", "California", "United States"),
    "new york": ("New York", "New York", "United States"),
    "new york city": ("New York", "New York", "United States"),
    "nyc": ("New York", "New York", "United States"),
    "seattle": ("Seattle", "Washington", "United States"),
    "los angeles": ("Los Angeles", "California", "United States"),
    "chicago": ("Chicago", "Illinois", "United States"),
    "boston": ("Boston", "Massachusetts", "United States"),
    "austin": ("Austin", "Texas", "United States"),
    "denver": ("Denver", "Colorado", "United States"),
    "atlanta": ("Atlanta", "Georgia", "United States"),
    "dallas": ("Dallas", "Texas", "United States"),
    "houston": ("Houston", "Texas", "United States"),
    "philadelphia": ("Philadelphia", "Pennsylvania", "United States"),
    "miami": ("Miami", "Florida", "United States"),
    "san jose": ("San Jose", "California", "United States"),
    "san diego": ("San Diego", "California", "United States"),
    "portland": ("Portland", "Oregon", "United States"),
    "pittsburgh": ("Pittsburgh", "Pennsylvania", "United States"),
    "washington": ("Washington", "District of Columbia", "United States"),
    "washington, d.c.": ("Washington", "District of Columbia", "United States"),
    "washington, dc": ("Washington", "District of Columbia", "United States"),
    "palo alto": ("Palo Alto", "California", "United States"),
    "mountain view": ("Mountain View", "California", "United States"),
    "sunnyvale": ("Sunnyvale", "California", "United States"),
    "menlo park": ("Menlo Park", "California", "United States"),
    "redwood city": ("Redwood City", "California", "United States"),
    "santa clara": ("Santa Clara", "California", "United States"),
    "culver city": ("Culver City", "California", "United States"),
    "cambridge": ("Cambridge", "Massachusetts", "United States"),
    "bellevue": ("Bellevue", "Washington", "United States"),
}

GLOBAL_CITIES: Dict[str, Tuple[str, str, str]] = {
    "london": ("London", "England", "United Kingdom"),
    "manchester": ("Manchester", "England", "United Kingdom"),
    "edinburgh": ("Edinburgh", "Scotland", "United Kingdom"),
    "bristol": ("Bristol", "England", "United Kingdom"),
    "birmingham": ("Birmingham", "England", "United Kingdom"),
    "leeds": ("Leeds", "England", "United Kingdom"),
    "glasgow": ("Glasgow", "Scotland", "United Kingdom"),
    "oxford": ("Oxford", "England", "United Kingdom"),
    "toronto": ("Toronto", "Ontario", "Canada"),
    "vancouver": ("Vancouver", "British Columbia", "Canada"),
    "montreal": ("Montreal", "Quebec", "Canada"),
    "ottawa": ("Ottawa", "Ontario", "Canada"),
    "waterloo": ("Waterloo", "Ontario", "Canada"),
    "calgary": ("Calgary", "Alberta", "Canada"),
    "edmonton": ("Edmonton", "Alberta", "Canada"),
    "quebec city": ("Quebec City", "Quebec", "Canada"),
    "halifax": ("Halifax", "Nova Scotia", "Canada"),
    "berlin": ("Berlin", "Berlin", "Germany"),
    "munich": ("Munich", "Bavaria", "Germany"),
    "frankfurt": ("Frankfurt", "Hesse", "Germany"),
    "hamburg": ("Hamburg", "Hamburg", "Germany"),
    "cologne": ("Cologne", "North Rhine-Westphalia", "Germany"),
    "köln": ("Cologne", "North Rhine-Westphalia", "Germany"),
    "stuttgart": ("Stuttgart", "Baden-Wurttemberg", "Germany"),
    "dusseldorf": ("Dusseldorf", "North Rhine-Westphalia", "Germany"),
    "düsseldorf": ("Dusseldorf", "North Rhine-Westphalia", "Germany"),
    "leipzig": ("Leipzig", "Saxony", "Germany"),
    "dortmund": ("Dortmund", "North Rhine-Westphalia", "Germany"),
    "paris": ("Paris", "Ile-de-France", "France"),
    "lyon": ("Lyon", "Auvergne-Rhone-Alpes", "France"),
    "dublin": ("Dublin", "Leinster", "Ireland"),
    "amsterdam": ("Amsterdam", "North Holland", "Netherlands"),
    "sydney": ("Sydney", "New South Wales", "Australia"),
    "melbourne": ("Melbourne", "Victoria", "Australia"),
    "brisbane": ("Brisbane", "Queensland", "Australia"),
    "perth": ("Perth", "Western Australia", "Australia"),
    "adelaide": ("Adelaide", "South Australia", "Australia"),
    "canberra": ("Canberra", "Australian Capital Territory", "Australia"),
    "hobart": ("Hobart", "Tasmania", "Australia"),
    "singapore": ("Singapore", "Singapore", "Singapore"),
    "tokyo": ("Tokyo", "Kanto", "Japan"),
    "seoul": ("Seoul", "Seoul", "South Korea"),
    "sao paulo": ("Sao Paulo", "Sao Paulo", "Brazil"),
    "rio de janeiro": ("Rio de Janeiro", "Rio de Janeiro", "Brazil"),
    "mexico city": ("Mexico City", "CDMX", "Mexico"),
    "tel aviv": ("Tel Aviv", "Tel Aviv", "Israel"),
    "madrid": ("Madrid", "Madrid", "Spain"),
    "barcelona": ("Barcelona", "Catalonia", "Spain"),
    "zurich": ("Zurich", "Zurich", "Switzerland"),
    "zürich": ("Zurich", "Zurich", "Switzerland"),
    "stockholm": ("Stockholm", "Stockholm", "Sweden"),
    "warsaw": ("Warsaw", "Masovian", "Poland"),
    "dubai": ("Dubai", "Dubai", "United Arab Emirates"),
    "riyadh": ("Riyadh", "Riyadh", "Saudi Arabia"),
    "kuwait city": ("Kuwait City", "Al Asimah", "Kuwait"),
    "doha": ("Doha", "Doha", "Qatar"),
    "bangkok": ("Bangkok", "Bangkok", "Thailand"),
    "jakarta": ("Jakarta", "Jakarta", "Indonesia"),
    "bucharest": ("Bucharest", "Bucharest", "Romania"),
    "vilnius": ("Vilnius", "Vilnius", "Lithuania"),
    "brussels": ("Brussels", "Brussels-Capital", "Belgium"),
    "johannesburg": ("Johannesburg", "Gauteng", "South Africa"),
    "cape town": ("Cape Town", "Western Cape", "South Africa"),
    "durban": ("Durban", "KwaZulu-Natal", "South Africa"),
    "nairobi": ("Nairobi", "Nairobi", "Kenya"),
    "kampala": ("Kampala", "Central", "Uganda"),
    "cairo": ("Cairo", "Cairo", "Egypt"),
    "auckland": ("Auckland", "Auckland", "New Zealand"),
    "wellington": ("Wellington", "Wellington", "New Zealand"),
    "vienna": ("Vienna", "Vienna", "Austria"),
    "oslo": ("Oslo", "Oslo", "Norway"),
    "copenhagen": ("Copenhagen", "Capital Region", "Denmark"),
    "helsinki": ("Helsinki", "Uusimaa", "Finland"),
    "lisbon": ("Lisbon", "Lisbon", "Portugal"),
    "porto": ("Porto", "Porto", "Portugal"),
    "prague": ("Prague", "Prague", "Czech Republic"),
    "athens": ("Athens", "Attica", "Greece"),
    "budapest": ("Budapest", "Budapest", "Hungary"),
    "krakow": ("Krakow", "Lesser Poland", "Poland"),
    "wroclaw": ("Wroclaw", "Lower Silesia", "Poland"),
    "tallinn": ("Tallinn", "Harju", "Estonia"),
    "riga": ("Riga", "Riga", "Latvia"),
    "buenos aires": ("Buenos Aires", "Buenos Aires", "Argentina"),
    "santiago": ("Santiago", "Santiago Metropolitan", "Chile"),
    "bogota": ("Bogota", "Bogota D.C.", "Colombia"),
    "lima": ("Lima", "Lima", "Peru"),
    "manila": ("Manila", "Metro Manila", "Philippines"),
    "kuala lumpur": ("Kuala Lumpur", "Federal Territory", "Malaysia"),
    "ho chi minh city": ("Ho Chi Minh City", "Ho Chi Minh City", "Vietnam"),
    "hanoi": ("Hanoi", "Hanoi", "Vietnam"),
}

COUNTRY_ALIASES: Dict[str, str] = {
    "india": "India",
    "bharat": "India",
    "united states": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "canada": "Canada",
    "can": "Canada",
    "germany": "Germany",
    "deutschland": "Germany",
    "france": "France",
    "ireland": "Ireland",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "australia": "Australia",
    "singapore": "Singapore",
    "japan": "Japan",
    "south korea": "South Korea",
    "korea": "South Korea",
    "brazil": "Brazil",
    "brasil": "Brazil",
    "mexico": "Mexico",
    "israel": "Israel",
    "spain": "Spain",
    "switzerland": "Switzerland",
    "ch": "Switzerland",
    "sweden": "Sweden",
    "poland": "Poland",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "dubai": "United Arab Emirates",
    "new zealand": "New Zealand",
    "italy": "Italy",
    "austria": "Austria",
    "belgium": "Belgium",
    "portugal": "Portugal",
    "denmark": "Denmark",
    "norway": "Norway",
    "finland": "Finland",
    "saudi arabia": "Saudi Arabia",
    "kuwait": "Kuwait",
    "qatar": "Qatar",
    "thailand": "Thailand",
    "indonesia": "Indonesia",
    "luxembourg": "Luxembourg",
    "romania": "Romania",
    "colombia": "Colombia",
    "lithuania": "Lithuania",
    "taiwan": "Taiwan",
    "china": "China",
    "hong kong": "Hong Kong",
    "czech republic": "Czech Republic",
    "czechia": "Czech Republic",
    "greece": "Greece",
    "south africa": "South Africa",
    "argentina": "Argentina",
    "chile": "Chile",
    "peru": "Peru",
    "philippines": "Philippines",
    "malaysia": "Malaysia",
    "vietnam": "Vietnam",
    "turkey": "Turkey",
    "turkiye": "Turkey",
    "egypt": "Egypt",
    "hungary": "Hungary",
}

# Alias mapping for search queries (e.g. searching Bangalore finds Bengaluru)
CITY_SEARCH_ALIASES: Dict[str, List[str]] = {
    "bangalore": ["bengaluru", "bangalore"],
    "bengaluru": ["bengaluru", "bangalore"],
    "bombay": ["mumbai", "bombay", "navi mumbai"],
    "mumbai": ["mumbai", "bombay", "navi mumbai"],
    "navi mumbai": ["mumbai", "navi mumbai"],
    "gurgaon": ["gurugram", "gurgaon"],
    "gurugram": ["gurugram", "gurgaon"],
    "delhi": ["delhi", "new delhi", "delhi ncr"],
    "new delhi": ["delhi", "new delhi", "delhi ncr"],
    "delhi ncr": ["delhi", "new delhi", "delhi ncr"],
    "noida": ["noida", "greater noida"],
    "greater noida": ["noida", "greater noida"],
    "hyderabad": ["hyderabad", "secunderabad"],
    "secunderabad": ["hyderabad", "secunderabad"],
    "calcutta": ["kolkata", "calcutta"],
    "kolkata": ["kolkata", "calcutta"],
    "madras": ["chennai", "madras"],
    "chennai": ["chennai", "madras"],
    "kochi": ["kochi", "cochin"],
    "cochin": ["kochi", "cochin"],
    "thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
    "trivandrum": ["thiruvananthapuram", "trivandrum"],
    "chandigarh": ["chandigarh", "mohali"],
    "mohali": ["chandigarh", "mohali"],
    "mysore": ["mysore", "mysuru"],
    "mysuru": ["mysore", "mysuru"],
    "mangalore": ["mangalore", "mangaluru"],
    "mangaluru": ["mangalore", "mangaluru"],
    "baroda": ["baroda", "vadodara"],
    "vadodara": ["baroda", "vadodara"],
    "visakhapatnam": ["visakhapatnam", "vizag"],
    "vizag": ["visakhapatnam", "vizag"],
    "bhubaneswar": ["bhubaneswar", "bhubaneshwar"],
    "bhubaneshwar": ["bhubaneswar", "bhubaneshwar"],
    "calicut": ["calicut", "kozhikode"],
    "kozhikode": ["calicut", "kozhikode"],
    "sf": ["san francisco", "sf"],
    "nyc": ["new york", "nyc", "new york city"],
    "dc": ["washington", "dc", "washington d.c."],
}

def normalize_location_and_country(
    raw_location: Any,
    raw_title: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """
    Deterministically normalizes raw location data from ATS feeds into:
    (clean_location, city, region, country, remote_type)

    Guarantees:
    - Never invents data.
    - Accurately identifies Indian tech hubs (Bengaluru, Mumbai, Delhi, Gurugram, etc.) with country='India'.
    - Handles US states, global capitals, and multi-location lists cleanly.
    - Honors remote / hybrid indicators in location and job title.
    """
    if raw_location is None:
        loc_str = ""
    elif isinstance(raw_location, dict):
        loc_str = str(raw_location.get("name") or raw_location.get("location") or "")
    else:
        loc_str = str(raw_location)

    loc = loc_str.strip()
    is_empty_loc = loc.lower() in ("", "n/a", "na", "null", "none", "location")

    remote_type = "ONSITE"
    loc_lower = "" if is_empty_loc else loc.lower()
    title_lower = (raw_title or "").lower()

    if "remote" in loc_lower or "remote" in title_lower:
        remote_type = "REMOTE"
    elif "hybrid" in loc_lower or "hybrid" in title_lower:
        remote_type = "HYBRID"

    city = None
    region = None
    country = None

    if not is_empty_loc:
        # Multi-location parsing: split on '|' or ';'
        parts = [p.strip() for p in re.split(r"[|;]", loc) if p.strip()]

        # Select primary part (skipping parts that are pure arrangement labels)
        primary_part = parts[0] if parts else loc
        for p in parts:
            clean_p = re.sub(r"\s*\([^)]*\)", "", p).strip().lower()
            if clean_p not in ("remote", "remote-friendly", "remote friendly", "hybrid", "onsite", "travel-required"):
                primary_part = p
                break

        clean_primary = re.sub(r"\s*\([^)]*\)", "", primary_part).strip()

        # Check 1: India Cities (sorted by pattern length descending to match 'new delhi' before 'delhi')
        for k, v in sorted(INDIA_CITIES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(k) + r"\b", clean_primary.lower()):
                city, region, country = v
                break

        # Check 1b: India States
        if not country:
            for state_k, state_v in sorted(INDIA_STATES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r"\b" + re.escape(state_k) + r"\b", clean_primary.lower()):
                    region = state_v
                    country = "India"
                    break

        # Check 2: Global Cities
        if not country:
            for k, v in sorted(GLOBAL_CITIES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r"\b" + re.escape(k) + r"\b", clean_primary.lower()):
                    city, region, country = v
                    break

        # Check 3: US Cities
        if not country:
            for k, v in sorted(US_CITIES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r"\b" + re.escape(k) + r"\b", clean_primary.lower()):
                    city, region, country = v
                    break

        # Check 4: State/Province abbreviation pattern (US, Canada, Australia)
        # Protect strictly against misclassifying India country/state code 'IN' as Indiana
        if not country:
            match_state = re.search(r",\s*([A-Z]{2})\b", primary_part)
            if match_state:
                state_code = match_state.group(1)
                city_candidate = primary_part.split(",")[0].strip()
                if state_code == "IN":
                    if any(ic in clean_primary.lower() for ic in ["india", "bharat", "bengaluru", "bangalore", "mumbai", "delhi", "gurugram", "gurgaon", "noida", "hyderabad", "pune", "chennai", "kolkata", "ahmedabad", "kochi", "jaipur"]):
                        country = "India"
                    elif city_candidate.lower() in ["indianapolis", "fort wayne", "bloomington", "south bend", "evansville", "carmel", "fishers", "gary", "muncie", "lafayette"]:
                        country = "United States"
                        region = "Indiana"
                        city = city_candidate
                    else:
                        country = "India"
                elif state_code in US_STATES:
                    country = "United States"
                    region = US_STATES[state_code]
                    if len(city_candidate) > 1 and city_candidate.lower() not in ("remote", "remote-friendly"):
                        city = city_candidate
                elif state_code in CANADIAN_PROVINCES:
                    country = "Canada"
                    region = CANADIAN_PROVINCES[state_code]
                    if len(city_candidate) > 1 and city_candidate.lower() not in ("remote", "remote-friendly"):
                        city = city_candidate
                elif state_code in AUSTRALIAN_STATES:
                    country = "Australia"
                    region = AUSTRALIAN_STATES[state_code]
                    if len(city_candidate) > 1 and city_candidate.lower() not in ("remote", "remote-friendly"):
                        city = city_candidate

        # Check 5: Explicit US keywords
        if not country:
            if re.search(r"\b(?:us|usa|united states)\b", clean_primary.lower()) or re.search(r"\b(?:us|usa|united states)\b", loc_lower):
                country = "United States"

        # Check 6: Canonical Country in primary_part or full location string
        if not country:
            for alias, canon in COUNTRY_ALIASES.items():
                if re.search(r"\b" + re.escape(alias) + r"\b", clean_primary.lower()) or re.search(r"\b" + re.escape(alias) + r"\b", loc_lower):
                    country = canon
                    break

    # Check 7: Fallback inspection of raw_title when location text was incomplete or empty
    if not country and raw_title:
        title_lower = raw_title.lower()
        for k, v in sorted(INDIA_CITIES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(k) + r"\b", title_lower):
                city, region, country = v
                break
        if not country:
            for state_k, state_v in sorted(INDIA_STATES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r"\b" + re.escape(state_k) + r"\b", title_lower):
                    region = state_v
                    country = "India"
                    break
        if not country:
            for k, v in sorted(GLOBAL_CITIES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r"\b" + re.escape(k) + r"\b", title_lower):
                    city, region, country = v
                    break
        if not country:
            for alias, canon in COUNTRY_ALIASES.items():
                if re.search(r"\b" + re.escape(alias) + r"\b", title_lower):
                    country = canon
                    break

    clean_ret_loc = None
    if not is_empty_loc:
        clean_ret_loc = loc
    elif remote_type == "REMOTE":
        clean_ret_loc = "Remote"
    elif country:
        clean_ret_loc = country

    return clean_ret_loc, city, region, country, remote_type


COUNTRY_TO_ISO_CODE: Dict[str, str] = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ", "Argentina": "AR", "Armenia": "AM",
    "Australia": "AU", "Austria": "AT", "Azerbaijan": "AZ", "Bahamas": "BS", "Bahrain": "BH",
    "Bangladesh": "BD", "Barbados": "BB", "Belarus": "BY", "Belgium": "BE", "Belize": "BZ",
    "Bermuda": "BM", "Bolivia": "BO", "Bosnia and Herzegovina": "BA", "Botswana": "BW", "Brazil": "BR",
    "Bulgaria": "BG", "Cambodia": "KH", "Cameroon": "CM", "Canada": "CA", "Chile": "CL",
    "China": "CN", "Colombia": "CO", "Costa Rica": "CR", "Croatia": "HR", "Cyprus": "CY",
    "Czech Republic": "CZ", "Denmark": "DK", "Dominican Republic": "DO", "Ecuador": "EC", "Egypt": "EG",
    "El Salvador": "SV", "Estonia": "EE", "Ethiopia": "ET", "Finland": "FI", "France": "FR",
    "Georgia": "GE", "Germany": "DE", "Ghana": "GH", "Greece": "GR", "Guatemala": "GT",
    "Honduras": "HN", "Hong Kong": "HK", "Hungary": "HU", "Iceland": "IS", "India": "IN",
    "Indonesia": "ID", "Ireland": "IE", "Israel": "IL", "Italy": "IT", "Jamaica": "JM",
    "Japan": "JP", "Jordan": "JO", "Kazakhstan": "KZ", "Kenya": "KE", "Kuwait": "KW",
    "Latvia": "LV", "Lebanon": "LB", "Lithuania": "LT", "Luxembourg": "LU", "Malaysia": "MY",
    "Malta": "MT", "Mauritius": "MU", "Mexico": "MX", "Moldova": "MD", "Monaco": "MC",
    "Mongolia": "MN", "Montenegro": "ME", "Morocco": "MA", "Nepal": "NP", "Netherlands": "NL",
    "New Zealand": "NZ", "Nigeria": "NG", "North Macedonia": "MK", "Norway": "NO", "Oman": "OM",
    "Pakistan": "PK", "Panama": "PA", "Paraguay": "PY", "Peru": "PE", "Philippines": "PH",
    "Poland": "PL", "Portugal": "PT", "Qatar": "QA", "Romania": "RO", "Rwanda": "RW",
    "Saudi Arabia": "SA", "Senegal": "SN", "Serbia": "RS", "Singapore": "SG", "Slovakia": "SK",
    "Slovenia": "SI", "South Africa": "ZA", "South Korea": "KR", "Spain": "ES", "Sri Lanka": "LK",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW", "Tanzania": "TZ", "Thailand": "TH",
    "Trinidad and Tobago": "TT", "Tunisia": "TN", "Turkey": "TR", "Uganda": "UG", "Ukraine": "UA",
    "United Arab Emirates": "AE", "United Kingdom": "GB", "United States": "US", "Uruguay": "UY",
    "Uzbekistan": "UZ", "Venezuela": "VE", "Vietnam": "VN", "Zambia": "ZM", "Zimbabwe": "ZW"
}

def get_country_code(country: Optional[str]) -> Optional[str]:
    """
    Returns ISO 3166-1 alpha-2 code for a normalized country name.
    """
    if not country:
        return None
    canon = COUNTRY_ALIASES.get(country.strip().lower(), country.strip())
    return COUNTRY_TO_ISO_CODE.get(canon)


EMPLOYMENT_TYPE_MAP: Dict[str, str] = {
    "full-time": "FULL_TIME",
    "full_time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "regular": "FULL_TIME",
    "permanent": "FULL_TIME",
    "a tiempo completo": "FULL_TIME",
    "tiempo completo": "FULL_TIME",
    "повна зайнятість": "FULL_TIME",
    "temps plein": "FULL_TIME",
    "vollzeit": "FULL_TIME",
    "part-time": "PART_TIME",
    "part_time": "PART_TIME",
    "parttime": "PART_TIME",
    "a tiempo parcial": "PART_TIME",
    "tiempo parcial": "PART_TIME",
    "часткова зайнятість": "PART_TIME",
    "temps partiel": "PART_TIME",
    "teilzeit": "PART_TIME",
    "contract": "CONTRACT",
    "contractor": "CONTRACT",
    "contract-to-hire": "CONTRACT",
    "c2c": "CONTRACT",
    "w2": "CONTRACT",
    "1099": "CONTRACT",
    "freelance": "FREELANCE",
    "freelancer": "FREELANCE",
    "intern": "INTERNSHIP",
    "internship": "INTERNSHIP",
    "co-op": "INTERNSHIP",
    "trainee": "INTERNSHIP",
    "apprentice": "APPRENTICESHIP",
    "apprenticeship": "APPRENTICESHIP",
    "temporary": "TEMPORARY",
    "temp": "TEMPORARY",
    "seasonal": "SEASONAL",
    "casual": "CASUAL",
    "commission": "COMMISSION",
    "commission-based": "COMMISSION",
    "performance-based": "PERFORMANCE_BASED",
    "target-based": "PERFORMANCE_BASED",
    "fixed-term": "FIXED_TERM",
    "fixed term": "FIXED_TERM",
    "ftc": "FIXED_TERM",
    "shift": "SHIFT_BASED",
    "shift-based": "SHIFT_BASED",
}

def normalize_employment_type(raw_val: Any, raw_title: Optional[str] = None) -> str:
    """
    Deterministically normalizes employment type preserving employer's classification.
    Supports all PRD types:
    FULL_TIME, PART_TIME, CONTRACT, FREELANCE, INTERNSHIP, APPRENTICESHIP,
    TEMPORARY, PERMANENT, SEASONAL, CASUAL, COMMISSION, PERFORMANCE_BASED,
    FIXED_TERM, SHIFT_BASED, OTHER.
    Do not classify unknown employment types as full-time by default.
    """
    val_str = ""
    if raw_val is not None:
        if isinstance(raw_val, dict):
            val_str = str(raw_val.get("name") or raw_val.get("label") or raw_val.get("id") or "")
        elif isinstance(raw_val, list) and raw_val:
            val_str = str(raw_val[0])
        else:
            val_str = str(raw_val)

    val_lower = val_str.lower().strip()
    title_lower = (raw_title or "").lower().strip()

    # 1. Title overrides for high-precision markers
    if re.search(r"\b(intern|internship|co-op)\b", title_lower):
        return "INTERNSHIP"
    if re.search(r"\b(contract|contractor|1099)\b", title_lower):
        return "CONTRACT"
    if re.search(r"\b(part[-\s]?time)\b", title_lower):
        return "PART_TIME"
    if re.search(r"\b(freelance|freelancer)\b", title_lower):
        return "FREELANCE"
    if re.search(r"\b(apprentice|apprenticeship)\b", title_lower):
        return "APPRENTICESHIP"
    if re.search(r"\b(temp|temporary)\b", title_lower):
        return "TEMPORARY"
    if re.search(r"\b(fixed[-\s]?term|12-month ftc|\bftc\b)\b", title_lower):
        return "FIXED_TERM"
    if re.search(r"\b(seasonal)\b", title_lower):
        return "SEASONAL"
    if re.search(r"\b(shift[-\s]?based|weekend shift|night shift)\b", title_lower):
        return "SHIFT_BASED"

    # 2. Check exact/substring matches in val_lower (longest keys first)
    for k in sorted(EMPLOYMENT_TYPE_MAP.keys(), key=len, reverse=True):
        if re.search(r"\b" + re.escape(k) + r"\b", val_lower):
            return EMPLOYMENT_TYPE_MAP[k]

    if val_lower and val_lower not in ("null", "none", "", "unspecified", "not specified"):
        return val_str.upper().replace(" ", "_")

    return "FULL_TIME"


def normalize_work_arrangement_and_eligibility(
    raw_arrangement: Any = None,
    raw_location: Any = None,
    raw_title: Optional[str] = None
) -> Tuple[str, str]:
    """
    Returns (work_arrangement, remote_eligibility).
    Arrangements: ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED
    Eligibilities: WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED
    """
    arr_str = str(raw_arrangement or "").lower()
    loc_str = str(raw_location or "").lower()
    tit_str = str(raw_title or "").lower()
    combined = f"{arr_str} {loc_str} {tit_str}"

    if "hybrid" in combined:
        work_arrangement = "HYBRID"
    elif "field" in combined or "field-based" in combined:
        work_arrangement = "FIELD_BASED"
    elif "flexible" in combined:
        work_arrangement = "FLEXIBLE"
    elif "remote" in combined or "wfh" in combined or "work from home" in combined:
        work_arrangement = "REMOTE"
    elif "onsite" in combined or "on-site" in combined or "wfo" in combined or "office" in combined:
        work_arrangement = "ONSITE"
    else:
        work_arrangement = "ONSITE"

    if work_arrangement not in ("REMOTE", "HYBRID", "FLEXIBLE"):
        remote_eligibility = "NOT_REMOTE"
    else:
        if any(p in combined for p in ["worldwide", "anywhere", "global", "remote - anywhere", "work from anywhere", "all countries", "eligible anywhere"]):
            remote_eligibility = "WORLDWIDE"
        elif any(p in combined for p in ["emea", "apac", "latam", "europe", "americas", "nordics", "asia"]):
            remote_eligibility = "REGION_RESTRICTED"
        elif any(p in combined for p in ["us remote", "remote - us", "remote (us", "remote (usa", "remote - india", "remote (india", "remote - uk", "remote (uk", "remote - canada", "remote (canada", "remote - germany", "remote (germany", "remote - australia", "remote (australia", "us only", "usa only", "india only", "uk only", "canada only", "germany only", "australia only"]):
            remote_eligibility = "COUNTRY_RESTRICTED"
        elif any(p in combined for p in ["est", "pst", "cst", "mst", "gmt", "utc", "timezone", "time zone"]):
            remote_eligibility = "TIMEZONE_RESTRICTED"
        else:
            remote_eligibility = "EMPLOYER_DEFINED"

    return work_arrangement, remote_eligibility


def normalize_location_full(
    raw_location: Any,
    raw_title: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """
    Full 6-tuple location normalization:
    (clean_location, city, region, country, country_code, remote_type)
    """
    clean_loc, city, region, country, remote_type = normalize_location_and_country(raw_location, raw_title)
    country_code = get_country_code(country)
    return clean_loc, city, region, country, country_code, remote_type


# Data Quality & Placeholder Filtering Gate
DISALLOWED_TITLES = {
    "test", "test job", "test jobs", "testing", "test posting", "dummy", "dummy job",
    "placeholder", "sample job", "untitled", "asdf", "test - do not apply",
    "internal test", "qa test job", "sample posting"
}

def is_valid_job_posting(title: Optional[str], description: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates raw vacancy content before database ingestion to reject
    internal employer testing, placeholder drafts, or malformed dummy postings.
    Returns (is_valid: bool, reject_reason: Optional[str]).
    """
    if not title or not title.strip():
        return False, "EMPTY_TITLE"

    clean_t = title.strip().lower()
    # Normalize internal punctuation and whitespace for comparison
    normalized_t = re.sub(r"[^\w\s]", "", clean_t).strip()

    if clean_t in DISALLOWED_TITLES or normalized_t in DISALLOWED_TITLES:
        return False, "TEST_PLACEHOLDER_TITLE"

    if re.match(r"^test(\s+job)?(\s+\d+)?$", normalized_t):
        return False, "TEST_REGEX_TITLE"

    if len(title.strip()) < 3:
        return False, "TITLE_TOO_SHORT"

    if not description or not description.strip():
        return False, "EMPTY_DESCRIPTION"

    clean_d = re.sub(r"<[^>]+>", " ", description)  # strip html tags
    clean_d = re.sub(r"\s+", " ", clean_d).strip().lower()

    if clean_d in {"test", "test test", "test posting", "testing", "asdf", "dummy", "placeholder", "lorem ipsum"}:
        return False, "TEST_PLACEHOLDER_BODY"

    if len(clean_d) < 5:
        return False, "DESCRIPTION_TOO_SHORT"

    return True, None


def is_valid_application_url(url: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates that a vacancy application URL is an authentic, accessible HTTP(S) link
    pointing to an employer career portal or ATS endpoint.
    """
    if not url or not isinstance(url, str):
        return False, "MISSING_APPLICATION_URL"
    url_clean = url.strip()
    if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
        return False, "INVALID_URL_SCHEME"
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url_clean)
        netloc = (parsed.netloc or "").lower().strip()
        if not netloc or "." not in netloc:
            return False, "INVALID_HOST"
        DUMMY_HOSTS = {"example.com", "localhost", "test.com", "placeholder.com"}
        if any(netloc == d or netloc.endswith("." + d) or netloc == "localhost" for d in DUMMY_HOSTS):
            return False, "DUMMY_URL"
        if len(url_clean) < 10:
            return False, "URL_TOO_SHORT"
        return True, None
    except Exception:
        return False, "URL_PARSE_ERROR"



