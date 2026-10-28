
from pathlib import Path
import csv
import random
import math

# ============================================================
# RCC G+3: LHS + NSGA-II PRELIMINARY OPTIMIZATION
#
# IMPORTANT:
# This is a simplified material-estimation model.
# It does NOT run STAAD.Pro or verify structural safety.
# ============================================================

ROOT = Path(r"C:\RCC AGAIN")
OUT = ROOT / "batch_results"
OUT.mkdir(parents=True, exist_ok=True)

ALL_FILE = OUT / "nsga2_all_candidates.csv"
PARETO_FILE = OUT / "nsga2_lhs_results.csv"
GRAPH_FILE = OUT / "nsga2_lhs_pareto.png"

# Approximate member lengths from the existing model.
BEAM_LENGTH = 775.0
COLUMN_LENGTH = 260.0

# Illustrative assumptions only. Replace with verified project data.
CONCRETE_COST = 8000.0          # INR/m3
CONCRETE_DENSITY = 2400.0       # kg/m3
CONCRETE_CARBON = 0.188         # kg CO2e/kg
STEEL_COST = 65.0               # INR/kg
STEEL_CARBON = 1.99             # kg CO2e/kg

# Variables:
# beam width, beam depth, column width, column depth (m)
# assumed reinforcement allowance (kg/m3 of concrete)
LOWER = [0.25, 0.40, 0.45, 0.45, 80.0]
UPPER = [0.35, 0.60, 0.65, 0.65, 160.0]

POP_SIZE = 64
GENERATIONS = 100
SEED = 42
random.seed(SEED)


def lhs_population(n):
    """Latin Hypercube Sampling for the initial population."""
    dimensions = len(LOWER)
    columns = []

    for j in range(dimensions):
        values = [(i + random.random()) / n for i in range(n)]
        random.shuffle(values)
        columns.append(values)

    population = []
    for i in range(n):
        x = [
            LOWER[j] + columns[j][i] * (UPPER[j] - LOWER[j])
            for j in range(dimensions)
        ]
        population.append(x)

    return population


def evaluate(x):
    """Estimate material volume, cost and embodied carbon."""
    bw, bd, cw, cd, steel_rate = x

    beam_volume = BEAM_LENGTH * bw * bd
    column_volume = COLUMN_LENGTH * cw * cd
    volume = beam_volume + column_volume

    concrete_cost = volume * CONCRETE_COST
    steel_mass = volume * steel_rate
    total_cost = concrete_cost + steel_mass * STEEL_COST

    concrete_mass = volume * CONCRETE_DENSITY
    total_carbon = (
        concrete_mass * CONCRETE_CARBON
        + steel_mass * STEEL_CARBON
    )

    return {
        "volume": volume,
        "steel_mass": steel_mass,
        "cost": total_cost,
        "carbon": total_carbon,
    }


def objectives(x):
    result = evaluate(x)
    return [result["cost"], result["carbon"]]


def dominates(a, b):
    """True if a is no worse in both objectives and better in one."""
    return (
        all(x <= y for x, y in zip(a, b))
        and any(x < y for x, y in zip(a, b))
    )


def nondominated_front(population, values):
    front = []
    for i, f in enumerate(values):
        if not any(
            i != j and dominates(other, f)
            for j, other in enumerate(values)
        ):
            front.append(i)
    return front


def crowding_distance(front, values):
    distance = {i: 0.0 for i in front}

    if len(front) <= 2:
        for i in front:
            distance[i] = float("inf")
        return distance

    for m in range(2):
        ordered = sorted(front, key=lambda i: values[i][m])
        distance[ordered[0]] = float("inf")
        distance[ordered[-1]] = float("inf")

        low = values[ordered[0]][m]
        high = values[ordered[-1]][m]

        if high == low:
            continue

        for k in range(1, len(ordered) - 1):
            idx = ordered[k]
            if distance[idx] != float("inf"):
                distance[idx] += (
                    values[ordered[k + 1]][m]
                    - values[ordered[k - 1]][m]
                ) / (high - low)

    return distance


def rank_population(population, values):
    """Return Pareto ranks and crowding distances."""
    remaining = set(range(len(population)))
    ranks = {}
    distances = {}
    rank = 0

    while remaining:
        current = sorted(remaining)
        front = [
            i for i in current
            if not any(
                i != j and dominates(values[j], values[i])
                for j in current
            )
        ]

        if not front:
            break

        distances.update(crowding_distance(front, values))
        for i in front:
            ranks[i] = rank
            remaining.remove(i)

        rank += 1

    return ranks, distances


def tournament(population, ranks, distances):
    a, b = random.sample(range(len(population)), 2)

    if ranks[a] < ranks[b]:
        return population[a][:]
    if ranks[b] < ranks[a]:
        return population[b][:]
    if distances[a] > distances[b]:
        return population[a][:]
    if distances[b] > distances[a]:
        return population[b][:]

    return random.choice([population[a][:], population[b][:]])


def crossover(a, b):
    child1, child2 = [], []

    for i in range(len(a)):
        alpha = random.random()
        v1 = alpha * a[i] + (1 - alpha) * b[i]
        v2 = alpha * b[i] + (1 - alpha) * a[i]

        child1.append(max(LOWER[i], min(UPPER[i], v1)))
        child2.append(max(LOWER[i], min(UPPER[i], v2)))

    return child1, child2


