import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.lhs import LatinHypercubeSampling

# ==========================================
# 1. LOAD STAAD DATA & TRAIN ML SURROGATE
# ==========================================
CSV_PATH = Path(r"C:\RCC AGAIN\objectives.csv")
OUT_DIR = Path(r"C:\RCC AGAIN\batch_results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading STAAD data and training ML model...")

X_data, y_cost, y_carbon = [], [], []

with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        v_beam = float(row["beam_volume_m3"])
        v_col = float(row["column_volume_m3"])
        
        bw = (v_beam / 155 / 5.0) * 1000
        cw = (v_col / 260) * 1000
        fc = 30 if row["concrete_grade"] == "M30" else 40
        fy = 500 if row["steel_grade"] == "Fe500" else 550
        
        X_data.append([bw, cw, fc, fy])
        y_cost.append(float(row["cost_inr"]))
        y_carbon.append(float(row["carbon_kgco2e"]))

# Train the models
model_cost = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_cost)
model_carbon = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_carbon)

print(f"ML Model trained on {len(X_data)} real STAAD designs!")

# ==========================================
# 2. NSGA-II PROBLEM DEFINITION
# ==========================================
class RCCProblem(Problem):
    def __init__(self):
        super().__init__(n_var=4, n_obj=2, 
                         xl=np.array([250, 350, 30, 500]), 
                         xu=np.array([400, 600, 40, 550]))

    def _evaluate(self, X, out, *args, **kwargs):
        X_snapped = np.round(X)
        
        # Predict Cost and Carbon
        cost = model_cost.predict(X_snapped)
        carbon = model_carbon.predict(X_snapped)
        
        out["F"] = np.column_stack([cost, carbon])

# ==========================================
# 3. RUN OPTIMIZATION
# ==========================================
print("Running NSGA-II (this takes about 5 seconds)...")
algorithm = NSGA2(
    pop_size=100, 
    sampling=LatinHypercubeSampling(),
    crossover=SBX(prob=0.9, eta=15), 
    mutation=PM(eta=20),
    eliminate_duplicates=True
)

try:
    res = minimize(
        RCCProblem(), algorithm, ('n_gen', 50), 
        seed=1, verbose=False
    )
    print("Optimization loop finished!")
except Exception as e:
    print(f"ERROR during optimization: {e}")
    raise e

# ==========================================
# 4. PLOT & SAVE RESULTS
# ==========================================
if res.F is not None:
    print(f"\nFound {len(res.F)} Pareto-optimal designs!")
    
    out_csv = OUT_DIR / "ml_pareto_front.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Beam_Width_mm", "Col_Width_mm", "Concrete_MPa", "Steel_MPa", "Cost_INR", "Carbon_kgCO2e"])
        for x, f_obj in zip(res.X, res.F):
            writer.writerow([round(x[0]), round(x[1]), round(x[2]), round(x[3]), round(f_obj[0]), round(f_obj[1])])
            
    print("CSV Saved successfully.")
    
    # Plot
    plt.figure(figsize=(10, 6))
    plt.scatter(res.F[:, 0], res.F[:, 1], color='green', s=50, label='ML-Assisted Pareto Front')
    plt.title("NSGA-II Pareto Front (Optimized using Real STAAD Data)")
    plt.xlabel("Estimated Material Cost (INR)")
    plt.ylabel("Estimated Embodied Carbon (kg CO2e)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    
    out_png = OUT_DIR / "ml_pareto_front.png"
    plt.savefig(out_png)
    print(f"Graph saved to: {out_png}")
    
    # Force the graph window to stay open
    plt.show(block=True)
    print("Graph window closed by user. Exiting script.")
    
else:
    print("NSGA-II returned None. Check your parameters.")