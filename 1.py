import csv
from pathlib import Path

CSV_PATH = Path(r"C:\RCC AGAIN\objectives.csv")
with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"{'Candidate':<12} | {'Strength OK?':<12} | {'Service OK?':<12} | {'Max Drift':<10} | {'Limit':<10}")
print("-" * 75)

for r in rows[:10]: # Just looking at the first 10
    cid = r.get("candidate_id", "?")
    s_ok = r.get("strength_ok", "?")
    v_ok = r.get("serviceability_ok", "?")
    drift = r.get("max_drift_ratio", "?")
    limit = r.get("drift_limit", "?")
    
    print(f"{cid:<12} | {s_ok:<12} | {v_ok:<12} | {drift:<10} | {limit:<10}")