def mutate(x, probability=0.25):
    """Mutate variables; enforce bounds."""
    for i in range(len(x)):
        if random.random() < probability:
            span = UPPER[i] - LOWER[i]
            x[i] += random.gauss(0, 0.15 * span)
            x[i] = max(LOWER[i], min(UPPER[i], x[i]))
    return x


def select_next_generation(population, values, size):
    """NSGA-II environmental selection."""
    remaining = set(range(len(population)))
    selected = []

    while remaining and len(selected) < size:
        current = sorted(remaining)
        front = [
            i for i in current
            if not any(
                i != j and dominates(values[j], values[i])
                for j in current
            )
        ]

        if not front:
            break

        if len(selected) + len(front) <= size:
            selected.extend(population[i][:] for i in front)
            remaining.difference_update(front)
        else:
            distances = crowding_distance(front, values)
            front.sort(key=lambda i: distances[i], reverse=True)
            needed = size - len(selected)
            selected.extend(population[i][:] for i in front[:needed])
            break

    return selected


def design_key(x):
    """Round values to avoid floating-point duplicates."""
    return tuple(round(v, 6) for v in x)


def save_csv(path, rows):
    if not rows:
        print(f"No rows to save: {path}")
        return

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_row(x, generation):
    result = evaluate(x)

    return {
        "generation": generation,
        "beam_width_m": x[0],
        "beam_depth_m": x[1],
        "column_width_m": x[2],
        "column_depth_m": x[3],
        "assumed_steel_kg_per_m3": x[4],
        "estimated_concrete_volume_m3": result["volume"],
        "estimated_steel_mass_kg": result["steel_mass"],
        "estimated_cost_INR": result["cost"],
        "estimated_carbon_kgCO2e": result["carbon"],
    }


def save_graph(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure(figsize=(9, 6))
        plt.scatter(
            [r["estimated_cost_INR"] for r in rows],
            [r["estimated_carbon_kgCO2e"] for r in rows],
        )
        plt.xlabel("Estimated material cost (INR)")
        plt.ylabel("Estimated embodied carbon (kg CO2e)")
        plt.title("Preliminary NSGA-II Pareto Front")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(GRAPH_FILE, dpi=300)
        plt.close()
        print("Graph saved:", GRAPH_FILE)

    except ImportError:
        print("Matplotlib unavailable; CSV files were still saved.")


def main():
    print("=" * 60)
    print("LHS + NSGA-II: RCC PRELIMINARY OPTIMIZATION")
    print("=" * 60)
    print("Population:", POP_SIZE)
    print("Generations:", GENERATIONS)

    population = lhs_population(POP_SIZE)

    # Archive every distinct design encountered.
    archive = {}
    for x in population:
        archive[design_key(x)] = x[:]

    for generation in range(1, GENERATIONS + 1):
        values = [objectives(x) for x in population]
        ranks, distances = rank_population(population, values)

        offspring = []
        while len(offspring) < POP_SIZE:
            p1 = tournament(population, ranks, distances)
            p2 = tournament(population, ranks, distances)

            if random.random() < 0.9:
                c1, c2 = crossover(p1, p2)
            else:
                c1, c2 = p1[:], p2[:]

            offspring.append(mutate(c1))
            if len(offspring) < POP_SIZE:
                offspring.append(mutate(c2))

        combined = population + offspring
        combined_values = [objectives(x) for x in combined]

        population = select_next_generation(
            combined, combined_values, POP_SIZE
        )

        for x in population:
            archive[design_key(x)] = x[:]

        if generation == 1 or generation % 10 == 0:
            current = [evaluate(x) for x in population]
            print(
                f"Generation {generation:3d}/{GENERATIONS} | "
                f"Unique designs encountered: {len(archive)} | "
                f"Minimum cost: Rs {min(v['cost'] for v in current):,.0f} | "
                f"Minimum carbon: {min(v['carbon'] for v in current):,.1f}"
            )

    # Save every unique design explored, not just the final population.
    all_rows = [
        make_row(x, "archive")
        for x in archive.values()
    ]
    save_csv(ALL_FILE, all_rows)

    # Find non-dominated designs across the full archive.
    designs = list(archive.values())
    values = [objectives(x) for x in designs]
    front = nondominated_front(designs, values)

    # Deduplicate identical objective pairs for the Pareto CSV.
    pareto_rows = []
    seen_objectives = set()

    for i in front:
        f = values[i]
        objective_key = (round(f[0], 2), round(f[1], 2))
        if objective_key in seen_objectives:
            continue
        seen_objectives.add(objective_key)
        pareto_rows.append(make_row(designs[i], "pareto"))

    save_csv(PARETO_FILE, pareto_rows)
    save_graph(pareto_rows)

    print("\n========== COMPLETED ==========")
    print("Unique designs explored:", len(archive))
    print("Pareto solutions:", len(pareto_rows))
    print("All candidates:", ALL_FILE)
    print("Pareto results:", PARETO_FILE)

    print("\nIMPORTANT:")
    print("Cost and carbon currently both favor lower material quantities.")
    print("A one-point Pareto front may therefore be mathematically correct.")
    print("This model does not run STAAD.Pro or check structural safety.")
    print("Do not use these candidates as approved building designs.")


if __name__ == "__main__":
    main()
