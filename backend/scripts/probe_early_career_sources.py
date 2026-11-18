import urllib.request
import json

candidates = [
    # Healthcare
    ("Cityblock Health", "https://boards-api.greenhouse.io/v1/boards/cityblock/jobs", "GREENHOUSE"),
    ("Ro", "https://boards-api.greenhouse.io/v1/boards/ro/jobs", "GREENHOUSE"),
    ("Color Health", "https://boards-api.greenhouse.io/v1/boards/color/jobs", "GREENHOUSE"),
    ("Oscar Health", "https://boards-api.greenhouse.io/v1/boards/oscar/jobs", "GREENHOUSE"),
    ("Maven Clinic", "https://boards-api.greenhouse.io/v1/boards/mavenclinic/jobs", "GREENHOUSE"),
    ("Clover Health", "https://boards-api.greenhouse.io/v1/boards/cloverhealth/jobs", "GREENHOUSE"),
    ("Benchling", "https://boards-api.greenhouse.io/v1/boards/benchling/jobs", "GREENHOUSE"),
    ("Sema4 / GeneDx", "https://boards-api.greenhouse.io/v1/boards/genedx/jobs", "GREENHOUSE"),
    ("Tempus", "https://boards-api.greenhouse.io/v1/boards/tempus/jobs", "GREENHOUSE"),
    # Finance / Accounting / Consulting
    ("Affirm", "https://boards-api.greenhouse.io/v1/boards/affirm/jobs", "GREENHOUSE"),
    ("Carta", "https://boards-api.greenhouse.io/v1/boards/carta/jobs", "GREENHOUSE"),
    ("Gusto", "https://boards-api.greenhouse.io/v1/boards/gusto/jobs", "GREENHOUSE"),
    ("Plaid", "https://boards-api.greenhouse.io/v1/boards/plaid/jobs", "GREENHOUSE"),
    ("Ramp", "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams", "ASHBY"),
    ("Klarna", "https://api.smartrecruiters.com/v1/companies/klarna/postings", "SMARTRECRUITERS"),
    ("BDO USA", "https://api.smartrecruiters.com/v1/companies/bdousa/postings", "SMARTRECRUITERS"),
    # Early Career / Tech Leaders
    ("Canva", "https://boards-api.greenhouse.io/v1/boards/canva/jobs", "GREENHOUSE"),
    ("Duolingo", "https://boards-api.greenhouse.io/v1/boards/duolingo/jobs", "GREENHOUSE"),
    ("Databricks", "https://boards-api.greenhouse.io/v1/boards/databricks/jobs", "GREENHOUSE"),
    ("Cloudflare", "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs", "GREENHOUSE"),
    ("Scale AI", "https://boards-api.greenhouse.io/v1/boards/scaleai/jobs", "GREENHOUSE"),
    ("Grammarly", "https://boards-api.greenhouse.io/v1/boards/grammarly/jobs", "GREENHOUSE"),
    ("GitLab", "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs", "GREENHOUSE"),
    ("Figma", "https://api.lever.co/v0/postings/figma?mode=json", "LEVER"),
    ("Notion", "https://api.lever.co/v0/postings/notion?mode=json", "LEVER"),
    ("Atlassian", "https://api.lever.co/v0/postings/atlassian?mode=json", "LEVER"),
    ("Palantir", "https://boards-api.greenhouse.io/v1/boards/palantir/jobs", "GREENHOUSE"),
    ("Reddit", "https://boards-api.greenhouse.io/v1/boards/reddit/jobs", "GREENHOUSE"),
]

print(f"Testing {len(candidates)} candidate sources...")
valid = []
for name, url, adapter in candidates:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.getcode()
            data = resp.read()
            count = 0
            if adapter == "GREENHOUSE":
                j = json.loads(data)
                count = len(j.get("jobs", []))
            elif adapter == "SMARTRECRUITERS":
                j = json.loads(data)
                count = len(j.get("content", []))
            elif adapter == "LEVER":
                j = json.loads(data)
                count = len(j)
            print(f"[OK] {name.ljust(20)} ({adapter}) -> HTTP {code}, {count} postings")
            if count > 0:
                valid.append((name, url, adapter, count))
    except Exception as e:
        print(f"[FAIL] {name.ljust(20)} ({adapter}) -> {e}")

print(f"\nTotal Valid Sources Found: {len(valid)}")
for v in valid:
    print(f"  {v[0]}: {v[3]} jobs ({v[2]})")
