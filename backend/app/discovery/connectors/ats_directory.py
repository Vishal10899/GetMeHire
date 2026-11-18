from typing import List, Dict, Any
from app.discovery.connectors.base import BaseDiscoveryConnector, DiscoveredCompanyCandidate
from app.discovery.normalizer import clean_company_name, extract_canonical_domain

# Authentic international employers with verified public ATS platforms across all 20 target industries and all 9 global geographic regions
GLOBAL_ATS_COMPANIES: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. NORTH AMERICA
    # =========================================================================
    # Software & IT / Data Science & AI
    {"name": "GitLab", "ats": "GREENHOUSE", "board": "gitlab", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "gitlab.com"},
    {"name": "HashiCorp", "ats": "GREENHOUSE", "board": "hashicorp", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "hashicorp.com"},
    {"name": "Zapier", "ats": "GREENHOUSE", "board": "zapier", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "zapier.com"},
    {"name": "Automattic", "ats": "GREENHOUSE", "board": "automattic", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "automattic.com"},
    {"name": "Notion", "ats": "GREENHOUSE", "board": "notion", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "notion.so"},
    {"name": "Vercel", "ats": "GREENHOUSE", "board": "vercel", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "vercel.com"},
    {"name": "Datadog", "ats": "GREENHOUSE", "board": "datadog", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "datadoghq.com"},
    {"name": "Cloudflare", "ats": "GREENHOUSE", "board": "cloudflare", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "cloudflare.com"},
    {"name": "Figma", "ats": "GREENHOUSE", "board": "figma", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "figma.com"},
    {"name": "Discord", "ats": "GREENHOUSE", "board": "discord", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "discord.com"},
    {"name": "Reddit", "ats": "GREENHOUSE", "board": "reddit", "country": "United States", "region": "North America", "industry": "Software & IT", "domain": "reddit.com"},
    {"name": "Weights & Biases", "ats": "GREENHOUSE", "board": "wandb", "country": "United States", "region": "North America", "industry": "Data Science & AI", "domain": "wandb.ai"},
    {"name": "Coactive AI", "ats": "ASHBY", "board": "coactiveai", "country": "United States", "region": "North America", "industry": "Data Science & AI", "domain": "coactive.ai"},
    {"name": "Snorkel AI", "ats": "GREENHOUSE", "board": "snorkelai", "country": "United States", "region": "North America", "industry": "Data Science & AI", "domain": "snorkel.ai"},
    {"name": "Cohere", "ats": "LEVER", "board": "cohere", "country": "Canada", "region": "North America", "industry": "Data Science & AI", "domain": "cohere.com"},
    {"name": "1Password", "ats": "LEVER", "board": "1password", "country": "Canada", "region": "North America", "industry": "Software & IT", "domain": "1password.com"},
    {"name": "Wealthsimple", "ats": "GREENHOUSE", "board": "wealthsimple", "country": "Canada", "region": "North America", "industry": "Finance & Banking", "domain": "wealthsimple.com"},
    {"name": "Hootsuite", "ats": "GREENHOUSE", "board": "hootsuite", "country": "Canada", "region": "North America", "industry": "Marketing & Advertising", "domain": "hootsuite.com"},

    # Finance & Banking
    {"name": "Coinbase", "ats": "GREENHOUSE", "board": "coinbase", "country": "United States", "region": "North America", "industry": "Finance & Banking", "domain": "coinbase.com"},
    {"name": "Brex", "ats": "GREENHOUSE", "board": "brex", "country": "United States", "region": "North America", "industry": "Finance & Banking", "domain": "brex.com"},
    {"name": "Affirm", "ats": "GREENHOUSE", "board": "affirm", "country": "United States", "region": "North America", "industry": "Finance & Banking", "domain": "affirm.com"},

    # Healthcare & Biotechnology
    {"name": "Ro", "ats": "GREENHOUSE", "board": "ro", "country": "United States", "region": "North America", "industry": "Healthcare & Pharmaceuticals", "domain": "ro.co"},
    {"name": "Color Health", "ats": "GREENHOUSE", "board": "color", "country": "United States", "region": "North America", "industry": "Healthcare & Pharmaceuticals", "domain": "color.com"},
    {"name": "Oscar Health", "ats": "GREENHOUSE", "board": "oscar", "country": "United States", "region": "North America", "industry": "Healthcare & Pharmaceuticals", "domain": "hioscar.com"},
    {"name": "Recursion", "ats": "GREENHOUSE", "board": "recursion", "country": "United States", "region": "North America", "industry": "Biotechnology", "domain": "recursion.com"},

    # E-commerce, Retail & Logistics
    {"name": "Shopify", "ats": "SMARTRECRUITERS", "board": "shopify", "country": "Canada", "region": "North America", "industry": "E-commerce & Retail", "domain": "shopify.com"},
    {"name": "Faire", "ats": "GREENHOUSE", "board": "faire", "country": "United States", "region": "North America", "industry": "E-commerce & Retail", "domain": "faire.com"},
    {"name": "Etsy", "ats": "GREENHOUSE", "board": "etsy", "country": "United States", "region": "North America", "industry": "E-commerce & Retail", "domain": "etsy.com"},
    {"name": "DoorDash", "ats": "GREENHOUSE", "board": "doordash", "country": "United States", "region": "North America", "industry": "Logistics & Supply Chain", "domain": "doordash.com"},
    {"name": "Flexport", "ats": "GREENHOUSE", "board": "flexport", "country": "United States", "region": "North America", "industry": "Logistics & Supply Chain", "domain": "flexport.com"},

    # Automotive, Aerospace & Energy
    {"name": "Rivian", "ats": "GREENHOUSE", "board": "rivian", "country": "United States", "region": "North America", "industry": "Automotive", "domain": "rivian.com"},
    {"name": "Lucid Motors", "ats": "GREENHOUSE", "board": "lucidmotors", "country": "United States", "region": "North America", "industry": "Automotive", "domain": "lucidmotors.com"},
    {"name": "Relativity Space", "ats": "GREENHOUSE", "board": "relativityspace", "country": "United States", "region": "North America", "industry": "Aerospace", "domain": "relativityspace.com"},
    {"name": "Astra", "ats": "GREENHOUSE", "board": "astra", "country": "United States", "region": "North America", "industry": "Aerospace", "domain": "astra.com"},
    {"name": "Enphase Energy", "ats": "GREENHOUSE", "board": "enphaseenergy", "country": "United States", "region": "North America", "industry": "Energy", "domain": "enphase.com"},

    # Education, Hospitality, Media & Consulting
    {"name": "Udemy", "ats": "GREENHOUSE", "board": "udemy", "country": "United States", "region": "North America", "industry": "Education", "domain": "udemy.com"},
    {"name": "Khan Academy", "ats": "GREENHOUSE", "board": "khanacademy", "country": "United States", "region": "North America", "industry": "Education", "domain": "khanacademy.org"},
    {"name": "Quizlet", "ats": "GREENHOUSE", "board": "quizlet", "country": "United States", "region": "North America", "industry": "Education", "domain": "quizlet.com"},
    {"name": "Riot Games", "ats": "GREENHOUSE", "board": "riotgames", "country": "United States", "region": "North America", "industry": "Media & Entertainment", "domain": "riotgames.com"},
    {"name": "Epic Games", "ats": "GREENHOUSE", "board": "epicgames", "country": "United States", "region": "North America", "industry": "Media & Entertainment", "domain": "epicgames.com"},
    {"name": "Unity", "ats": "GREENHOUSE", "board": "unity3d", "country": "United States", "region": "North America", "industry": "Media & Entertainment", "domain": "unity.com"},
    {"name": "Slalom", "ats": "GREENHOUSE", "board": "slalom", "country": "United States", "region": "North America", "industry": "Consulting", "domain": "slalom.com"},
    {"name": "Sonder", "ats": "GREENHOUSE", "board": "sonder", "country": "United States", "region": "North America", "industry": "Hospitality", "domain": "sonder.com"},

    # =========================================================================
    # 2. EUROPE
    # =========================================================================
    {"name": "Revolut", "ats": "LEVER", "board": "revolut", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking", "domain": "revolut.com"},
    {"name": "Wise", "ats": "SMARTRECRUITERS", "board": "transferwise", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking", "domain": "wise.com"},
    {"name": "Monzo", "ats": "GREENHOUSE", "board": "monzo", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking", "domain": "monzo.com"},
    {"name": "Checkout.com", "ats": "GREENHOUSE", "board": "checkout", "country": "United Kingdom", "region": "Europe", "industry": "Finance & Banking", "domain": "checkout.com"},
    {"name": "N26", "ats": "GREENHOUSE", "board": "n26", "country": "Germany", "region": "Europe", "industry": "Finance & Banking", "domain": "n26.com"},
    {"name": "Klarna", "ats": "SMARTRECRUITERS", "board": "klarna", "country": "Sweden", "region": "Europe", "industry": "Finance & Banking", "domain": "klarna.com"},
    {"name": "Spotify", "ats": "LEVER", "board": "spotify", "country": "Sweden", "region": "Europe", "industry": "Media & Entertainment", "domain": "spotify.com"},
    {"name": "Deezer", "ats": "SMARTRECRUITERS", "board": "deezer", "country": "France", "region": "Europe", "industry": "Media & Entertainment", "domain": "deezer.com"},
    {"name": "Hugging Face", "ats": "LEVER", "board": "huggingface", "country": "France", "region": "Europe", "industry": "Data Science & AI", "domain": "huggingface.co"},
    {"name": "Mistral AI", "ats": "ASHBY", "board": "mistralai", "country": "France", "region": "Europe", "industry": "Data Science & AI", "domain": "mistral.ai"},
    {"name": "Zalando", "ats": "SMARTRECRUITERS", "board": "zalando", "country": "Germany", "region": "Europe", "industry": "E-commerce & Retail", "domain": "zalando.com"},
    {"name": "Delivery Hero", "ats": "GREENHOUSE", "board": "deliveryhero", "country": "Germany", "region": "Europe", "industry": "Logistics & Supply Chain", "domain": "deliveryhero.com"},
    {"name": "Bolt", "ats": "GREENHOUSE", "board": "bolt", "country": "Estonia", "region": "Europe", "industry": "Logistics & Supply Chain", "domain": "bolt.eu"},
    {"name": "BioNTech", "ats": "PERSONIO", "board": "biontech", "country": "Germany", "region": "Europe", "industry": "Healthcare & Pharmaceuticals", "domain": "biontech.de"},
    {"name": "Babbel", "ats": "PERSONIO", "board": "babbel", "country": "Germany", "region": "Europe", "industry": "Education", "domain": "babbel.com"},
    {"name": "Personio", "ats": "PERSONIO", "board": "personio", "country": "Germany", "region": "Europe", "industry": "Software & IT", "domain": "personio.com"},
    {"name": "Schneider Electric", "ats": "SMARTRECRUITERS", "board": "schneiderelectric", "country": "France", "region": "Europe", "industry": "Manufacturing", "domain": "se.com"},
    {"name": "ABB", "ats": "SMARTRECRUITERS", "board": "abb", "country": "Switzerland", "region": "Europe", "industry": "Manufacturing", "domain": "abb.com"},
    {"name": "Northvolt", "ats": "TEAMTAILOR", "board": "northvolt", "country": "Sweden", "region": "Europe", "industry": "Automotive", "domain": "northvolt.com"},
    {"name": "Kry", "ats": "TEAMTAILOR", "board": "kry", "country": "Sweden", "region": "Europe", "industry": "Healthcare & Pharmaceuticals", "domain": "kry.se"},
    {"name": "Vodafone", "ats": "SMARTRECRUITERS", "board": "vodafone", "country": "United Kingdom", "region": "Europe", "industry": "Telecommunications", "domain": "vodafone.com"},
    {"name": "Orange", "ats": "SMARTRECRUITERS", "board": "orange", "country": "France", "region": "Europe", "industry": "Telecommunications", "domain": "orange.com"},
    {"name": "Telefonica", "ats": "SMARTRECRUITERS", "board": "telefonica", "country": "Spain", "region": "Europe", "industry": "Telecommunications", "domain": "telefonica.com"},
    {"name": "Sinch", "ats": "SMARTRECRUITERS", "board": "sinch", "country": "Sweden", "region": "Europe", "industry": "Telecommunications", "domain": "sinch.com"},
    {"name": "Capgemini", "ats": "SMARTRECRUITERS", "board": "capgemini", "country": "France", "region": "Europe", "industry": "Consulting", "domain": "capgemini.com"},
    {"name": "Vestas", "ats": "SMARTRECRUITERS", "board": "vestas", "country": "Denmark", "region": "Europe", "industry": "Energy", "domain": "vestas.com"},
    {"name": "Trustpilot", "ats": "GREENHOUSE", "board": "trustpilot", "country": "Denmark", "region": "Europe", "industry": "Software & IT", "domain": "trustpilot.com"},
    {"name": "Miro", "ats": "GREENHOUSE", "board": "miro", "country": "Netherlands", "region": "Europe", "industry": "Software & IT", "domain": "miro.com"},
    {"name": "Doctolib", "ats": "GREENHOUSE", "board": "doctolib", "country": "France", "region": "Europe", "industry": "Healthcare & Pharmaceuticals", "domain": "doctolib.fr"},

    # =========================================================================
    # 3. SOUTH ASIA & INDIA HIRING
    # =========================================================================
    {"name": "Swiggy", "ats": "SMARTRECRUITERS", "board": "swiggy", "country": "India", "region": "South Asia", "industry": "Logistics & Supply Chain", "domain": "swiggy.com"},
    {"name": "Freshworks", "ats": "SMARTRECRUITERS", "board": "freshworks", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "freshworks.com"},
    {"name": "Thoughtworks", "ats": "GREENHOUSE", "board": "thoughtworks", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "thoughtworks.com"},
    {"name": "Rubrik", "ats": "GREENHOUSE", "board": "rubrik", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "rubrik.com"},
    {"name": "Razorpay", "ats": "GREENHOUSE", "board": "razorpaysoftwareprivatelimited", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "razorpay.com"},
    {"name": "Groww", "ats": "GREENHOUSE", "board": "groww", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "groww.in"},
    {"name": "InMobi", "ats": "GREENHOUSE", "board": "inmobi", "country": "India", "region": "South Asia", "industry": "Marketing & Advertising", "domain": "inmobi.com"},
    {"name": "Postman", "ats": "BAMBOOHR", "board": "postman", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "postman.com"},
    {"name": "PhonePe", "ats": "SMARTRECRUITERS", "board": "phonepe", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "phonepe.com"},
    {"name": "Zomato", "ats": "SMARTRECRUITERS", "board": "zomato", "country": "India", "region": "South Asia", "industry": "Logistics & Supply Chain", "domain": "zomato.com"},
    {"name": "Zepto", "ats": "SMARTRECRUITERS", "board": "zepto", "country": "India", "region": "South Asia", "industry": "Logistics & Supply Chain", "domain": "zeptonow.com"},
    {"name": "Blinkit", "ats": "SMARTRECRUITERS", "board": "blinkit", "country": "India", "region": "South Asia", "industry": "Logistics & Supply Chain", "domain": "blinkit.com"},
    {"name": "BrowserStack", "ats": "SMARTRECRUITERS", "board": "browserstack", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "browserstack.com"},
    {"name": "Dream11", "ats": "SMARTRECRUITERS", "board": "dream11", "country": "India", "region": "South Asia", "industry": "Media & Entertainment", "domain": "dream11.com"},
    {"name": "Pine Labs", "ats": "SMARTRECRUITERS", "board": "pinelabs", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "pinelabs.com"},
    {"name": "Juspay", "ats": "SMARTRECRUITERS", "board": "juspay", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "juspay.in"},
    {"name": "Chargebee", "ats": "SMARTRECRUITERS", "board": "chargebee", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "chargebee.com"},
    {"name": "CleverTap", "ats": "SMARTRECRUITERS", "board": "clevertap", "country": "India", "region": "South Asia", "industry": "Marketing & Advertising", "domain": "clevertap.com"},
    {"name": "Ather Energy", "ats": "SMARTRECRUITERS", "board": "atherenergy", "country": "India", "region": "South Asia", "industry": "Automotive", "domain": "atherenergy.com"},
    {"name": "Navi", "ats": "SMARTRECRUITERS", "board": "navi", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "navi.com"},
    {"name": "MakeMyTrip", "ats": "SMARTRECRUITERS", "board": "makemytrip", "country": "India", "region": "South Asia", "industry": "Hospitality", "domain": "makemytrip.com"},
    {"name": "Paytm", "ats": "SMARTRECRUITERS", "board": "paytm", "country": "India", "region": "South Asia", "industry": "Finance & Banking", "domain": "paytm.com"},
    {"name": "Meesho", "ats": "SMARTRECRUITERS", "board": "meesho", "country": "India", "region": "South Asia", "industry": "E-commerce & Retail", "domain": "meesho.io"},
    {"name": "HackerRank", "ats": "GREENHOUSE", "board": "hackerrank", "country": "India", "region": "South Asia", "industry": "Software & IT", "domain": "hackerrank.com"},

    # =========================================================================
    # 4. EAST ASIA
    # =========================================================================
    {"name": "Coupang", "ats": "GREENHOUSE", "board": "coupang", "country": "South Korea", "region": "East Asia", "industry": "E-commerce & Retail", "domain": "coupang.com"},
    {"name": "Mercari", "ats": "GREENHOUSE", "board": "mercari", "country": "Japan", "region": "East Asia", "industry": "E-commerce & Retail", "domain": "mercari.com"},
    {"name": "Sendbird", "ats": "GREENHOUSE", "board": "sendbird", "country": "South Korea", "region": "East Asia", "industry": "Software & IT", "domain": "sendbird.com"},
    {"name": "SmartNews", "ats": "GREENHOUSE", "board": "smartnews", "country": "Japan", "region": "East Asia", "industry": "Media & Entertainment", "domain": "smartnews.com"},
    {"name": "Appier", "ats": "LEVER", "board": "appier", "country": "Taiwan", "region": "East Asia", "industry": "Data Science & AI", "domain": "appier.com"},
    {"name": "Kakao Pay", "ats": "GREENHOUSE", "board": "kakaopay", "country": "South Korea", "region": "East Asia", "industry": "Finance & Banking", "domain": "kakaopay.com"},
    {"name": "Rakuten Travel", "ats": "SMARTRECRUITERS", "board": "rakuten", "country": "Japan", "region": "East Asia", "industry": "Hospitality", "domain": "rakuten.com"},

    # =========================================================================
    # 5. SOUTHEAST ASIA
    # =========================================================================
    {"name": "Supabase", "ats": "ASHBY", "board": "supabase", "country": "Singapore", "region": "Southeast Asia", "industry": "Software & IT", "domain": "supabase.com"},
    {"name": "Grab", "ats": "GREENHOUSE", "board": "grab", "country": "Singapore", "region": "Southeast Asia", "industry": "Logistics & Supply Chain", "domain": "grab.com"},
    {"name": "Sea Limited", "ats": "GREENHOUSE", "board": "sea", "country": "Singapore", "region": "Southeast Asia", "industry": "E-commerce & Retail", "domain": "sea.com"},
    {"name": "Gojek", "ats": "GREENHOUSE", "board": "gojek", "country": "Indonesia", "region": "Southeast Asia", "industry": "Logistics & Supply Chain", "domain": "gojek.com"},
    {"name": "Traveloka", "ats": "GREENHOUSE", "board": "traveloka", "country": "Indonesia", "region": "Southeast Asia", "industry": "Hospitality", "domain": "traveloka.com"},
    {"name": "Carousell", "ats": "GREENHOUSE", "board": "carousell", "country": "Singapore", "region": "Southeast Asia", "industry": "E-commerce & Retail", "domain": "carousell.com"},
    {"name": "Ninja Van", "ats": "GREENHOUSE", "board": "ninjavan", "country": "Singapore", "region": "Southeast Asia", "industry": "Logistics & Supply Chain", "domain": "ninjavan.co"},
    {"name": "PropertyGuru", "ats": "GREENHOUSE", "board": "propertyguru", "country": "Singapore", "region": "Southeast Asia", "industry": "Construction & Infrastructure", "domain": "propertygurugroup.com"},

    # =========================================================================
    # 6. MIDDLE EAST
    # =========================================================================
    {"name": "Careem", "ats": "GREENHOUSE", "board": "careem", "country": "United Arab Emirates", "region": "Middle East", "industry": "Logistics & Supply Chain", "domain": "careem.com"},
    {"name": "Tabby", "ats": "GREENHOUSE", "board": "tabby", "country": "United Arab Emirates", "region": "Middle East", "industry": "Finance & Banking", "domain": "tabby.ai"},
    {"name": "Tamara", "ats": "GREENHOUSE", "board": "tamara", "country": "Saudi Arabia", "region": "Middle East", "industry": "Finance & Banking", "domain": "tamara.co"},
    {"name": "Getir", "ats": "GREENHOUSE", "board": "getir", "country": "Turkey", "region": "Middle East", "industry": "Logistics & Supply Chain", "domain": "getir.com"},
    {"name": "Monday.com", "ats": "GREENHOUSE", "board": "monday", "country": "Israel", "region": "Middle East", "industry": "Software & IT", "domain": "monday.com"},
    {"name": "Wiz", "ats": "GREENHOUSE", "board": "wiz", "country": "Israel", "region": "Middle East", "industry": "Software & IT", "domain": "wiz.io"},
    {"name": "Gong", "ats": "GREENHOUSE", "board": "gong", "country": "Israel", "region": "Middle East", "industry": "Data Science & AI", "domain": "gong.io"},
    {"name": "AppsFlyer", "ats": "GREENHOUSE", "board": "appsflyer", "country": "Israel", "region": "Middle East", "industry": "Marketing & Advertising", "domain": "appsflyer.com"},
    {"name": "Anghami", "ats": "BAMBOOHR", "board": "anghami", "country": "United Arab Emirates", "region": "Middle East", "industry": "Media & Entertainment", "domain": "anghami.com"},
    {"name": "Fawry", "ats": "BAMBOOHR", "board": "fawry", "country": "Egypt", "region": "Middle East", "industry": "Finance & Banking", "domain": "fawry.com"},

    # =========================================================================
    # 7. AFRICA
    # =========================================================================
    {"name": "Flutterwave", "ats": "BAMBOOHR", "board": "flutterwave", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "flutterwave.com"},
    {"name": "Chipper Cash", "ats": "GREENHOUSE", "board": "chippercash", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "chippercash.com"},
    {"name": "Paystack", "ats": "GREENHOUSE", "board": "paystack", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "paystack.com"},
    {"name": "Andela", "ats": "GREENHOUSE", "board": "andela", "country": "Nigeria", "region": "Africa", "industry": "Software & IT", "domain": "andela.com"},
    {"name": "Moniepoint", "ats": "GREENHOUSE", "board": "moniepoint", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "moniepoint.com"},
    {"name": "OPay", "ats": "GREENHOUSE", "board": "opay", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "opayweb.com"},
    {"name": "Kuda Bank", "ats": "BAMBOOHR", "board": "kuda", "country": "Nigeria", "region": "Africa", "industry": "Finance & Banking", "domain": "kuda.com"},
    {"name": "M-KOPA", "ats": "BAMBOOHR", "board": "mkopa", "country": "Kenya", "region": "Africa", "industry": "Energy", "domain": "m-kopa.com"},
    {"name": "Wasoko", "ats": "BAMBOOHR", "board": "wasoko", "country": "Kenya", "region": "Africa", "industry": "E-commerce & Retail", "domain": "wasoko.com"},
    {"name": "Jumia", "ats": "SMARTRECRUITERS", "board": "jumia", "country": "Nigeria", "region": "Africa", "industry": "E-commerce & Retail", "domain": "jumia.com"},
    {"name": "Takealot", "ats": "BAMBOOHR", "board": "takealot", "country": "South Africa", "region": "Africa", "industry": "E-commerce & Retail", "domain": "takealot.com"},

    # =========================================================================
    # 8. SOUTH AMERICA
    # =========================================================================
    {"name": "Nubank", "ats": "GREENHOUSE", "board": "nubank", "country": "Brazil", "region": "South America", "industry": "Finance & Banking", "domain": "nubank.com.br"},
    {"name": "Rappi", "ats": "GREENHOUSE", "board": "rappi", "country": "Colombia", "region": "South America", "industry": "Logistics & Supply Chain", "domain": "rappi.com"},
    {"name": "QuintoAndar", "ats": "GREENHOUSE", "board": "quintoandar", "country": "Brazil", "region": "South America", "industry": "Construction & Infrastructure", "domain": "quintoandar.com.br"},
    {"name": "Loft", "ats": "GREENHOUSE", "board": "loft", "country": "Brazil", "region": "South America", "industry": "Construction & Infrastructure", "domain": "loft.com.br"},
    {"name": "Kavak", "ats": "GREENHOUSE", "board": "kavak", "country": "Mexico", "region": "South America", "industry": "Automotive", "domain": "kavak.com"},
    {"name": "Wildlife Studios", "ats": "GREENHOUSE", "board": "wildlifestudios", "country": "Brazil", "region": "South America", "industry": "Media & Entertainment", "domain": "wildlifestudios.com"},
    {"name": "Clip", "ats": "GREENHOUSE", "board": "clip", "country": "Mexico", "region": "South America", "industry": "Finance & Banking", "domain": "clip.mx"},
    {"name": "dLocal", "ats": "GREENHOUSE", "board": "dlocal", "country": "Uruguay", "region": "South America", "industry": "Finance & Banking", "domain": "dlocal.com"},
    {"name": "Betterfly", "ats": "GREENHOUSE", "board": "betterfly", "country": "Chile", "region": "South America", "industry": "Healthcare & Pharmaceuticals", "domain": "betterfly.com"},
    {"name": "NotCo", "ats": "GREENHOUSE", "board": "notco", "country": "Chile", "region": "South America", "industry": "Manufacturing", "domain": "notco.com"},

    # =========================================================================
    # 9. OCEANIA
    # =========================================================================
    {"name": "Atlassian", "ats": "GREENHOUSE", "board": "atlassian", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "atlassian.com"},
    {"name": "Canva", "ats": "GREENHOUSE", "board": "canva", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "canva.com"},
    {"name": "SafetyCulture", "ats": "GREENHOUSE", "board": "safetyculture", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "safetyculture.com"},
    {"name": "Culture Amp", "ats": "GREENHOUSE", "board": "cultureamp", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "cultureamp.com"},
    {"name": "Employment Hero", "ats": "LEVER", "board": "employmenthero", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "employmenthero.com"},
    {"name": "Xero", "ats": "GREENHOUSE", "board": "xero", "country": "New Zealand", "region": "Oceania", "industry": "Finance & Banking", "domain": "xero.com"},
    {"name": "Airwallex", "ats": "GREENHOUSE", "board": "airwallex", "country": "Australia", "region": "Oceania", "industry": "Finance & Banking", "domain": "airwallex.com"},
    {"name": "Rokt", "ats": "GREENHOUSE", "board": "rokt", "country": "Australia", "region": "Oceania", "industry": "Marketing & Advertising", "domain": "rokt.com"},
    {"name": "Linktree", "ats": "GREENHOUSE", "board": "linktree", "country": "Australia", "region": "Oceania", "industry": "Media & Entertainment", "domain": "linktr.ee"},
    {"name": "Deputy", "ats": "GREENHOUSE", "board": "deputy", "country": "Australia", "region": "Oceania", "industry": "Software & IT", "domain": "deputy.com"},
]

class PublicAtsDirectoryConnector(BaseDiscoveryConnector):
    """
    Ingests authentic global companies known to operate publicly-accessible career feeds
    across Greenhouse, Lever, Ashby, SmartRecruiters, Personio, Workable, BambooHR, Teamtailor, Recruitee, Breezy HR.
    """

    @property
    def source_name(self) -> str:
        return "Public ATS Board Directory"

    def discover(self, limit: int = 1000) -> List[DiscoveredCompanyCandidate]:
        candidates = []
        for c in GLOBAL_ATS_COMPANIES[:limit]:
            canonical_name = clean_company_name(c["name"])
            domain = c.get("domain") or extract_canonical_domain(f"https://{c['name'].lower().replace(' ', '')}.com")

            # Determine official career page URL and feed URL from ATS provider
            ats = c["ats"]
            board = c["board"]
            career_url = None
            if ats == "GREENHOUSE":
                career_url = f"https://boards.greenhouse.io/{board}"
            elif ats == "LEVER":
                career_url = f"https://jobs.lever.co/{board}"
            elif ats == "ASHBY":
                career_url = f"https://jobs.ashbyhq.com/{board}"
            elif ats == "SMARTRECRUITERS":
                career_url = f"https://jobs.smartrecruiters.com/{board}"
            elif ats == "PERSONIO":
                career_url = f"https://{board}.jobs.personio.de"
            elif ats == "BAMBOOHR":
                career_url = f"https://{board}.bamboohr.com/careers"
            elif ats == "TEAMTAILOR":
                career_url = f"https://{board}.teamtailor.com"
            elif ats == "WORKABLE":
                career_url = f"https://apply.workable.com/{board}"
            elif ats == "RECRUITEE":
                career_url = f"https://{board}.recruitee.com"
            elif ats in ["BREEZY", "BREEZY_HR"]:
                career_url = f"https://{board}.breezy.hr"

            candidate = DiscoveredCompanyCandidate(
                name=canonical_name,
                domain=domain,
                website=f"https://{domain}" if domain else None,
                career_page_url=career_url,
                country=c.get("country", "United States"),
                operating_region=c.get("region", "North America"),
                industry=c.get("industry", "Software & IT"),
                ats_provider=ats,
                ats_board_id=board,
                discovery_source="PUBLIC_ATS_DIRECTORY",
                aliases=[c["name"]] if c["name"] != canonical_name else [],
                metadata={"ats_type": ats, "board": board}
            )
            candidates.append(candidate)

        return candidates
