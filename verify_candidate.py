


from pathlib import Path
import re

CANDIDATE_FOLDER = Path(r"C:\RCC AGAIN\candidate_models")


def read_model(path):
    if not path.exists():
        raise FileNotFoundError(path)

    return path.read_text(
        encoding="utf-8",
        errors="replace"
    )


def find_section(text, pattern):
    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )
    return match.groups() if match else None


def valid_number(value):
    """Accept valid integers and decimals, but reject '.'."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def inspect_candidate(path):
    text = read_model(path)

    print("\n" + "=" * 65)
    print(f"CANDIDATE: {path.name}")
    print("=" * 65)

    # Match only valid numeric tokens.
    number = r"(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"

    # Join STAAD continuation lines before checking properties.
    normalized = re.sub(r"-\s*\r?\n\s*", " ", text)

    beam = find_section(
        normalized,
        rf"^\s*1\s+TO\s+80\s+161\s+TO\s+235\s+PRIS\s+"
        rf"YD\s+({number})\s+ZD\s+({number})\s*$"
    )

    column = find_section(
        normalized,
        rf"^\s*81\s+TO\s+160\b.*?\bPRIS\s+"
        rf"YD\s+({number})\s+ZD\s+({number})\s*$"
    )

    if beam:
        yd = valid_number(beam[0])
        zd = valid_number(beam[1])

        if yd is not None and zd is not None:
            print(
                f"Beam section: YD={yd * 1000:.0f} mm, "
                f"ZD={zd * 1000:.0f} mm"
            )
        else:
            print("Beam section: INVALID DIMENSION")
    else:
        print("Beam section: NOT FOUND")

    if column:
        yd = valid_number(column[0])
        zd = valid_number(column[1])

        if yd is not None and zd is not None:
            print(
                f"Column section: YD={yd * 1000:.0f} mm, "
                f"ZD={zd * 1000:.0f} mm"
            )
        else:
            print("Column section: INVALID DIMENSION")
    else:
        print("Column section: NOT FOUND")

    # Find design commands only inside the concrete-design block.
    design_match = re.search(
        r"START CONCRETE DESIGN(.*?)END CONCRETE DESIGN",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not design_match:
        print("Concrete design block: NOT FOUND")
    else:
        design_text = design_match.group(1)
        print("Concrete design block: FOUND")

        for label in ("FC", "FYMAIN", "FYSEC"):
            match = re.search(
                rf"^\s*{label}\s+({number})\s+ALL\b",
                design_text,
                flags=re.IGNORECASE | re.MULTILINE
            )

            value = valid_number(match.group(1)) if match else None

            print(
                f"{label}: {value:g}"
                if value is not None
                else f"{label}: NOT FOUND OR INVALID"
            )

    print("Analysis status: NOT RUN BY THIS SCRIPT")


def main():
    if not CANDIDATE_FOLDER.exists():
        print(f"Folder not found: {CANDIDATE_FOLDER}")
        return

    candidates = sorted(
        path for path in CANDIDATE_FOLDER.glob("candidate_*.STD")
        if not path.stem.endswith("_review")
    )

    if not candidates:
        print("No candidate files found.")
        return

    print(f"Found {len(candidates)} candidate file(s).")

    for path in candidates:
        try:
            inspect_candidate(path)
        except Exception as error:
            print(f"Error reading {path.name}: {error}")


if __name__ == "__main__":
    main()


# read all three candidate files and extracted their section dimensions and design parameters.
#next step is to automate STAAD.Pro analysis for each candidate