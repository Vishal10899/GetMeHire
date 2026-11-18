from typing import List, Dict, Any
from app.discovery.connectors.base import BaseDiscoveryConnector, DiscoveredCompanyCandidate
from app.discovery.normalizer import clean_company_name, extract_canonical_domain

# Authentic global enterprises across all 20 target industries and all 9 global geographic regions
ENTERPRISES: List[Dict[str, Any]] = [
    # --- Aerospace ---
    {"name": "Lockheed Martin", "domain": "lockheedmartin.com", "country": "United States", "region": "North America", "industry": "Aerospace"},
    {"name": "Airbus", "domain": "airbus.com", "country": "France", "region": "Europe", "industry": "Aerospace"},
    {"name": "Boeing", "domain": "boeing.com", "country": "United States", "region": "North America", "industry": "Aerospace"},
    {"name": "Safran", "domain": "safran-group.com", "country": "France", "region": "Europe", "industry": "Aerospace"},
    {"name": "Embraer", "domain": "embraer.com", "country": "Brazil", "region": "South America", "industry": "Aerospace"},
    {"name": "Rolls-Royce", "domain": "rolls-royce.com", "country": "United Kingdom", "region": "Europe", "industry": "Aerospace"},

    # --- Automotive ---
    {"name": "Toyota", "domain": "toyota-global.com", "country": "Japan", "region": "Asia", "industry": "Automotive"},
    {"name": "Volkswagen", "domain": "volkswagen-group.com", "country": "Germany", "region": "Europe", "industry": "Automotive"},
    {"name": "BMW Group", "domain": "bmwgroup.com", "country": "Germany", "region": "Europe", "industry": "Automotive"},
    {"name": "Mercedes-Benz", "domain": "mercedes-benz.com", "country": "Germany", "region": "Europe", "industry": "Automotive"},
    {"name": "Hyundai Motor", "domain": "hyundai.com", "country": "South Korea", "region": "Asia", "industry": "Automotive"},
    {"name": "Tata Motors", "domain": "tatamotors.com", "country": "India", "region": "South Asia", "industry": "Automotive"},
    {"name": "Volvo Group", "domain": "volvogroup.com", "country": "Sweden", "region": "Europe", "industry": "Automotive"},

    # --- Biotechnology & Pharmaceuticals ---
    {"name": "Novartis", "domain": "novartis.com", "country": "Switzerland", "region": "Europe", "industry": "Biotechnology"},
    {"name": "Roche", "domain": "roche.com", "country": "Switzerland", "region": "Europe", "industry": "Biotechnology"},
    {"name": "Sanofi", "domain": "sanofi.com", "country": "France", "region": "Europe", "industry": "Biotechnology"},
    {"name": "CSL Behring", "domain": "csl.com", "country": "Australia", "region": "Oceania", "industry": "Biotechnology"},
    {"name": "Sun Pharma", "domain": "sunpharma.com", "country": "India", "region": "South Asia", "industry": "Healthcare & Pharmaceuticals"},
    {"name": "Takeda", "domain": "takeda.com", "country": "Japan", "region": "Asia", "industry": "Healthcare & Pharmaceuticals"},
    {"name": "Novo Nordisk", "domain": "novonordisk.com", "country": "Denmark", "region": "Europe", "industry": "Healthcare & Pharmaceuticals"},
    {"name": "Aspen Pharmacare", "domain": "aspenpharma.com", "country": "South Africa", "region": "Africa", "industry": "Healthcare & Pharmaceuticals"},

    # --- Construction & Infrastructure ---
    {"name": "Vinci", "domain": "vinci.com", "country": "France", "region": "Europe", "industry": "Construction & Infrastructure"},
    {"name": "Bouygues", "domain": "bouygues.com", "country": "France", "region": "Europe", "industry": "Construction & Infrastructure"},
    {"name": "ACS Group", "domain": "grupoacs.com", "country": "Spain", "region": "Europe", "industry": "Construction & Infrastructure"},
    {"name": "Skanska", "domain": "skanska.com", "country": "Sweden", "region": "Europe", "industry": "Construction & Infrastructure"},
    {"name": "Larsen & Toubro", "domain": "larsentoubro.com", "country": "India", "region": "South Asia", "industry": "Construction & Infrastructure"},
    {"name": "CIMIC Group", "domain": "cimic.com.au", "country": "Australia", "region": "Oceania", "industry": "Construction & Infrastructure"},
    {"name": "Orascom Construction", "domain": "orascom.com", "country": "Egypt", "region": "Middle East", "industry": "Construction & Infrastructure"},

    # --- Energy ---
    {"name": "TotalEnergies", "domain": "totalenergies.com", "country": "France", "region": "Europe", "industry": "Energy"},
    {"name": "Shell", "domain": "shell.com", "country": "United Kingdom", "region": "Europe", "industry": "Energy"},
    {"name": "BP", "domain": "bp.com", "country": "United Kingdom", "region": "Europe", "industry": "Energy"},
    {"name": "Enel", "domain": "enel.com", "country": "Italy", "region": "Europe", "industry": "Energy"},
    {"name": "Iberdrola", "domain": "iberdrola.com", "country": "Spain", "region": "Europe", "industry": "Energy"},
    {"name": "Equinor", "domain": "equinor.com", "country": "Norway", "region": "Europe", "industry": "Energy"},
    {"name": "Saudi Aramco", "domain": "aramco.com", "country": "Saudi Arabia", "region": "Middle East", "industry": "Energy"},
    {"name": "Petrobras", "domain": "petrobras.com.br", "country": "Brazil", "region": "South America", "industry": "Energy"},
    {"name": "Sasol", "domain": "sasol.com", "country": "South Africa", "region": "Africa", "industry": "Energy"},

    # --- Telecommunications ---
    {"name": "Deutsche Telekom", "domain": "telekom.com", "country": "Germany", "region": "Europe", "industry": "Telecommunications"},
    {"name": "Telstra", "domain": "telstra.com.au", "country": "Australia", "region": "Oceania", "industry": "Telecommunications"},
    {"name": "Singtel", "domain": "singtel.com", "country": "Singapore", "region": "Southeast Asia", "industry": "Telecommunications"},
    {"name": "Bharti Airtel", "domain": "airtel.in", "country": "India", "region": "South Asia", "industry": "Telecommunications"},
    {"name": "MTN Group", "domain": "mtn.com", "country": "South Africa", "region": "Africa", "industry": "Telecommunications"},
    {"name": "America Movil", "domain": "americamovil.com", "country": "Mexico", "region": "South America", "industry": "Telecommunications"},
    {"name": "e& (Etisalat)", "domain": "eand.com", "country": "United Arab Emirates", "region": "Middle East", "industry": "Telecommunications"},
    {"name": "NTT Docomo", "domain": "docomo.ne.jp", "country": "Japan", "region": "Asia", "industry": "Telecommunications"},

    # --- Logistics & Supply Chain ---
    {"name": "DHL Group", "domain": "dhl.com", "country": "Germany", "region": "Europe", "industry": "Logistics & Supply Chain"},
    {"name": "Kuehne+Nagel", "domain": "kuehne-nagel.com", "country": "Switzerland", "region": "Europe", "industry": "Logistics & Supply Chain"},
    {"name": "Maersk", "domain": "maersk.com", "country": "Denmark", "region": "Europe", "industry": "Logistics & Supply Chain"},
    {"name": "DP World", "domain": "dpworld.com", "country": "United Arab Emirates", "region": "Middle East", "industry": "Logistics & Supply Chain"},
    {"name": "Bollore Logistics", "domain": "bollore.com", "country": "France", "region": "Europe", "industry": "Logistics & Supply Chain"},
    {"name": "Brambles", "domain": "brambles.com", "country": "Australia", "region": "Oceania", "industry": "Logistics & Supply Chain"},

    # --- Hospitality ---
    {"name": "Accor", "domain": "group.accor.com", "country": "France", "region": "Europe", "industry": "Hospitality"},
    {"name": "InterContinental Hotels Group", "domain": "ihg.com", "country": "United Kingdom", "region": "Europe", "industry": "Hospitality"},
    {"name": "Marriott International", "domain": "marriott.com", "country": "United States", "region": "North America", "industry": "Hospitality"},
    {"name": "Jumeirah Group", "domain": "jumeirah.com", "country": "United Arab Emirates", "region": "Middle East", "industry": "Hospitality"},
    {"name": "Minor International", "domain": "minor.com", "country": "Thailand", "region": "Southeast Asia", "industry": "Hospitality"},

    # --- Media & Entertainment ---
    {"name": "Sony", "domain": "sony.com", "country": "Japan", "region": "Asia", "industry": "Media & Entertainment"},
    {"name": "Vivendi", "domain": "vivendi.com", "country": "France", "region": "Europe", "industry": "Media & Entertainment"},
    {"name": "Nintendo", "domain": "nintendo.co.jp", "country": "Japan", "region": "Asia", "industry": "Media & Entertainment"},
    {"name": "Bertelsmann", "domain": "bertelsmann.com", "country": "Germany", "region": "Europe", "industry": "Media & Entertainment"},
    {"name": "MultiChoice", "domain": "multichoice.com", "country": "South Africa", "region": "Africa", "industry": "Media & Entertainment"},

    # --- Government & Public Organizations ---
    {"name": "European Space Agency", "domain": "esa.int", "country": "France", "region": "Europe", "industry": "Government & Public"},
    {"name": "World Health Organization", "domain": "who.int", "country": "Switzerland", "region": "Europe", "industry": "Government & Public"},
    {"name": "United Nations Development Programme", "domain": "undp.org", "country": "United States", "region": "North America", "industry": "Government & Public"},
    {"name": "CSIRO", "domain": "csiro.au", "country": "Australia", "region": "Oceania", "industry": "Government & Public"},

    # --- Global Software & IT Leaders ---
    {"name": "SAP", "domain": "sap.com", "country": "Germany", "region": "Europe", "industry": "Software & IT"},
    {"name": "ASML", "domain": "asml.com", "country": "Netherlands", "region": "Europe", "industry": "Software & IT"},
    {"name": "Infosys", "domain": "infosys.com", "country": "India", "region": "South Asia", "industry": "Software & IT"},
    {"name": "Tata Consultancy Services", "domain": "tcs.com", "country": "India", "region": "South Asia", "industry": "Software & IT"},
    {"name": "Wipro", "domain": "wipro.com", "country": "India", "region": "South Asia", "industry": "Software & IT"},
    {"name": "HCLTech", "domain": "hcltech.com", "country": "India", "region": "South Asia", "industry": "Software & IT"},
    {"name": "Capgemini", "domain": "capgemini.com", "country": "France", "region": "Europe", "industry": "Software & IT"},
    {"name": "Dassault Systemes", "domain": "3ds.com", "country": "France", "region": "Europe", "industry": "Software & IT"},
    {"name": "Amadeus", "domain": "amadeus.com", "country": "Spain", "region": "Europe", "industry": "Software & IT"},
    {"name": "Globant", "domain": "globant.com", "country": "Argentina", "region": "South America", "industry": "Software & IT"},
    {"name": "Adyen", "domain": "adyen.com", "country": "Netherlands", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "TeamViewer", "domain": "teamviewer.com", "country": "Germany", "region": "Europe", "industry": "Software & IT"},

    # --- Global Finance & Banking Leaders ---
    {"name": "HSBC", "domain": "hsbc.com", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "BNP Paribas", "domain": "group.bnpparibas", "country": "France", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "Banco Santander", "domain": "santander.com", "country": "Spain", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "UBS", "domain": "ubs.com", "country": "Switzerland", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "Barclays", "domain": "barclays.com", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "Deutsche Bank", "domain": "db.com", "country": "Germany", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "ING Group", "domain": "ing.com", "country": "Netherlands", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "BBVA", "domain": "bbva.com", "country": "Spain", "region": "Europe", "industry": "Finance & Banking"},
    {"name": "HDFC Bank", "domain": "hdfcbank.com", "country": "India", "region": "South Asia", "industry": "Finance & Banking"},
    {"name": "ICICI Bank", "domain": "icicibank.com", "country": "India", "region": "South Asia", "industry": "Finance & Banking"},
    {"name": "DBS Bank", "domain": "dbs.com", "country": "Singapore", "region": "Southeast Asia", "industry": "Finance & Banking"},
    {"name": "Commonwealth Bank of Australia", "domain": "commbank.com.au", "country": "Australia", "region": "Oceania", "industry": "Finance & Banking"},
    {"name": "National Australia Bank", "domain": "nab.com.au", "country": "Australia", "region": "Oceania", "industry": "Finance & Banking"},
    {"name": "Westpac", "domain": "westpac.com.au", "country": "Australia", "region": "Oceania", "industry": "Finance & Banking"},
    {"name": "ANZ Banking Group", "domain": "anz.com.au", "country": "Australia", "region": "Oceania", "industry": "Finance & Banking"},
    {"name": "Itau Unibanco", "domain": "itau.com.br", "country": "Brazil", "region": "South America", "industry": "Finance & Banking"},
    {"name": "Standard Bank", "domain": "standardbank.com", "country": "South Africa", "region": "Africa", "industry": "Finance & Banking"},
    {"name": "FirstRand", "domain": "firstrand.co.za", "country": "South Africa", "region": "Africa", "industry": "Finance & Banking"},

    # --- Global E-commerce, Retail & Consumer ---
    {"name": "Inditex (Zara)", "domain": "inditex.com", "country": "Spain", "region": "Europe", "industry": "E-commerce & Retail"},
    {"name": "H&M Group", "domain": "hmgroup.com", "country": "Sweden", "region": "Europe", "industry": "E-commerce & Retail"},
    {"name": "LVMH", "domain": "lvmh.com", "country": "France", "region": "Europe", "industry": "E-commerce & Retail"},
    {"name": "Kering", "domain": "kering.com", "country": "France", "region": "Europe", "industry": "E-commerce & Retail"},
    {"name": "Fast Retailing (Uniqlo)", "domain": "fastretailing.com", "country": "Japan", "region": "Asia", "industry": "E-commerce & Retail"},
    {"name": "Rakuten", "domain": "rakuten.com", "country": "Japan", "region": "Asia", "industry": "E-commerce & Retail"},
    {"name": "Woolworths Group", "domain": "woolworthsgroup.com.au", "country": "Australia", "region": "Oceania", "industry": "E-commerce & Retail"},
    {"name": "Wesfarmers", "domain": "wesfarmers.com.au", "country": "Australia", "region": "Oceania", "industry": "E-commerce & Retail"},

    # --- Global Manufacturing & Semiconductor ---
    {"name": "BASF", "domain": "basf.com", "country": "Germany", "region": "Europe", "industry": "Manufacturing"},
    {"name": "Bayer", "domain": "bayer.com", "country": "Germany", "region": "Europe", "industry": "Manufacturing"},
    {"name": "Thyssenkrupp", "domain": "thyssenkrupp.com", "country": "Germany", "region": "Europe", "industry": "Manufacturing"},
    {"name": "Saint-Gobain", "domain": "saint-gobain.com", "country": "France", "region": "Europe", "industry": "Manufacturing"},
    {"name": "TSMC", "domain": "tsmc.com", "country": "Taiwan", "region": "Asia", "industry": "Manufacturing"},
    {"name": "Samsung Electronics", "domain": "samsung.com", "country": "South Korea", "region": "Asia", "industry": "Manufacturing"},
    {"name": "LG Electronics", "domain": "lg.com", "country": "South Korea", "region": "Asia", "industry": "Manufacturing"},
    {"name": "Panasonic", "domain": "panasonic.com", "country": "Japan", "region": "Asia", "industry": "Manufacturing"},
    {"name": "Hitachi", "domain": "hitachi.com", "country": "Japan", "region": "Asia", "industry": "Manufacturing"},
    {"name": "Komatsu", "domain": "komatsu.com", "country": "Japan", "region": "Asia", "industry": "Manufacturing"},
    {"name": "Daikin", "domain": "daikin.com", "country": "Japan", "region": "Asia", "industry": "Manufacturing"},

    # --- Consulting, Legal & Professional Services ---
    {"name": "Deloitte", "domain": "deloitte.com", "country": "United States", "region": "North America", "industry": "Consulting"},
    {"name": "PwC", "domain": "pwc.com", "country": "United Kingdom", "region": "Europe", "industry": "Consulting"},
    {"name": "Ernst & Young (EY)", "domain": "ey.com", "country": "United Kingdom", "region": "Europe", "industry": "Consulting"},
    {"name": "KPMG", "domain": "kpmg.com", "country": "Netherlands", "region": "Europe", "industry": "Consulting"},
    {"name": "Accenture Global", "domain": "accenture.com", "country": "Ireland", "region": "Europe", "industry": "Consulting"},
    {"name": "Clifford Chance", "domain": "cliffordchance.com", "country": "United Kingdom", "region": "Europe", "industry": "Legal and Professional Services"},
    {"name": "Baker McKenzie", "domain": "bakermckenzie.com", "country": "United States", "region": "North America", "industry": "Legal and Professional Services"},
    {"name": "Linklaters", "domain": "linklaters.com", "country": "United Kingdom", "region": "Europe", "industry": "Legal and Professional Services"},
    {"name": "DLA Piper", "domain": "dlapiper.com", "country": "United States", "region": "North America", "industry": "Legal and Professional Services"},

    # --- Marketing & Advertising ---
    {"name": "WPP", "domain": "wpp.com", "country": "United Kingdom", "region": "Europe", "industry": "Marketing and Advertising"},
    {"name": "Publicis Groupe", "domain": "publicisgroupe.com", "country": "France", "region": "Europe", "industry": "Marketing and Advertising"},
    {"name": "Omnicom Group", "domain": "omnicomgroup.com", "country": "United States", "region": "North America", "industry": "Marketing and Advertising"},
    {"name": "Dentsu", "domain": "dentsu.com", "country": "Japan", "region": "Asia", "industry": "Marketing and Advertising"},
    {"name": "Interpublic Group", "domain": "interpublic.com", "country": "United States", "region": "North America", "industry": "Marketing and Advertising"},

    # --- Energy & Utilities ---
    {"name": "Orsted", "domain": "orsted.com", "country": "Denmark", "region": "Europe", "industry": "Energy"},
    {"name": "EDP (Energias de Portugal)", "domain": "edp.com", "country": "Portugal", "region": "Europe", "industry": "Energy"},
    {"name": "E.ON", "domain": "eon.com", "country": "Germany", "region": "Europe", "industry": "Energy"},
    {"name": "RWE", "domain": "rwe.com", "country": "Germany", "region": "Europe", "industry": "Energy"},
    {"name": "SSE", "domain": "sse.com", "country": "United Kingdom", "region": "Europe", "industry": "Energy"},
    {"name": "Fortum", "domain": "fortum.com", "country": "Finland", "region": "Europe", "industry": "Energy"},
    {"name": "NTPC", "domain": "ntpc.co.in", "country": "India", "region": "South Asia", "industry": "Energy"},
    {"name": "Woodside Energy", "domain": "woodside.com", "country": "Australia", "region": "Oceania", "industry": "Energy"},
    {"name": "Origin Energy", "domain": "originenergy.com.au", "country": "Australia", "region": "Oceania", "industry": "Energy"},
]

class GlobalEnterpriseConnector(BaseDiscoveryConnector):
    """
    Ingests authentic global market leaders and public institutions across all 20 target industries
    and 9 global geographic regions.
    """

    @property
    def source_name(self) -> str:
        return "Global Enterprise Directory"

    def discover(self, limit: int = 1000) -> List[DiscoveredCompanyCandidate]:
        candidates = []
        for ent in ENTERPRISES[:limit]:
            canonical = clean_company_name(ent["name"])
            domain = ent.get("domain")

            candidate = DiscoveredCompanyCandidate(
                name=canonical,
                domain=domain,
                website=f"https://{domain}" if domain else None,
                career_page_url=f"https://{domain}/careers" if domain else None,
                country=ent.get("country", "United States"),
                operating_region=ent.get("region", "Global"),
                industry=ent.get("industry", "Software & IT"),
                discovery_source="GLOBAL_ENTERPRISE_REGISTRY",
                aliases=[ent["name"]] if ent["name"] != canonical else [],
                metadata={"type": "global_enterprise"}
            )
            candidates.append(candidate)

        return candidates
