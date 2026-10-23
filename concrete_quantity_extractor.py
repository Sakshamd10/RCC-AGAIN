
import csv
import re
from pathlib import Path
from math import sqrt

# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(r"C:\RCC AGAIN")
CANDIDATE_DIR = PROJECT_DIR / "candidate_models"
OUTPUT_DIR = PROJECT_DIR / "batch_results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "concrete_volume_summary.csv"
DETAIL_FILE = OUTPUT_DIR / "concrete_volume_details.csv"
MISSING_FILE = OUTPUT_DIR / "missing_member_sections.csv"

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


# ============================================================
# MEMBER RANGE PARSER
# ============================================================

def expand_member_ids(text):
    tokens = text.split()
    result = []
    i = 0

    while i < len(tokens):
        if not tokens[i].isdigit():
            raise ValueError(
                f"Unexpected member ID token: {tokens[i]}"
            )

        first = int(tokens[i])

        if (
            i + 2 < len(tokens)
            and tokens[i + 1].upper() == "TO"
        ):
            last = int(tokens[i + 2])

            if last < first:
                raise ValueError("Invalid descending member range.")

            result.extend(range(first, last + 1))
            i += 3
        else:
            result.append(first)
            i += 1

    return result


# ============================================================
# READ STAAD MODEL
# ============================================================

def read_staad_model(model_path):
    text = model_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    nodes = {}
    members = {}
    sections = {}

    mode = None
    pending_property_ids = []

    node_pattern = re.compile(
        rf"^\s*(\d+)\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})"
    )

    member_pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)"
    )

    section_pattern = re.compile(
        rf"\bPRIS\b.*?\bYD\s+({NUMBER})\s+ZD\s+({NUMBER})",
        re.IGNORECASE
    )

    # Commands that end a coordinate, incidence or property block.
    command_pattern = re.compile(
        r"^(UNIT|DEFINE|CONSTANTS|SUPPORTS|LOAD|PERFORM|"
        r"FINISH|END|ELEMENT|START|CONSTRAINT|GROUP|FLOOR|"
        r"REPEAT|SET|PRINT|CHECK|SELECT|PARAMETER|CHANGE|"
        r"LOAD LIST|LOAD COMBINATION|SELFWEIGHT|"
        r"MEMBER RELEASE|MEMBER TRUSS|MEMBER TENSION|"
        r"MEMBER COMPRESSION|JOINT LOAD|MEMBER LOAD|"
        r"FLOOR LOAD|ELEMENT LOAD|WIND LOAD|"
        r"DEFINE MATERIAL|MATERIAL CONSTANTS)\b",
        re.IGNORECASE
    )

    def process_property_line(line):
        """
        Read section assignments that may continue across lines,
        e.g. member IDs on one line and PRIS YD/ZD on the next.
        """
        nonlocal pending_property_ids

        match = section_pattern.search(line)

        if match:
            prefix = line[:match.start()].strip()

            current_ids = (
                expand_member_ids(prefix)
                if prefix else []
            )

            assigned_ids = pending_property_ids + current_ids

            yd = float(match.group(1))
            zd = float(match.group(2))

            for member_id in assigned_ids:
                sections[member_id] = (yd, zd)

            pending_property_ids = []
            return

        # Member IDs only: keep them for the following continuation.
        if re.fullmatch(
            r"\s*\d+(?:\s+(?:TO\s+)?\d+)*\s*",
            line,
            re.IGNORECASE
        ):
            pending_property_ids.extend(expand_member_ids(line))
            return

        # Unknown property syntax: don't assign guessed dimensions.
        pending_property_ids = []

    for raw_line in text.splitlines():
        # Remove comments and ignore blank lines.
        line = raw_line.split("*", 1)[0].strip()

        if not line:
            continue

        upper = line.upper()

        # Identify the beginning of each relevant block.
        if upper.startswith("JOINT COORDINATES"):
            mode = "nodes"
            line = re.sub(
                r"^JOINT COORDINATES\b",
                "",
                line,
                flags=re.IGNORECASE
            ).strip()

            if not line:
                continue

        elif upper.startswith("MEMBER INCIDENCES"):
            mode = "members"
            line = re.sub(
                r"^MEMBER INCIDENCES\b",
                "",
                line,
                flags=re.IGNORECASE
            ).strip()

            if not line:
                continue

        elif upper.startswith("MEMBER PROPERTY"):
            mode = "properties"
            pending_property_ids = []

            line = re.sub(
                r"^MEMBER PROPERTY(?:\s+\w+)?",
                "",
                line,
                count=1,
                flags=re.IGNORECASE
            ).strip()

            if not line:
                continue

        elif command_pattern.match(upper):
            mode = None
            pending_property_ids = []
            continue

        # Read coordinates.
        if mode == "nodes":
            match = node_pattern.match(line)

            if match:
                node_id = int(match.group(1))
                nodes[node_id] = tuple(
                    float(match.group(i))
                    for i in (2, 3, 4)
                )

        # Read member start/end nodes.
        elif mode == "members":
            match = member_pattern.match(line)

            if match:
                member_id, start_node, end_node = map(
                    int, match.groups()
                )

                members[member_id] = (
                    start_node,
                    end_node
                )

        # Read rectangular PRIS sections.
        elif mode == "properties":
            process_property_line(line)

    if not nodes:
        raise ValueError("No joint coordinates were found.")

    if not members:
        raise ValueError("No member incidences were found.")

    return nodes, members, sections


