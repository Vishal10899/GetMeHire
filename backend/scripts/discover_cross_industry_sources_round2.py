"""
Probe round 2: Automotive, Clean Energy, Hospitality, Media, Streaming, Telco
"""

import httpx

candidates_round2 = [
    # AUTOMOTIVE, CLEAN ENERGY, INFRASTRUCTURE
    ("greenhouse", "formenergy", "Form Energy", "Clean Energy", "US"),
    ("greenhouse", "redwoodmaterials", "Redwood Materials", "Battery & Materials", "US"),
    ("greenhouse", "lucidmotors", "Lucid Motors", "Automotive & EV", "US"),
    ("greenhouse", "cruisecareers", "Cruise", "Autonomous Vehicles", "US"),
    ("greenhouse", "enpal", "Enpal", "Solar Energy", "Germany"),
    ("greenhouse", "northvolt", "Northvolt", "Battery Tech", "Sweden"),

    # HOSPITALITY, TRAVEL & FOOD TECH
    ("greenhouse", "toast", "Toast", "Restaurant Tech & Hospitality", "US"),
    ("greenhouse", "getyourguide", "GetYourGuide", "Travel & Tourism", "Germany"),
    ("greenhouse", "hopper", "Hopper", "Travel", "Canada"),
    ("greenhouse", "sonder", "Sonder", "Hospitality", "US"),

    # MEDIA, STREAMING, COMMUNICATION & GAMING
    ("greenhouse", "discord", "Discord", "Communications & Gaming", "US"),
    ("greenhouse", "reddit", "Reddit", "Social Media", "US"),
    ("greenhouse", "soundcloud", "SoundCloud", "Audio & Music", "Germany"),
    ("greenhouse", "epicgames", "Epic Games", "Gaming", "US"),
    ("greenhouse", "roblox", "Roblox", "Gaming & Metaverse", "US"),
    ("greenhouse", "unity3d", "Unity Technologies", "Gaming & 3D", "US"),
    ("lever", "spotify", "Spotify", "Audio & Streaming", "Sweden"),
    ("ashby", "perplexity", "Perplexity AI", "Search & AI", "US"),
    ("ashby", "glean", "Glean", "Enterprise Search", "US"),

    # COMMERCE, LOGISTICS, CONSUMER
    ("greenhouse", "faire", "Faire", "Wholesale Marketplace", "US"),
    ("greenhouse", "klaviyo", "Klaviyo", "Marketing Automation", "US"),
    ("greenhouse", "braze", "Braze", "Customer Engagement", "US"),
    ("greenhouse", "affirm", "Affirm", "Financial Services", "US"),
]

headers = {"User-Agent": "GetMeHirePlatform/2.0"}

results2 = []
for ats, slug, name, industry, country in candidates_round2:
    url = ""
    if ats == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    elif ats == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    elif ats == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

    try:
        r = httpx.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            count = 0
            if ats == "greenhouse":
                count = len(r.json().get("jobs", []))
            elif ats == "lever":
                count = len(r.json())
            elif ats == "ashby":
                count = len(r.json().get("jobs", []))
            
            if count > 0:
                results2.append({
                    "ats": ats.upper(),
                    "slug": slug,
                    "name": name,
                    "industry": industry,
                    "country": country,
                    "url": url,
                    "job_count": count
                })
                print(f"[FOUND] {name} ({industry}, {country}) on {ats.upper()}: {count} jobs")
        else:
            print(f"[NOT FOUND] {name} ({slug}): status {r.status_code}")
    except Exception as e:
        print(f"[ERROR] {name}: {e}")

print(f"\nRound 2 Active Boards: {len(results2)}, Total Vacancies: {sum(r['job_count'] for r in results2)}")

import json
with open("backend/discovered_candidate_sources_round2.json", "w") as f:
    json.dump(results2, f, indent=2)
