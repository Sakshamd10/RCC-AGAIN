


from pathlib import Path
import re
import csv
import math

# ============================================================
# RCC OPTIMIZATION: MATERIAL COST AND EMBODIED CARBON
# ============================================================

ROOT = Path(r"C:\RCC AGAIN")
MODEL_DIR = ROOT / "candidate_models"
OUTPUT_DIR = ROOT / "batch_results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# ILLUSTRATIVE ASSUMPTIONS - REPLACE WITH VERIFIED PROJECT DATA
# ------------------------------------------------------------

CONCRETE_DENSITY = 2400.0          # kg/m3
CONCRETE_COST = 8000.0             # INR/m3
CONCRETE_CARBON = 0.188            # kg CO2e/kg concrete

STEEL_COST = 65.0                  # INR/kg
STEEL_CARBON = 1.99                # kg CO2e/kg steel
STEEL_ALLOWANCE = 100.0            # assumed kg steel/m3 concrete

# Member IDs identified in the validated STAAD model.
# Assumes the same member numbering in all candidates.
BEAM_RANGES = [(1, 80), (161, 235)]


def get_section(lines, start_text, end_text):
    """Extract lines between two STAAD section markers."""
    start = None

    for i, line in enumerate(lines):
        if start_text.upper() in line.upper():
            start = i + 1
            break

    if start is None:
        raise ValueError(f"Section not found: {start_text}")

    end = len(lines)

    for i in range(start, len(lines)):
        if end_text.upper() in lines[i].upper():
            end = i
            break

    return lines[start:end]


def numeric_values(text):
    """Extract integer/decimal/scientific-notation numbers."""
    pattern = (
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
        r"(?:[Ee][-+]?\d+)?"
    )
    return re.findall(pattern, text)


def parse_nodes(section_lines):
    """Parse node coordinates from the joint-coordinate section."""
    nodes = {}

    for line in section_lines:
        line = line.strip()

        if not line or line.startswith("*"):
            continue

        # STAAD files may use semicolons to separate records.
        records = line.split(";")

        for record in records:
            record = record.strip()
            if not record:
                continue

            values = numeric_values(record)

            # Each node record contains ID, X, Y and Z.
            if len(values) < 4 or len(values) % 4 != 0:
                continue

            try:
                for i in range(0, len(values), 4):
                    node_id = int(float(values[i]))
                    x = float(values[i + 1])
                    y = float(values[i + 2])
                    z = float(values[i + 3])
                    nodes[node_id] = (x, y, z)
            except (ValueError, OverflowError):
                continue

    if not nodes:
        # Fallback: process one node record per line.
        for line in section_lines:
            line = line.strip().rstrip(";")
            if not line or line.startswith("*"):
                continue

            values = numeric_values(line)

            if len(values) >= 4:
                try:
                    node_id = int(float(values[0]))
                    nodes[node_id] = (
                        float(values[1]),
                        float(values[2]),
                        float(values[3]),
                    )
                except (ValueError, OverflowError):
                    continue

    if not nodes:
        raise ValueError(
            "No nodes parsed. Check the JOINT COORDINATES section format."
        )

    return nodes


def parse_members(section_lines):
    """Parse member ID, start node and end node."""
    members = {}

    for line in section_lines:
        line = line.strip()

        if not line or line.startswith("*"):
            continue

        for record in line.split(";"):
            record = record.strip()
            if not record:
                continue

            values = numeric_values(record)

            # A standard incidence record contains three integers.
            if len(values) < 3 or len(values) % 3 != 0:
                continue

            try:
                for i in range(0, len(values), 3):
                    member_id = int(float(values[i]))
                    start_node = int(float(values[i + 1]))
                    end_node = int(float(values[i + 2]))

                    members[member_id] = (start_node, end_node)
            except (ValueError, OverflowError):
                continue

    if not members:
        raise ValueError("No members parsed from MEMBER INCIDENCES.")

    return members


