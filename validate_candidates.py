
from pathlib import Path
import re
import csv

BASE_DIR = Path(r"C:\RCC AGAIN")
MODEL_DIR = BASE_DIR / "candidate_models"
OUTPUT_DIR = BASE_DIR / "batch_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def expand_ids(text):
    tokens = text.upper().replace("-", " ").split()
    result = []
    i = 0

    while i < len(tokens):
        if not tokens[i].isdigit():
            i += 1
            continue

        start = int(tokens[i])

        if (
            i + 2 < len(tokens)
            and tokens[i + 1] == "TO"
            and tokens[i + 2].isdigit()
        ):
            end = int(tokens[i + 2])
            result.extend(range(start, end + 1))
            i += 3
        else:
            result.append(start)
            i += 1

    return result


def parse_model(path):
    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    nodes = {}
    members = {}
    sections = {}

    mode = None
    property_pending = ""

    for raw in lines:
        line = raw.strip()
        upper = line.upper()

        if not line or upper.startswith("!"):
            continue

        if upper.startswith("JOINT COORDINATES"):
            mode = "nodes"
            continue

        if upper.startswith("MEMBER INCIDENCES"):
            mode = "members"
            continue

        if upper == "MEMBER PROPERTY":
            mode = "properties"
            property_pending = ""
            continue

        if mode in ("nodes", "members"):
            if re.match(
                r"^(DEFINE MATERIAL|CONSTANTS|SUPPORTS|"
                r"DEFINE WIND|DEFINE IS1893|LOAD\b|"
                r"MEMBER PROPERTY|PERFORM\b|FINISH\b|END\b)",
                upper
            ):
                mode = None
                continue

            for record in line.split(";"):
                parts = record.split()

                try:
                    if mode == "nodes" and len(parts) >= 4:
                        nodes[int(parts[0])] = tuple(
                            map(float, parts[1:4])
                        )

                    elif mode == "members" and len(parts) >= 3:
                        members[int(parts[0])] = (
                            int(parts[1]),
                            int(parts[2])
                        )
                except (ValueError, IndexError):
                    continue

            continue

        if mode == "properties":
            # A new STAAD command ends the property block.
            if re.match(r"^[A-Z][A-Z0-9_]*(?:\s|$)", upper):
                mode = None
                property_pending = ""
                continue

            property_pending += " " + line

            if property_pending.rstrip().endswith("-"):
                property_pending = (
                    property_pending.rstrip()[:-1] + " "
                )
                continue

            match = re.search(
                r"\bPRIS\s+YD\s+([0-9.eE+-]+)"
                r"\s+ZD\s+([0-9.eE+-]+)",
                property_pending,
                re.IGNORECASE
            )

            if match:
                depth = float(match.group(1))
                width = float(match.group(2))

                ids_text = property_pending[:match.start()]

                for member_id in expand_ids(ids_text):
                    sections[member_id] = (depth, width)

            property_pending = ""

    return nodes, members, sections


def main():
    files = sorted(MODEL_DIR.glob("*.STD"))

    if not files:
        raise FileNotFoundError(
            f"No STAAD files found in {MODEL_DIR}"
        )

    results = []

    print(f"Found {len(files)} candidate files.")

    for index, path in enumerate(files, 1):
        print(f"\n[{index}/{len(files)}] {path.name}")

        try:
            nodes, members, sections = parse_model(path)

            missing_nodes = sorted({
                node
                for start, end in members.values()
                for node in (start, end)
                if node not in nodes
            })

            missing_sections = sorted(
                set(members) - set(sections)
            )

            invalid_sections = sorted(
                member_id
                for member_id, (depth, width) in sections.items()
                if depth <= 0 or width <= 0
            )

            results.append({
                "model": path.name,
                "nodes": len(nodes),
                "members": len(members),
                "section_assignments": len(sections),
                "missing_nodes": len(missing_nodes),
                "missing_sections": len(missing_sections),
                "missing_section_ids": ";".join(
                    map(str, missing_sections)
                ),
                "invalid_sections": ";".join(
                    map(str, invalid_sections)
                ),
                "status": (
                    "REVIEW"
                    if missing_nodes
                    or missing_sections
                    or invalid_sections
                    or not nodes
                    or not members
                    else "PASS"
                )
            })

            print(f"Nodes: {len(nodes)}")
            print(f"Members: {len(members)}")
            print(f"Section assignments: {len(sections)}")
            print(f"Members missing sections: {len(missing_sections)}")
            print(f"Status: {results[-1]['status']}")

        except Exception as error:
            results.append({
                "model": path.name,
                "nodes": 0,
                "members": 0,
                "section_assignments": 0,
                "missing_nodes": 0,
                "missing_sections": 0,
                "missing_section_ids": "",
                "invalid_sections": "",
                "status": f"ERROR: {error}"
            })
            print(f"ERROR: {error}")

    report = OUTPUT_DIR / "candidate_validation.csv"

    with report.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys())
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 45)
    print("VALIDATION FINISHED")
    print(f"Models checked: {len(results)}")
    print(f"PASS: {sum(r['status'] == 'PASS' for r in results)}")
    print(f"REVIEW: {sum(r['status'] == 'REVIEW' for r in results)}")
    print(
        f"ERROR: {sum(str(r['status']).startswith('ERROR:') for r in results)}"
    )
    print(f"Report saved to: {report}")


if __name__ == "__main__":
    main()
