import csv
import json
from pathlib import Path
from candidate_evaluator import evaluate

CANDIDATE_DIR = Path(r"C:\RCC AGAIN\candidate_models")
OUT_CSV = Path(r"C:\RCC AGAIN\objectives.csv")

print("Scanning candidates and applying new unit math...")
models = sorted([p for p in CANDIDATE_DIR.glob("candidate_*.STD") if not p.stem.endswith("_review")])

results = {}

for std_path in models:
    cid = std_path.stem
    anl_path = std_path.with_suffix(".ANL")
    
    if not anl_path.exists():
        print(f"[WAIT] {cid} is missing its .ANL file")
        continue
        
    try:
        # This reads the JSON, applies the inches/mm fix, and gets the new safe status
        res_dict = evaluate(std_path.with_suffix(""))
        res_dict["candidate_id"] = cid
        results[cid] = res_dict
        print(f"[OK] Evaluated {cid} -> Safe: {res_dict.get('feasible_staad_design')}")
    except Exception as e:
        print(f"  -> Error on {cid}: {e}")

# Save to CSV
if results:
    fields = sorted(list(results[list(results.keys())[0]].keys()))
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results.values())
    print(f"\nSuccessfully saved {len(results)} evaluated models to {OUT_CSV}")