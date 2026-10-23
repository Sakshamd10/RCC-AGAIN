import csv
import json
from pathlib import Path
from candidate_evaluator import evaluate

CANDIDATE_DIR = Path(r"C:\RCC AGAIN\candidate_models")
OUT_CSV = Path(r"C:\RCC AGAIN\objectives.csv")

# Load existing rows so we don't lose the ones you already have
existing = {}
if OUT_CSV.exists():
    with OUT_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            existing[row["candidate_id"]] = row

print("Scanning candidates...")
models = sorted([p for p in CANDIDATE_DIR.glob("candidate_*.STD") if not p.stem.endswith("_review")])

for std_path in models:
    cid = std_path.stem
    anl_path = std_path.with_suffix(".ANL")
    
    # If we already have the result and the ANL exists, we can skip
    if cid in existing and anl_path.exists():
        print(f"[SKIP] {cid} already in CSV")
        continue
        
    if not anl_path.exists():
        print(f"[WAIT] {cid} is still missing its .ANL file")
        continue
        
    print(f"[EVALUATING] {cid}...")
    try:
        # We pass the path without the extension to evaluate()
        res = evaluate(std_path.with_suffix(""))
        res["candidate_id"] = cid
        
        # Since we don't have _structural_results.json yet, serviceability will be False.
        # If you only care about cost/carbon right now, that's fine.
        
        existing[cid] = res
    except Exception as e:
        print(f"  -> Error: {e}")

# Get all unique columns for the CSV
fields = set()
for row in existing.values():
    fields.update(row.keys())
fields = sorted(list(fields))

with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(existing.values())

print(f"\nDone! Saved {len(existing)} rows to {OUT_CSV}")