
import json
from pathlib import Path
from datetime import datetime

# ============================================================
# CANDIDATE 001: PRELIMINARY COST AND EMBODIED-CARBON ESTIMATE
# Geometry transcribed from the uploaded STAAD.Pro output.
# ============================================================

PROJECT_DIR = Path(r"C:\RCC AGAIN")
OUTPUT_DIR = PROJECT_DIR / "candidate_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "candidate_001_cost_carbon.json"

# ------------------------------------------------------------
# 1. QUANTITIES FROM CANDIDATE_001 MODEL GEOMETRY
# Units: metres, m3
# ------------------------------------------------------------

BEAM_COUNT = 155
BEAM_LENGTH_M = 5.0
BEAM_WIDTH_M = 0.275
BEAM_DEPTH_M = 0.400

MAIN_COLUMN_COUNT = 80
MAIN_COLUMN_HEIGHT_M = 3.0
COLUMN_WIDTH_M = 0.550
COLUMN_DEPTH_M = 0.600

ADDITIONAL_COLUMN_COUNT = 20
ADDITIONAL_COLUMN_HEIGHT_M = 1.0

beam_volume_m3 = (
    BEAM_COUNT
    * BEAM_LENGTH_M
    * BEAM_WIDTH_M
    * BEAM_DEPTH_M
)

column_volume_m3 = (
    MAIN_COLUMN_COUNT
    * MAIN_COLUMN_HEIGHT_M
    * COLUMN_WIDTH_M
    * COLUMN_DEPTH_M
    + ADDITIONAL_COLUMN_COUNT
    * ADDITIONAL_COLUMN_HEIGHT_M
    * COLUMN_WIDTH_M
    * COLUMN_DEPTH_M
)

# Gross geometric volume. Intersections have not been deducted.
concrete_volume_m3 = beam_volume_m3 + column_volume_m3

# ------------------------------------------------------------
# 2. ICE REFERENCE FACTORS AND COST RATES
# ------------------------------------------------------------

# Older ICE RC 40/50 concrete reference:
CONCRETE_CARBON_KGCO2E_PER_KG = 0.188

# ICE V3 world-average reinforcing steel reference:
REBAR_CARBON_KGCO2E_PER_KG = 1.99

# Assumptions for an initial Indian cost comparison.
# Replace with local supplier quotations / current schedule rates.
CONCRETE_COST_INR_PER_M3 = 8000.0
REBAR_COST_INR_PER_KG = 65.0

# Explicit preliminary allowance, NOT measured from the report.
REBAR_ALLOWANCE_KG_PER_M3 = 100.0

# Concrete density assumption for conversion from m3 to kg.
CONCRETE_DENSITY_KG_PER_M3 = 2400.0

# ------------------------------------------------------------
# 3. MATERIAL QUANTITIES
# ------------------------------------------------------------

concrete_mass_kg = (
    concrete_volume_m3 * CONCRETE_DENSITY_KG_PER_M3
)

rebar_mass_kg = (
    concrete_volume_m3 * REBAR_ALLOWANCE_KG_PER_M3
)

# ------------------------------------------------------------
# 4. COST CALCULATION
# ------------------------------------------------------------

concrete_cost_inr = (
    concrete_volume_m3 * CONCRETE_COST_INR_PER_M3
)

rebar_cost_inr = (
    rebar_mass_kg * REBAR_COST_INR_PER_KG
)

total_material_cost_inr = concrete_cost_inr + rebar_cost_inr

# ------------------------------------------------------------
# 5. EMBODIED-CARBON CALCULATION
# Cradle-to-gate material factors; no transport/site emissions.
# ------------------------------------------------------------

concrete_carbon_kgco2e = (
    concrete_mass_kg * CONCRETE_CARBON_KGCO2E_PER_KG
)

rebar_carbon_kgco2e = (
    rebar_mass_kg * REBAR_CARBON_KGCO2E_PER_KG
)

total_carbon_kgco2e = (
    concrete_carbon_kgco2e + rebar_carbon_kgco2e
)

# ------------------------------------------------------------
# 6. SAVE RESULTS
# ------------------------------------------------------------

results = {
    "candidate_id": "candidate_001",
    "calculation_time": datetime.now().isoformat(timespec="seconds"),
    "quantity_basis": "STAAD output geometry; preliminary gross quantities",
    "concrete_grade": "M40",
    "beam_concrete_volume_m3": round(beam_volume_m3, 3),
    "column_concrete_volume_m3": round(column_volume_m3, 3),
    "gross_concrete_volume_m3": round(concrete_volume_m3, 3),
    "concrete_density_kg_per_m3": CONCRETE_DENSITY_KG_PER_M3,
    "concrete_mass_kg": round(concrete_mass_kg, 2),
    "rebar_allowance_kg_per_m3": REBAR_ALLOWANCE_KG_PER_M3,
    "estimated_rebar_mass_kg": round(rebar_mass_kg, 2),
    "carbon_factors": {
        "concrete_kgco2e_per_kg": CONCRETE_CARBON_KGCO2E_PER_KG,
        "reinforcing_steel_kgco2e_per_kg": REBAR_CARBON_KGCO2E_PER_KG,
        "reference": "Older ICE RC 40/50 and ICE V3 rebar references"
    },
    "cost_rates_inr": {
        "concrete_per_m3": CONCRETE_COST_INR_PER_M3,
        "reinforcing_steel_per_kg": REBAR_COST_INR_PER_KG
    },
    "cost_breakdown_inr": {
        "concrete": round(concrete_cost_inr, 2),
        "reinforcing_steel": round(rebar_cost_inr, 2),
        "total_material_cost": round(total_material_cost_inr, 2)
    },
    "carbon_breakdown_kgco2e": {
        "concrete": round(concrete_carbon_kgco2e, 2),
        "reinforcing_steel": round(rebar_carbon_kgco2e, 2),
        "total": round(total_carbon_kgco2e, 2),
        "total_tonnes_co2e": round(total_carbon_kgco2e / 1000, 3)
    },
    "limitations": [
        "Slab concrete is not included because slab geometry was not identified.",
        "Gross member volumes may double-count beam-column intersections.",
        "Reinforcement mass is an assumed allowance, not an extracted bar schedule.",
        "Formwork, labour, transport, wastage, foundations beyond listed members, "
        "and construction equipment are excluded.",
        "Carbon factors and cost rates must be validated for the project location."
    ]
}

with OUTPUT_FILE.open("w", encoding="utf-8") as file:
    json.dump(results, file, indent=4)

print("\n===== CANDIDATE 001 COST AND CARBON =====")
print(f"Beam concrete volume:   {beam_volume_m3:.3f} m3")
print(f"Column concrete volume: {column_volume_m3:.3f} m3")
print(f"Gross concrete volume:  {concrete_volume_m3:.3f} m3")
print(f"Estimated rebar mass:   {rebar_mass_kg:,.2f} kg")
print(f"Concrete cost:          Rs. {concrete_cost_inr:,.2f}")
print(f"Rebar cost:             Rs. {rebar_cost_inr:,.2f}")
print(f"Total material cost:    Rs. {total_material_cost_inr:,.2f}")
print(f"Concrete carbon:        {concrete_carbon_kgco2e:,.2f} kg CO2e")
print(f"Rebar carbon:           {rebar_carbon_kgco2e:,.2f} kg CO2e")
print(f"Total embodied carbon:  {total_carbon_kgco2e:,.2f} kg CO2e")
print(f"Total carbon:           {total_carbon_kgco2e / 1000:.3f} tonnes CO2e")
print(f"\nSaved results to: {OUTPUT_FILE}")
