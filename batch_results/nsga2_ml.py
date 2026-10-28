import csv
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.lhs import LatinHypercubeSampling

CSV_PATH = Path(r"C:\RCC AGAIN\objectives.csv")
OUT_CSV = Path(r"C:\RCC AGAIN\batch_results\final_pareto_designs.csv")

print("1. Loading data...")
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

print("2. Training Random Forest...")
model_cost = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_cost)
model_carbon = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_carbon)

class RCCProblem(Problem):
    def __init__(self):
        super().__init__(n_var=4, n_obj=2, 
                         xl=np.array([250, 350, 30, 500]), 
                         xu=np.array([400, 600, 40, 550]))

    def _evaluate(self, X, out, *args, **kwargs):
        X_snapped = np.round(X)
        cost = model_cost.predict(X_snapped)
        carbon = model_carbon.predict(X_snapped)
        out["F"] = np.column_stack([cost, carbon])

print("3. Running NSGA-II...")
algorithm = NSGA2(pop_size=100, sampling=LatinHypercubeSampling(), 
                  crossover=SBX(prob=0.9, eta=15), mutation=PM(eta=20), eliminate_duplicates=True)

res = minimize(RCCProblem(), algorithm, ('n_gen', 50), seed=1, verbose=False)

print("4. Optimization Finished!")

if res.F is not None:
    print(f"\nSuccess! Found {len(res.F)} Pareto-optimal designs.")
    
    # Save results to CSV
    OUT_CSV.parent.mkdir(exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Beam_Width_mm", "Col_Width_mm", "Concrete_MPa", "Steel_MPa", "Cost_INR", "Carbon_kgCO2e"])
        for x, f_obj in zip(res.X, res.F):
            writer.writerow([round(x[0]), round(x[1]), round(x[2]), round(x[3]), round(f_obj[0]), round(f_obj[1])])
    
    print(f"Designs saved to: {OUT_CSV}")
    
    # Print the first 5 designs so you can see them in the terminal
    print("\n--- Top 5 Optimal Designs ---")
    print(f"Beam W | Col W | Grade | Steel | Cost (Rs) | Carbon (kg)")
    for x, f in list(zip(res.X, res.F))[:5]:
        print(f"{x[0]:>6.0f} | {x[1]:>5.0f} | {x[2]:>5.0f} | {x[3]:>5.0f} | {f[0]:>9,.0f} | {f[1]:>8,.0f}")
        
else:
    print("Error: NSGA-II returned no results.")