import urllib.request
import json
import urllib.parse

queries = [
    "costumer suppot",
    "softwere enginer",
    "acountent",
    "nurse",
    "restaurant",
    "curriculum",
    "account executive",
    "data scientist",
]

print("=== EVALUATING 8 MULTI-DOMAIN SEARCH QUERIES ===\n")
for q in queries:
    url = f"http://127.0.0.1:8000/api/v1/jobs?keyword={urllib.parse.quote(q)}&page_size=5"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())
    
    total = data.get("total", 0)
    did_you_mean = data.get("did_you_mean")
    is_corrected = data.get("is_corrected")
    latency = data.get("query_latency_ms", 0.0)
    items = data.get("items", [])
    
    print(f"QUERY: '{q}'")
    print(f"  Total Results: {total} | Latency: {latency:.1f}ms")
    print(f"  Typo Corrected: {is_corrected} -> '{did_you_mean}'")
    print("  Top Results:")
    if not items:
        print("    (Honest empty result - No matching verified listings)")
    for idx, item in enumerate(items, 1):
        c_name = item.get("company_name") or (item.get("company") or {}).get("canonical_name")
        print(f"    {idx}. '{item.get('normalized_title') or item.get('title')}' at {c_name}")
        print(f"       Category: {item.get('profession')} (Confidence: {item.get('classification_confidence')}) | Seeded: {item.get('is_demo', False)}")
        print(f"       Apply URL: {item.get('application_url', '')[:65]}...")
    print("-" * 60)
