
from pathlib import Path
import csv

# ============================================================
# RCC OPTIMIZATION: PARETO FRONT ANALYSIS
# Input: objective_results.csv
# Objectives: Minimize cost and embodied carbon
# ============================================================

ROOT = Path(r"C:\RCC AGAIN")
INPUT_FILE = ROOT / "batch_results" / "objective_results.csv"
OUTPUT_DIR = ROOT / "batch_results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PARETO_FILE = OUTPUT_DIR / "pareto_front.csv"
DOMINATED_FILE = OUTPUT_DIR / "dominated_candidates.csv"
GRAPH_FILE = OUTPUT_DIR / "pareto_front.png"

COST_COLUMN = "estimated_total_cost_INR"
CARBON_COLUMN = "estimated_total_carbon_kgCO2e"


def load_candidates():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    candidates = []

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        required = {
            "model",
            COST_COLUMN,
            CARBON_COLUMN,
            "gross_member_concrete_volume_m3",
        }

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"Required CSV columns are missing: {sorted(missing)}"
            )

        for row in reader:
            candidates.append({
                **row,
                "cost": float(row[COST_COLUMN]),
                "carbon": float(row[CARBON_COLUMN]),
                "volume": float(
                    row["gross_member_concrete_volume_m3"]
                ),
            })

    if not candidates:
        raise ValueError("No candidates were found in the input CSV.")

    return candidates


def dominates(a, b):
    """
    Candidate a dominates candidate b if:
    a is no worse in both objectives and strictly better in at least one.
    Both objectives are minimized.
    """
    no_worse = (
        a["cost"] <= b["cost"]
        and a["carbon"] <= b["carbon"]
    )

    strictly_better = (
        a["cost"] < b["cost"]
        or a["carbon"] < b["carbon"]
    )

    return no_worse and strictly_better


def find_pareto_front(candidates):
    pareto = []
    dominated = []

    for candidate in candidates:
        is_dominated = any(
            dominates(other, candidate)
            for other in candidates
            if other["model"] != candidate["model"]
        )

        if is_dominated:
            dominated.append(candidate)
        else:
            pareto.append(candidate)

    # Order the Pareto candidates by cost.
    pareto.sort(key=lambda item: item["cost"])

    return pareto, dominated


def save_csv(path, rows):
    if not rows:
        print(f"No rows to write to {path.name}")
        return

    # Preserve the original columns and add no temporary fields.
    output_rows = []

    for row in rows:
        output_rows.append({
            key: value
            for key, value in row.items()
            if key not in {"cost", "carbon", "volume"}
        })

    with path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(output_rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(output_rows)


def create_graph(candidates, pareto):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "\nMatplotlib is not installed, so the graph was skipped."
        )
        print(
            "To install it, run: python -m pip install matplotlib"
        )
        return

    plt.figure(figsize=(10, 6))

    # All candidates
    plt.scatter(
        [c["cost"] for c in candidates],
        [c["carbon"] for c in candidates],
        label="All candidates"
    )

    # Non-dominated candidates
    plt.scatter(
        [c["cost"] for c in pareto],
        [c["carbon"] for c in pareto],
        marker="x",
        s=100,
        label="Pareto front"
    )

    for candidate in pareto:
        plt.annotate(
            candidate["model"].replace(".STD", ""),
            (candidate["cost"], candidate["carbon"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8
        )

    plt.xlabel("Estimated material cost (INR)")
    plt.ylabel("Estimated embodied carbon (kg CO2e)")
    plt.title("RCC Candidate Designs: Pareto Front")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPH_FILE, dpi=300)
    plt.close()

    print(f"Graph saved to: {GRAPH_FILE}")


def main():
    print("Loading candidate objective results...")
    candidates = load_candidates()

    print(f"Candidates loaded: {len(candidates)}")

    pareto, dominated = find_pareto_front(candidates)

    save_csv(PARETO_FILE, pareto)
    save_csv(DOMINATED_FILE, dominated)
    create_graph(candidates, pareto)

    print("\n========== PARETO ANALYSIS ==========")
    print(f"Total candidates: {len(candidates)}")
    print(f"Non-dominated candidates: {len(pareto)}")
    print(f"Dominated candidates: {len(dominated)}")

    print("\nNon-dominated candidates:")

    for candidate in pareto:
        print(
            f"{candidate['model']} | "
            f"Cost = Rs {candidate['cost']:,.0f} | "
            f"Carbon = {candidate['carbon']:,.1f} kg CO2e"
        )

    print(f"\nPareto results: {PARETO_FILE}")
    print(f"Dominated results: {DOMINATED_FILE}")

    print(
        "\nIMPORTANT: This is Pareto screening of existing candidates, "
        "not an evolutionary NSGA-II run."
    )


if __name__ == "__main__":
    main()
