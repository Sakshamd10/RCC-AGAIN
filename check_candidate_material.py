# openstaad_check_candidate_material.py
#check the material and design commands in a candidate STAAD.Pro model

from pathlib import Path
import re
import subprocess
import os

# ==================================================
# CONFIGURATION
# ==================================================

ORIGINAL_MODEL = Path(
    r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"
)

INPUT_CANDIDATE = Path(
    r"C:\RCC AGAIN\candidate_models\candidate_001.STD"
)

OUTPUT_FOLDER = Path(
    r"C:\RCC AGAIN\candidate_models"
)

OUTPUT_CANDIDATE = OUTPUT_FOLDER / "candidate_001_review.STD"

# Intended grades
CONCRETE_GRADE_MPA = 40
STEEL_GRADE_MPA = 415

# Optional: set this to the actual location of your
# STAAD.Pro executable if it is not on the default path.
STAAD_EXE = None


# ==================================================
# READ AND INSPECT
# ==================================================

def read_file(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.read_text(
        encoding="utf-8",
        errors="replace"
    )


def print_material_and_design_sections(text):
    lines = text.splitlines()

    print("\n--- MATERIAL DEFINITION ---")
    in_material = False

    for line in lines:
        upper = line.strip().upper()

        if upper.startswith("DEFINE MATERIAL START"):
            in_material = True

        if in_material:
            print(line)

        if in_material and upper.startswith("END DEFINE MATERIAL"):
            in_material = False

    print("\n--- CONCRETE DESIGN PARAMETERS ---")
    in_design = False

    for line in lines:
        upper = line.strip().upper()

        if upper.startswith("START CONCRETE DESIGN"):
            in_design = True

        if in_design:
            print(line)

        if in_design and upper.startswith("END CONCRETE DESIGN"):
            in_design = False


# ==================================================
# CHECK THE CURRENT DESIGN COMMANDS
# ==================================================

def inspect_design_commands(text):
    print("\n--- GRADE COMMAND CHECK ---")

    for line in text.splitlines():
        upper = line.strip().upper()

        if re.match(r"^FC\s+", upper):
            print("Concrete design command:", line.strip())

        elif re.match(r"^FYMAIN\s+", upper):
            print("Main reinforcement command:", line.strip())

        elif re.match(r"^FYSEC\s+", upper):
            print("Secondary reinforcement command:", line.strip())

        elif "STRENGTH FCU" in upper:
            print("Material strength definition:", line.strip())


# ==================================================
# PREPARE A SEPARATE REVIEW COPY
# ==================================================

def prepare_review_copy(candidate_text):
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # We do not guess or rewrite FCU, E, or density.
    # Keep the candidate design commands as generated,
    # but warn if they differ from the intended values.
    expected_fc = CONCRETE_GRADE_MPA * 1000
    expected_fy = STEEL_GRADE_MPA * 1000

    fc_match = re.search(
        r"(?im)^\s*FC\s+([\d.]+)\s+ALL\b",
        candidate_text
    )

    fy_match = re.search(
        r"(?im)^\s*FYMAIN\s+([\d.]+)\s+ALL\b",
        candidate_text
    )

    fys_match = re.search(
        r"(?im)^\s*FYSEC\s+([\d.]+)\s+ALL\b",
        candidate_text
    )

    print("\n--- PREPARATION CHECK ---")

    if fc_match:
        actual_fc = float(fc_match.group(1))
        print(f"FC found: {actual_fc:g}; intended numeric value: {expected_fc}")
    else:
        print("WARNING: FC command not found.")

    if fy_match:
        actual_fy = float(fy_match.group(1))
        print(f"FYMAIN found: {actual_fy:g}; intended numeric value: {expected_fy}")
    else:
        print("WARNING: FYMAIN command not found.")

    if fys_match:
        actual_fys = float(fys_match.group(1))
        print(f"FYSEC found: {actual_fys:g}; intended numeric value: {expected_fy}")
    else:
        print("WARNING: FYSEC command not found.")

    print(
        "\nIMPORTANT: These comparisons check numeric values only. "
        "They do not prove STAAD.Pro interprets the grades correctly."
    )

    # Save a review copy without altering the input candidate.
    OUTPUT_CANDIDATE.write_text(
        candidate_text,
        encoding="utf-8"
    )

    print(f"\nReview copy saved:\n{OUTPUT_CANDIDATE}")
    return OUTPUT_CANDIDATE


# ==================================================
# OPEN IN STAAD.PRO
# ==================================================

def open_in_staad(path):
    print("\n--- OPENING CANDIDATE ---")

    try:
        if STAAD_EXE:
            subprocess.Popen([STAAD_EXE, str(path)])
        else:
            # Opens the .STD file with its registered application.
            os.startfile(str(path))

        print("The candidate file was sent to its registered application.")
        print("Confirm that it opens in STAAD.Pro and inspect the model.")
    except Exception as error:
        print("Could not open the file automatically.")
        print("Open this file manually in STAAD.Pro:")
        print(path)
        print("Reason:", error)


# ==================================================
# MAIN
# ==================================================

def main():
    try:
        original_text = read_file(ORIGINAL_MODEL)
        candidate_text = read_file(INPUT_CANDIDATE)

        print("=" * 65)
        print("ORIGINAL MODEL: MATERIAL SETTINGS")
        print("=" * 65)
        print_material_and_design_sections(original_text)

        print("\n" + "=" * 65)
        print("CANDIDATE MODEL: MATERIAL SETTINGS")
        print("=" * 65)
        print_material_and_design_sections(candidate_text)

        inspect_design_commands(candidate_text)

        review_path = prepare_review_copy(candidate_text)

        print("\n" + "=" * 65)
        print("NEXT MANUAL CHECKS IN STAAD.PRO")
        print("=" * 65)
        print("1. Confirm the model opens without input errors.")
        print("2. Check member dimensions and material assignments.")
        print("3. Verify material and design commands in the output.")
        print("4. Run analysis only after the commands are validated.")
        print("5. Check analysis warnings and concrete design results.")
        print("6. Do not treat a successful opening as proof of safety.")

        open_in_staad(review_path)

    except Exception as error:
        print("\nERROR:", error)


if __name__ == "__main__":
    main()
