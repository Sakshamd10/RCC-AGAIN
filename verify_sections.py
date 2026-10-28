
from pathlib import Path
import re

MODEL_PATH = Path(
    r"C:\RCC AGAIN\candidate_models\candidate_001.STD"
)


def expand_member_ids(text):
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
            result.extend(range(start, int(tokens[i + 2]) + 1))
            i += 3
        else:
            result.append(start)
            i += 1

    return result


def read_explicit_sections(path):
    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    sections = {}
    in_property_block = False
    pending = ""

    for raw_line in lines:
        line = raw_line.strip()
        upper = line.upper()

        if not line or upper.startswith("!"):
            continue

        if upper == "MEMBER PROPERTY":
            in_property_block = True
            pending = ""
            continue

        if not in_property_block:
            continue

        # Stop at the next STAAD command.
        if upper == "CONSTANTS" or upper.startswith("CONSTANTS "):
            break

        pending += " " + line

        # STAAD continuation line.
        if pending.rstrip().endswith("-"):
            pending = pending.rstrip()[:-1] + " "
            continue

        match = re.search(
            r"\bPRIS\s+YD\s+([0-9.eE+-]+)"
            r"\s+ZD\s+([0-9.eE+-]+)",
            pending,
            re.IGNORECASE
        )

        if match:
            depth = float(match.group(1))
            width = float(match.group(2))

            ids_text = pending[:match.start()]

            for member_id in expand_member_ids(ids_text):
                sections[member_id] = (depth, width)

        pending = ""

    return sections


sections = read_explicit_sections(MODEL_PATH)

beams = list(range(1, 81)) + list(range(161, 236))

columns = (
    list(range(81, 161))
    + [236, 237, 239, 241]
    + list(range(246, 250))
    + list(range(254, 258))
    + list(range(262, 266))
    + list(range(270, 274))
)

print("Model:", MODEL_PATH.name)
print("Explicit section assignments:", len(sections))
print("Beam assignments:", sum(m in sections for m in beams))
print("Column/stub assignments:", sum(m in sections for m in columns))
print("Beam section:", sections.get(1))
print("Column section:", sections.get(81))
print("Member 273 section:", sections.get(273))

print("\nUnexpected member IDs:")
print(sorted(set(sections) - set(beams) - set(columns)))

print("\nMissing beam IDs:")
print(sorted(set(beams) - set(sections)))

print("\nMissing column/stub IDs:")
print(sorted(set(columns) - set(sections)))




from pathlib import Path

path = Path(
    r"C:\RCC AGAIN\candidate_models\candidate_001.STD"
)

lines = path.read_text(
    encoding="utf-8",
    errors="replace"
).splitlines()

start = None
end = None

for i, line in enumerate(lines):
    if line.strip().upper() == "MEMBER PROPERTY":
        start = i

    elif start is not None and line.strip().upper() == "CONSTANTS":
        end = i
        break

print("SCRIPT VERSION: DEBUG_PROPERTY_BLOCK_V1")
print("Property start line:", start + 1 if start is not None else None)
print("Property end line:", end + 1 if end is not None else None)

if start is None or end is None:
    raise RuntimeError("Could not locate MEMBER PROPERTY and CONSTANTS.")

print("\n===== EXACT MEMBER PROPERTY BLOCK =====")

for i in range(start, end):
    print(f"{i + 1}: {lines[i]}")

print("\nExpected assignments from this block:")
print("Beams: 80 + 75 = 155")
print("Columns/stubs: 80 + 1 + 1 + 1 + 1 + 4 + 4 + 4 + 4 = 100 IDs listed")
print("Unique expected section assignments: 176")
