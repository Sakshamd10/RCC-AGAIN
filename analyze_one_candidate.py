
import re
import json
import time
from pathlib import Path

from openstaadpy.os_analytical import connect


# ============================================================
# CONFIGURATION
# ============================================================

CANDIDATE = Path(
    r"C:\RCC AGAIN\candidate_models\candidate_001.STD"
)

OUTPUT_JSON = CANDIDATE.with_name(
    "candidate_001_structural_results.json"
)

ANALYSIS_TIMEOUT_SECONDS = 600


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def to_python(value):
    """Convert common API return values into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): to_python(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_python(v) for v in value]

    try:
        return [to_python(v) for v in value]
    except (TypeError, ValueError):
        return str(value)


def get_active_model_path(staad):
    """Try to retrieve the active model path."""
    try:
        return str(staad.GetSTAADFile())
    except Exception:
        return None


def parse_load_ids(model_text):
    """Read primary load cases and load combinations from the STD file."""
    primary = sorted({
        int(x) for x in re.findall(
            r"(?im)^\s*LOAD\s+(\d+)\s+LOADTYPE\b",
            model_text
        )
    })

    combinations = sorted({
        int(x) for x in re.findall(
            r"(?im)^\s*LOAD\s+COMB\s+(\d+)\b",
            model_text
        )
    })

    return primary, combinations


# ============================================================
# MAIN
# ============================================================

def main():
    if not CANDIDATE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {CANDIDATE}"
        )

    print("=" * 60)
    print("STAAD.PRO STRUCTURAL RESULTS EXTRACTION")
    print("=" * 60)

    # 1. Connect first: this fixes the previous NameError.
    staad = connect()

    if staad is None:
        raise RuntimeError(
            "Could not connect to STAAD.Pro. "
            "Open STAAD.Pro and try again."
        )

    print("Connected to STAAD.Pro.")

    # 2. Check which model is active.
    active_path = get_active_model_path(staad)

    print("Requested candidate:", CANDIDATE)
    print("Active model reported by API:", active_path)

    if active_path:
        try:
            same_model = (
                Path(active_path).resolve()
                == CANDIDATE.resolve()
            )
        except (OSError, ValueError):
            same_model = (
                active_path.strip().lower()
                == str(CANDIDATE).strip().lower()
            )

        if not same_model:
            print(
                "\nThe active model does not match the requested "
                "candidate. Open candidate_001.STD in STAAD.Pro "
                "and run this script again."
            )
            return

    else:
        print(
            "WARNING: The API did not report the active model path. "
            "Verify the active model in STAAD.Pro manually."
        )

    # 3. Check analysis status and result availability.
    if staad.IsAnalyzing():
        print("STAAD.Pro is currently analyzing.")
        start = time.time()

        while staad.IsAnalyzing():
            if time.time() - start > ANALYSIS_TIMEOUT_SECONDS:
                raise TimeoutError(
                    "Analysis did not finish within 600 seconds."
                )
            time.sleep(2)

    results_available = bool(
        staad.Output.AreResultsAvailable()
    )

    if not results_available:
        print(
            "\nNo results are currently available. "
            "Run Analysis in STAAD.Pro, wait for it to finish, "
            "and run this script again."
        )
        return

    print("Analysis results are available; no new analysis requested.")

    # 4. Parse load case IDs from the candidate file.
    model_text = CANDIDATE.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    load_cases, load_combinations = parse_load_ids(model_text)

    print("Primary load cases:", load_cases)
    print("Load combinations:", load_combinations)

    if not load_cases:
        print(
            "WARNING: No primary LOADTYPE cases were detected. "
            "Check the LOAD definitions in the STD file."
        )

    # 5. Retrieve model node and member IDs.
    node_ids = [
        int(x) for x in staad.Geometry.GetNodeList()
    ]

    member_ids = [
        int(x) for x in staad.Geometry.GetBeamList()
    ]

    print("Nodes found:", len(node_ids))
    print("Members found:", len(member_ids))

    # 6. Prepare results structure.
    data = {
        "candidate_file": str(CANDIDATE),
        "active_model_path": active_path,
        "results_available": results_available,
        "primary_load_cases": load_cases,
        "load_combinations": load_combinations,
        "node_count": len(node_ids),
        "member_count": len(member_ids),
        "nodal_displacements": [],
        "member_end_forces": [],
        "extraction_errors": []
    }

    # 7. Extract nodal displacements for primary load cases.
    print("\nExtracting nodal displacements...")

    for load_id in load_cases:
        for node_id in node_ids:
            try:
                result = staad.Output.GetNodeDisplacements(
                    node_id, load_id
                )

                data["nodal_displacements"].append({
                    "node_id": node_id,
                    "load_case_id": load_id,
                    "result": to_python(result)
                })

            except Exception as exc:
                data["extraction_errors"].append({
                    "result_type": "nodal_displacement",
                    "node_id": node_id,
                    "load_case_id": load_id,
                    "error": str(exc)
                })

    # 8. Extract member end forces.
    # LocalOrGlobal=0 is an initial API argument.
    # Confirm the installed OpenSTAAD version's enum convention
    # before interpreting the returned force components.
    print("Extracting member end forces...")

    for load_id in load_cases:
        for member_id in member_ids:
            for end in (0, 1):
                try:
                    result = staad.Output.GetMemberEndForces(
                        member_id,
                        end,
                        load_id,
                        0
                    )

                    data["member_end_forces"].append({
                        "member_id": member_id,
                        "end_argument": end,
                        "load_case_id": load_id,
                        "coordinate_system_argument": 0,
                        "result": to_python(result)
                    })

                except Exception as exc:
                    data["extraction_errors"].append({
                        "result_type": "member_end_force",
                        "member_id": member_id,
                        "end_argument": end,
                        "load_case_id": load_id,
                        "error": str(exc)
                    })

    # 9. Save extracted results.
    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print("Displacement records:", len(data["nodal_displacements"]))
    print("Member-force records:", len(data["member_end_forces"]))
    print("Extraction errors:", len(data["extraction_errors"]))
    print("Saved results:", OUTPUT_JSON)

    if data["extraction_errors"]:
        print(
            "Some API calls failed. Inspect extraction_errors "
            "in the JSON file before using the data."
        )
    else:
        print("All requested API calls returned without exceptions.")

    print(
        "\nNote: Returned values still require unit and component "
        "validation before engineering calculations."
    )


if __name__ == "__main__":
    main()
