# staad_candidate_generator.py
#
# Batch generator for candidate STAAD models.
#
# Usage:
#   python staad_candidate_generator.py --count 60 --seed 1
#
# Writes candidate_002.STD ... candidate_061.STD into candidate_models/
# (never overwrites an existing candidate_NNN.STD).
#
# Uses stratified sampling so the 60 points spread across the space
# rather than clustering.

from pathlib import Path
import argparse
import random
import re

from design_parameters import DESIGN_PARAMETERS

MODEL_PATH = Path(
    r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"
)
OUTPUT_DIR = Path(r"C:\RCC AGAIN\candidate_models")


def _all_values(cfg):
    return list(range(cfg["min"], cfg["max"] + 1, cfg["step"]))


def _stratified_sample(values, n, rng):
    if n >= len(values):
        out = list(values) * (n // len(values) + 1)
        rng.shuffle(out)
        return out[:n]
    step = len(values) / n
    picks = []
    for i in range(n):
        lo = int(i * step)
        hi = int((i + 1) * step)
        picks.append(rng.choice(values[lo:hi]))
    return picks


def _replace_once(pattern, replacement, text, description):
    updated, count = re.subn(
        pattern, replacement, text, count=1, flags=re.MULTILINE
    )
    if count != 1:
        raise RuntimeError(
            f"Could not uniquely update {description}; "
            f"matches found: {count}. No candidate written."
        )
    return updated


def _next_candidate_path():
    index = 1
    while True:
        path = OUTPUT_DIR / f"candidate_{index:03d}.STD"
        if not path.exists():
            return path
        index += 1


def build_candidate(template_text, p):
    """
    p: dict with beam_width_mm, beam_depth_mm, column_width_mm,
       column_depth_mm, concrete_grade, concrete_mpa,
       steel_grade, steel_mpa
    """
    text = template_text

    beam_yd = p["beam_depth_mm"] / 1000.0
    beam_zd = p["beam_width_mm"] / 1000.0
    col_yd = p["column_depth_mm"] / 1000.0
    col_zd = p["column_width_mm"] / 1000.0

    # Beam section
    beam_pat = (
        r"(?m)^(\s*1\s+TO\s+80\s+161\s+TO\s+235\s+PRIS\s+)"
        r"YD\s+[\d.]+\s+ZD\s+[\d.]+\s*$"
    )
    text = _replace_once(
        beam_pat,
        rf"\g<1>YD {beam_yd:.3f} ZD {beam_zd:.3f}",
        text,
        "beam property",
    )

    # Column section (handles the STAAD continuation line)
    col_pat = (
        r"(?ms)^(\s*81\s+TO\s+160\b.*?TO\s+272\s*-\s*\n"
        r"\s*273\s+PRIS\s+)YD\s+[\d.]+\s+ZD\s+[\d.]+\s*$"
    )
    if re.search(col_pat, text):
        text = _replace_once(
            col_pat,
            rf"\g<1>YD {col_yd:.3f} ZD {col_zd:.3f}",
            text,
            "column property",
        )
    else:
        simple_col_pat = (
            r"(?m)^(\s*81\s+TO\s+160\s+PRIS\s+)"
            r"YD\s+[\d.]+\s+ZD\s+[\d.]+\s*$"
        )
        text = _replace_once(
            simple_col_pat,
            rf"\g<1>YD {col_yd:.3f} ZD {col_zd:.3f}",
            text,
            "simple column property",
        )

    # Grades
    fc = p["concrete_mpa"] * 1000
    fy = p["steel_mpa"] * 1000
    text = _replace_once(
        r"(?im)^(\s*FC\s+)[\d.]+(\s+ALL\s*)$",
        rf"\g<1>{fc}\g<2>",
        text,
        "FC command",
    )
    text = _replace_once(
        r"(?im)^(\s*FYMAIN\s+)[\d.]+(\s+ALL\s*)$",
        rf"\g<1>{fy}\g<2>",
        text,
        "FYMAIN command",
    )
    text = _replace_once(
        r"(?im)^(\s*FYSEC\s+)[\d.]+(\s+ALL\s*)$",
        rf"\g<1>{fy}\g<2>",
        text,
        "FYSEC command",
    )
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"STAAD model not found: {MODEL_PATH}")

    template = MODEL_PATH.read_text(encoding="utf-8", errors="replace")
    rng = random.Random(args.seed)

    bw_v = _all_values(DESIGN_PARAMETERS["beam_width_mm"])
    bd_v = _all_values(DESIGN_PARAMETERS["beam_depth_mm"])
    cw_v = _all_values(DESIGN_PARAMETERS["column_width_mm"])
    cd_v = _all_values(DESIGN_PARAMETERS["column_depth_mm"])
    conc = list(DESIGN_PARAMETERS["concrete_grade"].items())
    stl = list(DESIGN_PARAMETERS["reinforcing_steel_grade"].items())

    bws = _stratified_sample(bw_v, args.count, rng)
    bds = _stratified_sample(bd_v, args.count, rng)
    cws = _stratified_sample(cw_v, args.count, rng)
    cds = _stratified_sample(cd_v, args.count, rng)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0

    for i in range(args.count):
        bw = min(bws[i], bds[i])
        bd = max(bws[i], bds[i])
        cw = min(cws[i], cds[i])
        cd = max(cws[i], cds[i])

        cname, cmpa = conc[rng.randrange(len(conc))]
        sname, smpa = stl[rng.randrange(len(stl))]

        p = dict(
            beam_width_mm=bw,
            beam_depth_mm=bd,
            column_width_mm=cw,
            column_depth_mm=cd,
            concrete_grade=cname,
            concrete_mpa=cmpa,
            steel_grade=sname,
            steel_mpa=smpa,
        )

        try:
            text = build_candidate(template, p)
        except RuntimeError as err:
            print(f"[{i+1}/{args.count}] SKIP: {err}")
            continue

        path = _next_candidate_path()
        path.write_text(text, encoding="utf-8")
        written += 1
        print(
            f"[{i+1}/{args.count}] {path.name}: "
            f"beam {bw}x{bd}, column {cw}x{cd}, {cname}, {sname}"
        )

    print()
    print("=" * 55)
    print(f"Wrote {written} candidate(s) into {OUTPUT_DIR}")
    print("Next: python run_batch.py")
    print("=" * 55)


if __name__ == "__main__":
    main()