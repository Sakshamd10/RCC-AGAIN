
from pathlib import Path
import re

MODEL_PATH = Path(
    r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"
)

text = MODEL_PATH.read_text(
    encoding="utf-8",
    errors="replace"
)

keywords = (
    "UNIT",
    "DEFINE MATERIAL",
    "ISOTROPIC",
    "CONCRETE",
    "STRENGTH",
    "FCU",
    "E ",
    "POISSON",
    "DENSITY",
    "START CONCRETE DESIGN",
    "CODE INDIAN",
    "FC ",
    "FYMAIN",
    "FYSEC",
    "END CONCRETE DESIGN",
)

print("=" * 65)
print("MATERIAL AND DESIGN COMMANDS IN ORIGINAL MODEL")
print("=" * 65)

for number, line in enumerate(text.splitlines(), start=1):
    stripped = line.strip()
    upper = stripped.upper()

    if any(keyword in upper for keyword in keywords):
        print(f"{number:4}: {stripped}")

print("\nInspection complete. The original file was not modified.")
