import httpx

headers = {"User-Agent": "GetMeHirePlatform/2.0"}
slugs = ["klarna", "transferwise", "wise", "zalando", "abb", "vodafone", "capgemini", "deliveryhero", "cern", "bosch", "ikea"]

for slug in slugs:
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=5"
    try:
        r = httpx.get(url, headers=headers, timeout=10)
        total = r.json().get("totalFound") if r.status_code == 200 else None
        print(f"{slug}: status={r.status_code}, totalFound={total}")
    except Exception as e:
        print(f"{slug}: error={e}")
