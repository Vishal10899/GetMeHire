import sys
import os
import json

with open("backend/source_audit_complete.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("--- SMARTRECRUITERS ISSUES ---")
for s in data["sources"]:
    if s["ats_provider"] == "SMARTRECRUITERS" and (s["health_status"] != "HEALTHY" or s.get("last_error")):
        print(f"ID #{s['source_id']} ({s['employer']}) | URL: {s['source_url']}")
        print(f"   Error: {s['last_error']}")

print("\n--- NON-GREENHOUSE FAILING SOURCES ---")
for s in data["sources"]:
    if s["ats_provider"] != "GREENHOUSE" and (s["health_status"] != "HEALTHY" or s.get("last_error")):
        print(f"ID #{s['source_id']} ({s['employer']}, {s['ats_provider']}) | URL: {s['source_url']}")
        print(f"   Error: {s['last_error']}")
