# run_batch.py
#
# Batch driver for every candidate_NNN.STD in candidate_models/:
#   1. Ensure candidate_NNN.ANL exists (run STAAD analysis if not).
#   2. Ensure candidate_NNN_structural_results.json exists (extract
#      displacements/forces if not).
#   3. Call candidate_evaluator.evaluate().
#   4. Append/update a row in objectives.csv.
#
# Usage:
#   python run_batch.py                # all pending candidates
#   python run_batch.py --start 2 --end 61
#   python run_batch.py --skip-analysis  # only re-evaluate existing .ANL files
#
# Requires STAAD.Pro to be open (openstaadpy.connect() must succeed)
# unless --skip-analysis is used.

from pathlib import Path
import argparse
import csv
import json
import time

from openstaadpy.os_analytical import connect

from candidate_evaluator import evaluate

CANDIDATE_DIR = Path(r"C:\RCC AGAIN\candidate_models")
OBJECTIVES_CSV = Path(r"C:\RCC AGAIN\objectives.csv")

ANALYSIS_TIMEOUT_S = 900
POLL_INTERVAL_S = 3

FIELDS = [
    "candidate_id",
    "beam_volume_m3",
    "column_volume_m3",
    "concrete_volume_m3",
    "steel_kg",
    "steel_kg_per_m3",
    "concrete_grade",
    "steel_grade",
    "cost_inr",
    "carbon_kgco2e",
    "max_column_interaction_ratio",
    "fail_messages",
    "blocks_skipped",
    "max_drift_ratio",
    "drift_limit",
    "max_deflection_ratio",
    "deflection_limit",
    "strength_ok",
    "serviceability_ok",
    "feasible_staad_design",
    "status",
]


# ----------------------------------------------------------------------
def _connect():
    staad = connect()
    if staad is None:
        raise RuntimeError(
            "Could not connect to STAAD.Pro. "
            "Open STAAD.Pro with a model loaded and retry."
        )
    return staad


def _is_active(staad, path):
    try:
        return Path(staad.GetSTAADFile()).resolve() == path.resolve()
    except Exception:
        return False


def ensure_analysis(staad, std_path):
    anl = std_path.with_suffix(".ANL")
    if anl.exists() and anl.stat().st_mtime >= std_path.stat().st_mtime:
        print("  .ANL up to date, skipping analysis")
        return anl

    print(f"  Opening {std_path.name}")
    staad.OpenSTAADFile(str(std_path))
    time.sleep(2)

    if not _is_active(staad, std_path):
        raise RuntimeError(
            f"STAAD did not activate {std_path.name}; "
            f"active model is {staad.GetSTAADFile()}"
        )

    fn = (
        getattr(staad, "Analyze", None)
        or getattr(staad, "AnalyzeModel", None)
        or getattr(staad, "AnalyzeEx", None)
    )
    if fn is None:
        raise RuntimeError(
            "Installed OpenSTAAD API has no Analyze/AnalyzeModel/AnalyzeEx"
        )

    print("  Running analysis...")
    try:
        fn()
    except Exception as e:
        print(f"  Analyze() raised {e!r}; polling for .ANL anyway")

    start = time.time()
    while (not anl.exists()) or (
        anl.stat().st_mtime < std_path.stat().st_mtime
    ):
        if time.time() - start > ANALYSIS_TIMEOUT_S:
            raise TimeoutError(
                f"Analysis of {std_path.name} exceeded "
                f"{ANALYSIS_TIMEOUT_S}s"
            )
        time.sleep(POLL_INTERVAL_S)

    time.sleep(2)
    print(f"  Analysis complete: {anl.name}")
    return anl


def ensure_structural_results(std_path, skip=False):
    out = std_path.with_name(std_path.stem + "_structural_results.json")
    if out.exists() and out.stat().st_mtime >= std_path.stat().st_mtime:
        return out
    if skip:
        return out

    # analyze_one_candidate.py has module-level CANDIDATE / OUTPUT_JSON;
    # overwrite them, then call main().
    import analyze_one_candidate as aoc
    aoc.CANDIDATE = std_path
    aoc.OUTPUT_JSON = out
    aoc.main()

    if not out.exists():
        raise RuntimeError(
            f"analyze_one_candidate.py did not produce {out.name}"
        )
    return out


# ----------------------------------------------------------------------
def load_rows():
    if not OBJECTIVES_CSV.exists():
        return {}
    with OBJECTIVES_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        return {row["candidate_id"]: row for row in csv.DictReader(f)}


def save_rows(rows):
    with OBJECTIVES_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows.values())


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--skip-analysis", action="store_true")
    args = ap.parse_args()

    candidates = sorted(
        p for p in CANDIDATE_DIR.glob("candidate_*.STD")
        if not p.stem.endswith("_review")
    )
    if args.start is not None:
        candidates = [
            p for p in candidates
            if int(p.stem.split("_")[1]) >= args.start
        ]
    if args.end is not None:
        candidates = [
            p for p in candidates
            if int(p.stem.split("_")[1]) <= args.end
        ]

    if not candidates:
        print("No candidates to process.")
        return

    print(f"Processing {len(candidates)} candidate(s)")
    print(f"Objectives CSV: {OBJECTIVES_CSV}")

    staad = None
    if not args.skip_analysis:
        staad = _connect()
        print(f"STAAD: {staad.GetApplicationVersion()}")

    rows = load_rows()
    failures = []

    for i, std_path in enumerate(candidates, 1):
        cid = std_path.stem
        print(f"\n[{i}/{len(candidates)}] {cid}")
        try:
            if not args.skip_analysis:
                ensure_analysis(staad, std_path)
            elif not std_path.with_suffix(".ANL").exists():
                raise RuntimeError("No .ANL and --skip-analysis was set")

            ensure_structural_results(std_path, skip=args.skip_analysis)
            result = evaluate(std_path.with_suffix(""))
            result["candidate_id"] = cid

            rows[cid] = result
            save_rows(rows)

            print(
                f"  cost=Rs {result.get('cost_inr', '?'):,}  "
                f"carbon={result.get('carbon_kgco2e', '?'):,} kgCO2e  "
                f"feasible={result.get('feasible_staad_design')}"
            )
        except Exception as err:
            print(f"  FAILED: {err}")
            failures.append((cid, str(err)))

    print("\n" + "=" * 60)
    print(f"Done. {len(rows)} row(s) in {OBJECTIVES_CSV}")
    if failures:
        print(f"{len(failures)} failure(s):")
        for cid, msg in failures:
            print(f"  {cid}: {msg}")

    feasible = sum(
        1 for r in rows.values()
        if str(r.get("feasible_staad_design")).lower() in ("true", "1")
    )
    print(f"Feasible: {feasible} / {len(rows)}")


if __name__ == "__main__":
    main()
    