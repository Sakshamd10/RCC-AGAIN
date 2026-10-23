import csv
import json
import time
from pathlib import Path
from openstaadpy.os_analytical import connect
from candidate_evaluator import evaluate

CANDIDATE_DIR = Path(r"C:\RCC AGAIN\candidate_models")
OUT_CSV = Path(r"C:\RCC AGAIN\objectives.csv")

def main():
    print("Connecting to STAAD.Pro...")
    staad = connect()
    if staad is None:
        print("ERROR: Open STAAD.Pro and load ANY model before running this.")
        return

    models = sorted([p for p in CANDIDATE_DIR.glob("candidate_*.STD") if not p.stem.endswith("_review")])
    print(f"Found {len(models)} candidates. Starting safe evaluation...")

    results = {}

    for i, std_path in enumerate(models, 1):
        cid = std_path.stem
        anl_path = std_path.with_suffix(".ANL")
        json_path = std_path.with_name(std_path.stem + "_structural_results.json")

        print(f"[{i}/{len(models)}] Checking {cid}...")

        if not anl_path.exists():
            print(f"  -> SKIP: No .ANL file found.")
            continue

        # 1. Extract Displacements (Only if we don't have the JSON yet)
        if not json_path.exists():
            try:
                staad.OpenSTAADFile(str(std_path))
                time.sleep(1) # Let STAAD load
                
                # Get Node IDs
                node_ids = [int(x) for x in staad.Geometry.GetNodeList()]
                
                # We only need Load Case 1 and 5 usually for drift, but let's grab 1 for now
                # (Extracting all 10 cases takes too long)
                disp_data = []
                for node_id in node_ids:
                    res = staad.Output.GetNodeDisplacements(node_id, 1)
                    disp_data.append({"node_id": node_id, "load_case_id": 1, "result": res})
                
                # Save to JSON so candidate_evaluator.py can read it
                with json_path.open("w") as f:
                    json.dump({"nodal_displacements": disp_data}, f)
                    
            except Exception as e:
                print(f"  -> STAAD API Error: {e}")
                continue

        # 2. Evaluate (Cost, Carbon, Strength, and Serviceability)
        try:
            # We use .with_suffix("") to strip the .STD extension
            res_dict = evaluate(std_path.with_suffix(""))
            res_dict["candidate_id"] = cid
            
            results[cid] = res_dict
            
            # Print a quick summary
            safe = res_dict.get("feasible_staad_design", False)
            print(f"  -> SAFE: {safe} | Cost: {res_dict.get('cost_inr'):,} | Carbon: {res_dict.get('carbon_kgco2e'):,}")
            
        except Exception as e:
            print(f"  -> Evaluator Error: {e}")

    # Save to CSV
    if results:
        fields = sorted(list(results[list(results.keys())[0]].keys()))
        with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results.values())
        print(f"\nSuccessfully saved {len(results)} evaluated models to {OUT_CSV}")

if __name__ == "__main__":
    main()