def expand_ids(text):
    """Expand STAAD member ranges such as 1 TO 10 15 20 TO 25."""
    tokens = text.split()
    result = set()
    i = 0

    while i < len(tokens):
        if not tokens[i].isdigit():
            i += 1
            continue

        start = int(tokens[i])

        if (
            i + 2 < len(tokens)
            and tokens[i + 1].upper() == "TO"
            and tokens[i + 2].isdigit()
        ):
            end = int(tokens[i + 2])

            if end < start:
                raise ValueError(f"Invalid member range: {start} TO {end}")

            result.update(range(start, end + 1))
            i += 3
        else:
            result.add(start)
            i += 1

    return result


def parse_sections(section_lines):
    """Parse PRIS YD and ZD section assignments."""
    # Join continuation lines and remove STAAD continuation hyphens.
    text = " ".join(
        line.strip().rstrip("-").strip()
        for line in section_lines
        if line.strip() and not line.strip().startswith("*")
    )

    # Find each property assignment.
    pattern = re.compile(
        r"(?P<ids>.*?)\bPRIS\s+YD\s+"
        r"(?P<yd>[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
        r"(?:[Ee][-+]?\d+)?)\s+ZD\s+"
        r"(?P<zd>[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
        r"(?:[Ee][-+]?\d+)?)",
        re.IGNORECASE
    )

    sections = {}

    for match in pattern.finditer(text):
        member_ids = expand_ids(match.group("ids"))
        yd = float(match.group("yd"))
        zd = float(match.group("zd"))

        if yd <= 0 or zd <= 0:
            raise ValueError("A section has a non-positive dimension.")

        for member_id in member_ids:
            sections[member_id] = (yd, zd)

    if not sections:
        raise ValueError(
            "No PRIS YD/ZD properties parsed from MEMBER PROPERTY."
        )

    return sections


def parse_model(file_path):
    """Read a STAAD file and return its nodes, members and sections."""
    lines = file_path.read_text(
        encoding="utf-8-sig",
        errors="replace"
    ).splitlines()

    # Identify section boundaries directly instead of maintaining
    # a state variable while reading the whole file.
    nodes_section = get_section(
        lines, "JOINT COORDINATES", "MEMBER INCIDENCES"
    )
    members_section = get_section(
        lines, "MEMBER INCIDENCES", "DEFINE MATERIAL"
    )
    properties_section = get_section(
        lines, "MEMBER PROPERTY", "CONSTANTS"
    )

    nodes = parse_nodes(nodes_section)
    members = parse_members(members_section)
    sections = parse_sections(properties_section)

    missing_sections = set(members) - set(sections)
    if missing_sections:
        raise ValueError(
            f"{len(missing_sections)} members lack section properties. "
            f"Examples: {sorted(missing_sections)[:10]}"
        )

    missing_nodes = {
        node
        for endpoints in members.values()
        for node in endpoints
        if node not in nodes
    }

    if missing_nodes:
        raise ValueError(
            f"Member endpoints reference missing nodes: "
            f"{sorted(missing_nodes)[:10]}"
        )

    return nodes, members, sections


def is_beam(member_id):
    return any(
        first <= member_id <= last
        for first, last in BEAM_RANGES
    )


def calculate_volumes(nodes, members, sections):
    """Calculate gross member volume = length x section area."""
    beam_volume = 0.0
    column_stub_volume = 0.0

    for member_id, (node_a, node_b) in members.items():
        x1, y1, z1 = nodes[node_a]
        x2, y2, z2 = nodes[node_b]

        length = math.sqrt(
            (x2 - x1) ** 2
            + (y2 - y1) ** 2
            + (z2 - z1) ** 2
        )

        yd, zd = sections[member_id]
        volume = length * yd * zd

        if is_beam(member_id):
            beam_volume += volume
        else:
            column_stub_volume += volume

    return beam_volume, column_stub_volume


