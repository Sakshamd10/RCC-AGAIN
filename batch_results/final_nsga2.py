import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from scipy.stats import qmc

# ==========================================
# 1. LOAD STAAD DATA & TRAIN ML SURROGATE
# ==========================================
CSV_PATH = Path(r"C:\RCC AGAIN\objectives.csv")
OUT_CSV = Path(r"C:\RCC AGAIN\batch_results\custom_nsga2_pareto.csv")

print("1. Loading data and training ML...")
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

model_cost = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_cost)
model_carbon = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_data, y_carbon)

# ==========================================
# 2. CUSTOM NSGA-II ENGINE
# ==========================================
class CustomNSGA2:
    def __init__(self, pop_size=100, n_gen=50):
        self.pop_size = pop_size
        self.n_gen = n_gen
        self.bounds = np.array([[250, 350, 30, 500], [400, 600, 40, 550]])

    def snap(self, X):
        """Force continuous variables to exact design steps."""
        X = np.clip(X, self.bounds[0], self.bounds[1])
        X[:, 0] = np.round(X[:, 0] / 25.0) * 25.0
        X[:, 1] = np.round(X[:, 1] / 25.0) * 25.0
        X[:, 2] = np.where(X[:, 2] < 35, 30, 40)
        X[:, 3] = np.where(X[:, 3] < 525, 500, 550)
        return X

    def evaluate(self, X):
        return np.column_stack([model_cost.predict(X), model_carbon.predict(X)])

    def fast_non_dominated_sort(self, F):
        """Sort population into Pareto fronts."""
        n = len(F)
        S = [[] for _ in range(n)]
        n_dom = np.zeros(n, dtype=int)
        rank = np.zeros(n, dtype=int)

        for p in range(n):
            for q in range(n):
                if (F[p, 0] <= F[q, 0] and F[p, 1] <= F[q, 1]) and (F[p, 0] < F[q, 0] or F[p, 1] < F[q, 1]):
                    S[p].append(q)
                elif (F[q, 0] <= F[p, 0] and F[q, 1] <= F[p, 1]) and (F[q, 0] < F[p, 0] or F[q, 1] < F[p, 1]):
                    n_dom[p] += 1
            if n_dom[p] == 0:
                rank[p] = 0

        fronts = [[]]
        for p in range(n):
            if n_dom[p] == 0:
                fronts[0].append(p)

        i = 0
        while len(fronts[i]) > 0:
            next_front = []
            for p in fronts[i]:
                for q in S[p]:
                    n_dom[q] -= 1
                    if n_dom[q] == 0:
                        rank[q] = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)
        return fronts[:-1]

    def crowding_distance(self, F):
        n, m = F.shape
        distances = np.zeros(n)
        for i in range(m):
            sort_idx = np.argsort(F[:, i])
            distances[sort_idx[0]] = distances[sort_idx[-1]] = np.inf
            f_range = F[sort_idx[-1], i] - F[sort_idx[0], i]
            if f_range == 0: continue
            for j in range(1, n - 1):
                distances[sort_idx[j]] += (F[sort_idx[j + 1], i] - F[sort_idx[j - 1], i]) / f_range
        return distances

    def run(self):
        print(f"Running Custom NSGA-II (Pop: {self.pop_size}, Gens: {self.n_gen})...")
        
        # 1. Initialization using Latin Hypercube Sampling (LHS)
        sampler = qmc.LatinHypercube(d=4)
        X = sampler.random(n=self.pop_size)
        X = self.bounds[0] + X * (self.bounds[1] - self.bounds[0])
        X = self.snap(X)
        F = self.evaluate(X)

        for gen in range(self.n_gen):
            # 2. Create offspring (Simple crossover and mutation)
            X_offspring = np.zeros_like(X)
            for i in range(self.pop_size):
                p1, p2 = X[np.random.choice(self.pop_size, 2, replace=False)]
                # Crossover
                alpha = np.random.rand(4)
                child = alpha * p1 + (1 - alpha) * p2
                # Mutation
                if np.random.rand() < 0.2:
                    child += np.random.normal(0, 10, 4)
                X_offspring[i] = child

            X_offspring = self.snap(X_offspring)
            F_offspring = self.evaluate(X_offspring)

            # 3. Combine and Select
            X_combined = np.vstack([X, X_offspring])
            F_combined = np.vstack([F, F_offspring])

            fronts = self.fast_non_dominated_sort(F_combined)
            
            new_X, new_F = [], []
            for front in fronts:
                if len(new_X) + len(front) <= self.pop_size:
                    new_X.extend(X_combined[front])
                    new_F.extend(F_combined[front])
                else:
                    distances = self.crowding_distance(F_combined[front])
                    sorted_idx = np.argsort(distances)[::-1]
                    needed = self.pop_size - len(new_X)
                    for idx in sorted_idx[:needed]:
                        new_X.append(X_combined[front[idx]])
                        new_F.append(F_combined[front[idx]])
                    break
            
            X = np.array(new_X)
            F = np.array(new_F)
            
            if (gen+1) % 10 == 0:
                print(f"  Generation {gen+1}/{self.n_gen} complete.")

        return X, F

# ==========================================
# 3. EXECUTE AND SAVE
# ==========================================
nsga = CustomNSGA2(pop_size=100, n_gen=50)
X_final, F_final = nsga.run()

print(f"\nSuccess! Found {len(X_final)} Pareto-optimal designs.")

OUT_CSV.parent.mkdir(exist_ok=True)
with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Beam_Width_mm", "Col_Width_mm", "Concrete_MPa", "Steel_MPa", "Cost_INR", "Carbon_kgCO2e"])
    for x, f_obj in zip(X_final, F_final):
        writer.writerow([x[0], x[1], x[2], x[3], round(f_obj[0]), round(f_obj[1])])

print(f"Designs saved to: {OUT_CSV}")

# Show the Pareto Front
plt.figure(figsize=(10, 6))
plt.scatter(F_final[:, 0], F_final[:, 1], color='green', s=60, edgecolors='black')
plt.title("Custom NSGA-II Pareto Front (Optimized using Real STAAD Data)")
plt.xlabel("Estimated Material Cost (INR)")
plt.ylabel("Estimated Embodied Carbon (kg CO2e)")
plt.grid(True)
plt.tight_layout()
plt.show()

print("\n--- Top 5 Optimal Designs ---")
print(f"Beam W | Col W | Grade | Steel | Cost (Rs) | Carbon (kg)")
for x, f in list(zip(X_final, F_final))[:5]:
    print(f"{x[0]:>6.0f} | {x[1]:>5.0f} | {x[2]:>5.0f} | {x[3]:>5.0f} | {f[0]:>9,.0f} | {f[1]:>8,.0f}")