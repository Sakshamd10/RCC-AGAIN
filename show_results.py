import csv
from pathlib import Path

CSV_PATH = Path(r"C:\RCC AGAIN\objectives.csv")

if not CSV_PATH.exists():
    print("No objectives.csv found yet!")
    exit()

with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if not rows:
    print("CSV is empty.")
    exit()

# Define the columns we want to show
cols = [
    "candidate_id", 
    "concrete_volume_m3", 
    "steel_kg", 
    "cost_inr", 
    "carbon_kgco2e", 
    "feasible_staad_design"
]

# Print a nice header
print("=" * 85)
print(f"{'Candidate':<12} | {'Vol (m3)':<10} | {'Steel (kg)':<12} | {'Cost (Rs)':<12} | {'Carbon (kg)':<12} | {'Safe?':<6}")
print("=" * 85)

safe_count = 0

for r in rows:
    cid = r.get("candidate_id", "?")
    vol = float(r.get("concrete_volume_m3", 0))
    steel = float(r.get("steel_kg", 0))
    cost = float(r.get("cost_inr", 0))
    carb = float(r.get("carbon_kgco2e", 0))
    
    # Check if safe
    safe_str = r.get("feasible_staad_design", "False")
    is_safe = str(safe_str).lower() in ("true", "1", "yes")
    if is_safe:
        safe_count += 1
        safe_display = "YES"
    else:
        safe_display = "NO"
    
    print(f"{cid:<12} | {vol:<10.1f} | {steel:<12.1f} | {cost:<12,.0f} | {carb:<12,.0f} | {safe_display:<6}")

print("=" * 85)
print(f"Total Candidates: {len(rows)}")
print(f"Safe Designs:     {safe_count} / {len(rows)}")
print(f"File saved at:    {CSV_PATH}")