def calculate_objectives(volume):
    """Estimate material cost and embodied carbon."""
    concrete_mass = volume * CONCRETE_DENSITY

    # Assumption only: actual reinforcement is not extracted here.
    steel_mass = volume * STEEL_ALLOWANCE

    concrete_cost = volume * CONCRETE_COST
    steel_cost = steel_mass * STEEL_COST
    total_cost = concrete_cost + steel_cost

    concrete_carbon = concrete_mass * CONCRETE_CARBON
    steel_carbon = steel_mass * STEEL_CARBON
    total_carbon = concrete_carbon + steel_carbon

    return {
        "concrete_mass_kg": concrete_mass,
        "assumed_steel_mass_kg": steel_mass,
        "concrete_cost_INR": concrete_cost,
        "assumed_steel_cost_INR": steel_cost,
        "estimated_total_cost_INR": total_cost,
        "concrete_carbon_kgCO2e": concrete_carbon,
        "assumed_steel_carbon_kgCO2e": steel_carbon,
        "estimated_total_carbon_kgCO2e": total_carbon,
    }


def main():
    # Matches candidate_001.STD through candidate_063.STD.
    # Excludes candidate_001_review.STD.
    model_files = sorted(
        MODEL_DIR.glob("candidate_[0-9][0-9][0-9].STD")
    )

    if not model_files:
        raise FileNotFoundError(
            f"No candidate_###.STD files found in {MODEL_DIR}"
        )

    results = []
    errors = []

    print(f"Found {len(model_files)} numbered candidate models.\n")

    for index, file_path in enumerate(model_files, start=1):
        try:
            nodes, members, sections = parse_model(file_path)

            beam_volume, column_volume = calculate_volumes(
                nodes, members, sections
            )
            total_volume = beam_volume + column_volume

            if total_volume <= 0:
                raise ValueError("Calculated member volume is not positive.")

            objectives = calculate_objectives(total_volume)

            row = {
                "model": file_path.name,
                "nodes": len(nodes),
                "members": len(members),
                "section_assignments": len(sections),
                "beam_volume_m3": beam_volume,
                "column_stub_volume_m3": column_volume,
                "gross_member_concrete_volume_m3": total_volume,
                **objectives,
                "status": "PASS",
            }
            results.append(row)

            print(
                f"[{index}/{len(model_files)}] {file_path.name} | "
                f"Volume={total_volume:.3f} m3 | "
                f"Cost=Rs {objectives['estimated_total_cost_INR']:,.0f} | "
                f"Carbon="
                f"{objectives['estimated_total_carbon_kgCO2e']:,.1f} kg CO2e"
            )

        except Exception as exc:
            errors.append({
                "model": file_path.name,
                "error": str(exc),
            })

            print(
                f"[{index}/{len(model_files)}] "
                f"{file_path.name} | ERROR: {exc}"
            )

    results_file = OUTPUT_DIR / "objective_results.csv"
    errors_file = OUTPUT_DIR / "objective_errors.csv"

    if results:
        with results_file.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=list(results[0].keys())
            )
            writer.writeheader()
            writer.writerows(results)

    if errors:
        with errors_file.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=["model", "error"]
            )
            writer.writeheader()
            writer.writerows(errors)

    print("\n========== SUMMARY ==========")
    print(f"Models found: {len(model_files)}")
    print(f"Successful: {len(results)}")
    print(f"Errors: {len(errors)}")

    if results:
        print(f"Results saved to: {results_file}")

    if errors:
        print(f"Errors saved to: {errors_file}")

    print("\nLimitations:")
    print("- Gross member volume only; slab and foundation quantities are excluded.")
    print("- Beam-column intersection overlap is not deducted.")
    print("- Steel quantity is an assumed allowance, not a bar schedule.")
    print("- Cost and carbon factors are illustrative assumptions.")


if __name__ == "__main__":
    main()