# ============================================================
# CALCULATE GROSS MEMBER VOLUME
# ============================================================

def calculate_volumes(nodes, members, sections):
    details = []
    missing = []

    for member_id, (start_node, end_node) in sorted(members.items()):

        if start_node not in nodes or end_node not in nodes:
            missing.append({
                "member_id": member_id,
                "reason": "Missing node coordinates"
            })
            continue

        if member_id not in sections:
            missing.append({
                "member_id": member_id,
                "reason": "No recognized section assignment"
            })
            continue

        x1, y1, z1 = nodes[start_node]
        x2, y2, z2 = nodes[end_node]

        length = sqrt(
            (x2 - x1) ** 2
            + (y2 - y1) ** 2
            + (z2 - z1) ** 2
        )

        yd, zd = sections[member_id]

        if length <= 0 or yd <= 0 or zd <= 0:
            missing.append({
                "member_id": member_id,
                "reason": "Invalid length or section dimension"
            })
            continue

        area = yd * zd
        volume = length * area

        details.append({
            "member_id": member_id,
            "start_node": start_node,
            "end_node": end_node,
            "length_m": round(length, 6),
            "YD_m": yd,
            "ZD_m": zd,
            "area_m2": round(area, 6),
            "gross_volume_m3": round(volume, 6)
        })

    return details, missing


# ============================================================
# PROCESS ONE MODEL
# ============================================================

def process_candidate(model_path):
    nodes, members, sections = read_staad_model(model_path)

    details, missing = calculate_volumes(
        nodes,
        members,
        sections
    )

    total_volume = sum(
        item["gross_volume_m3"]
        for item in details
    )

    for item in details:
        item["candidate"] = model_path.stem

    for item in missing:
        item["candidate"] = model_path.stem

    summary = {
        "candidate": model_path.stem,
        "model_file": str(model_path),
        "nodes_read": len(nodes),
        "members_read": len(members),
        "section_assignments_read": len(sections),
        "members_calculated": len(details),
        "members_missing": len(missing),
        "gross_supported_volume_m3": round(total_volume, 6),
        "status": (
            "CHECK REQUIRED"
            if missing
            else "All members have recognized sections"
        )
    }

    return summary, details, missing


# ============================================================
# BATCH PROCESS ALL CANDIDATES
# ============================================================

def main():
    model_files = sorted(
        path
        for path in CANDIDATE_DIR.glob("candidate_*.STD")
        if not path.stem.lower().endswith("_review")
    )

    if not model_files:
        raise FileNotFoundError(
            f"No candidate_*.STD files found in {CANDIDATE_DIR}"
        )

    summaries = []
    all_details = []
    all_missing = []

    for index, model_path in enumerate(model_files, start=1):
        print(
            f"\n[{index}/{len(model_files)}] "
            f"Processing {model_path.name}"
        )

        try:
            summary, details, missing = process_candidate(model_path)

            summaries.append(summary)
            all_details.extend(details)
            all_missing.extend(missing)

            print("Nodes:", summary["nodes_read"])
            print("Members:", summary["members_read"])
            print(
                "Section assignments:",
                summary["section_assignments_read"]
            )
            print("Calculated members:", summary["members_calculated"])
            print("Missing members:", summary["members_missing"])
            print(
                "Gross supported volume:",
                f"{summary['gross_supported_volume_m3']:.3f} m3"
            )
            print("Status:", summary["status"])

        except Exception as error:
            print(f"ERROR: {error}")

            summaries.append({
                "candidate": model_path.stem,
                "model_file": str(model_path),
                "status": f"FAILED: {error}"
            })

    def write_csv(path, rows):
        if not rows:
            return

        fields = list(dict.fromkeys(
            key for row in rows for key in row.keys()
        ))

        with path.open(
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fields,
                extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(rows)

    write_csv(SUMMARY_FILE, summaries)
    write_csv(DETAIL_FILE, all_details)
    write_csv(MISSING_FILE, all_missing)

    print("\n========== EXTRACTION COMPLETE ==========")
    print("Candidates processed:", len(model_files))
    print("Summary CSV:", SUMMARY_FILE)
    print("Member details CSV:", DETAIL_FILE)
    print("Missing sections CSV:", MISSING_FILE)

    print(
        "\nImportant: volumes are gross estimates for recognized "
        "rectangular PRIS members. Check model units, all section "
        "assignments, slabs, foundations and member intersections "
        "before using these totals for cost or carbon optimization."
    )


if __name__ == "__main__":
    main()
