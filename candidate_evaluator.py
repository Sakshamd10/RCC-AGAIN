"""
candidate_evaluator.py
Turns one STAAD candidate (candidate_NNN.STD + candidate_NNN.ANL +
candidate_NNN_structural_results.json) into a dict with cost, carbon,
and feasibility checks (strength + serviceability).
"""

import json
import math
import re
import sys
from pathlib import Path

# ======================================================================
# RATES AND CARBON FACTORS
# ======================================================================
CONCRETE = {          # cost Rs/m3 ; carbon kgCO2e per kg of concrete
    "M25": dict(cost=6500, co2=0.150),   # PLACEHOLDER
    "M30": dict(cost=7000, co2=0.165),   # PLACEHOLDER
    "M35": dict(cost=7500, co2=0.177),   # PLACEHOLDER
    "M40": dict(cost=8000, co2=0.188),   # your value
}
STEEL = {             # cost Rs/kg ; carbon kgCO2e per kg
    "Fe415": dict(cost=65, co2=1.99),    # your value
    "Fe500": dict(cost=67, co2=1.99),    # PLACEHOLDER
    "Fe550": dict(cost=69, co2=1.99),    # PLACEHOLDER
}
CONCRETE_DENSITY = 2400.0     # kg/m3
DETAILING_FACTOR = 1.00       # 1.10–1.20 for laps/anchorage

# Serviceability limits (typical IS 456 values)
DRIFT_LIMIT = 1.0 / 250.0         # max inter-storey drift
DEFLECTION_LIMIT = 1.0 / 250.0    # max beam deflection / span

# Optional slab inclusion
INCLUDE_SLAB = False
SLAB_AREA_M2 = 300.0
SLAB_LEVELS = 4
SLAB_THICK_M = 0.150
SLAB_STEEL_KG_M3 = 50.0


# ======================================================================
# 1. READ THE .STD FILE
# ======================================================================
def expand_ids(text):
    tok, out, i = text.split(), [], 0
    while i < len(tok):
        if i + 2 < len(tok) and tok[i + 1].upper() == "TO":
            out += range(int(tok[i]), int(tok[i + 2]) + 1)
            i += 3
        else:
            out.append(int(tok[i]))
            i += 1
    return out


def read_std(path):
    text = Path(path).read_text(encoding="latin-1").replace("\r", "")

    jc = text.split("JOINT COORDINATES")[1].split("MEMBER INCIDENCES")[0]
    nodes = {
        int(a): (float(x), float(y), float(z))
        for a, x, y, z in re.findall(
            r"(\d+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;", jc
        )
    }

    mi = text.split("MEMBER INCIDENCES")[1].split("DEFINE MATERIAL")[0]
    members = {
        int(m): (int(a), int(b))
        for m, a, b in re.findall(r"(\d+)\s+(\d+)\s+(\d+)\s*;", mi)
    }

    prop = text.split("MEMBER PROPERTY")[1].split("CONSTANTS")[0]
    prop = re.sub(r"-\s*\n", " ", prop)     # join STAAD continuation lines
    sections = {}
    for ids, yd, zd in re.findall(
        r"([\d\sTOto]+?)PRIS\s+YD\s+([\d.]+)\s+ZD\s+([\d.]+)", prop
    ):
        for m in expand_ids(ids.upper()):
            sections[m] = (float(yd), float(zd))

    fc = float(re.search(r"^\s*FC\s+([\d.]+)", text, re.M).group(1)) / 1000
    fy = float(re.search(r"^\s*FYMAIN\s+([\d.]+)", text, re.M).group(1)) / 1000
    return nodes, members, sections, fc, fy


def concrete_volumes(nodes, members, sections):
    vol = {"beam": 0.0, "column": 0.0}
    col_ids, missing = set(), []
    beam_lengths = []

    for m, (a, b) in members.items():
        if m not in sections:
            missing.append(m)
            continue
        pa, pb = nodes[a], nodes[b]
        L = math.dist(pa, pb)
        kind = "column" if abs(pa[1] - pb[1]) > 1e-3 else "beam"
        if kind == "column":
            col_ids.add(m)
        else:
            beam_lengths.append(L)
        yd, zd = sections[m]
        vol[kind] += L * yd * zd

    return vol, col_ids, missing, beam_lengths


# ======================================================================
# 2. READ STAAD'S IS 456 DESIGN OUTPUT (.ANL)
# ======================================================================
def bar_area(d):
    return math.pi * d * d / 4


RHO = 7850e-9     # kg per mm3 of steel


def steel_from_anl(anl_path, col_ids):
    t = Path(anl_path).read_text(encoding="latin-1", errors="replace")
    beam_kg = col_kg = 0.0
    nb = nc = skipped = 0
    max_ir = 0.0
    fails = len(re.findall(r"FAIL", t, re.I))

    for blk in re.split(r"B E A M\s+N O\.\s+", t)[1:]:
        L = float(re.search(r"LENGTH:\s+([\d.]+) mm", blk).group(1))
        w, D = map(float, re.search(
            r"SIZE:\s+([\d.]+) mm X\s+([\d.]+) mm", blk
        ).groups())
        cov = float(re.search(r"COVER:\s+([\d.]+)", blk).group(1))
        k = blk.find("SUMMARY OF PROVIDED REINF. AREA")
        s = blk[k:k + 900]
        top = re.search(r"TOP\s+(.*)", s).group(1)
        bot = re.search(r"BOTTOM\s+(.*)", s).group(1)

        def area(line):
            return [int(n) * bar_area(float(d))
                    for n, d in re.findall(r"(\d+)-(\d+)d", line)]

        ta, ba = area(top), area(bot)
        if len(ta) != 5 or len(ba) != 5:
            skipped += 1
            continue

        wts = [.125, .25, .25, .25, .125]
        longi = sum(wi * (a + b) for wi, a, b in zip(wts, ta, ba)) * L

        legs = re.search(r"(\d+) legged\s+(\d+)d", s)
        sp = re.findall(r"@\s*(\d+) mm c/c", s)[:5]
        stir = 0.0
        if legs and sp:
            spacing = sum(map(float, sp)) / len(sp)
            stir = (L / spacing) * 2 * (
                (w - 2 * cov) + (D - 2 * cov)
            ) * bar_area(float(legs.group(2)))

        beam_kg += (longi + stir) * RHO
        nb += 1

    for blk in re.split(r"C O L U M N\s+N O\.\s+", t)[1:]:
        mid = int(re.match(r"\s*(\d+)", blk).group(1))
        if mid not in col_ids:
            continue
        L = float(re.search(r"LENGTH:\s+([\d.]+) mm", blk).group(1))
        w, D = map(float, re.search(
            r"CROSS SECTION:\s+([\d.]+) mm X\s+([\d.]+) mm", blk
        ).groups())
        m = re.search(r"Provide\s+(\d+)\s*-\s*(\d+) dia\.", blk)
        tie = re.search(
            r"Provide\s+(\d+) mm dia\. rectangular ties @ (\d+) mm", blk
        )
        ir = re.search(r"INTERACTION RATIO:\s+([\d.]+)", blk)
        if ir:
            max_ir = max(max_ir, round(float(ir.group(1)), 3))
        if not m:
            skipped += 1
            continue

        main = int(m.group(1)) * bar_area(float(m.group(2))) * L
        ties = 0.0
        if tie:
            ties = (L / float(tie.group(2))) * 2 * (
                (w - 80) + (D - 80)
            ) * bar_area(float(tie.group(1)))

        col_kg += (main + ties) * RHO
        nc += 1

    return dict(
        beam_steel_kg=beam_kg * DETAILING_FACTOR,
        column_steel_kg=col_kg * DETAILING_FACTOR,
        beams_read=nb,
        columns_read=nc,
        blocks_skipped=skipped,
        max_column_interaction_ratio=max_ir,
        fail_messages=fails,
    )


# ======================================================================
# 3. SERVICEABILITY CHECKS (drift + deflection)
# ======================================================================
def serviceability_checks(base, beam_lengths):
    """
    Read candidate_NNN_structural_results.json and compute max drift
    and max deflection ratios. Automatically handles inches/mm.
    """
    results_path = base.with_name(base.stem + "_structural_results.json")

    inf = float("inf")
    empty = dict(
        max_drift_ratio=inf,
        max_deflection_ratio=inf,
        drift_limit=DRIFT_LIMIT,
        deflection_limit=DEFLECTION_LIMIT,
        serviceability_status="NO_DATA",
    )

    if not results_path.exists():
        return empty

    try:
        data = json.loads(results_path.read_text())
    except Exception:
        return empty

    disp = data.get("nodal_displacements", [])
    if not disp:
        return empty

    # ---- Storey height from the .STD joint Y coordinates ----
    try:
        nodes, _, _, _, _ = read_std(base.with_suffix(".STD"))
        ys = sorted({round(p[1], 3) for p in nodes.values()})
        if len(ys) > 1:
            storey_h = min(
                ys[i + 1] - ys[i] for i in range(len(ys) - 1)
            )
            total_h = max(ys) - min(ys)
        else:
            storey_h, total_h = 3.0, 3.0
    except Exception:
        storey_h, total_h = 3.0, 12.0

    # ---- Max horizontal displacement magnitude ----
    max_drift_raw = 0.0
    max_vert_raw = 0.0
    for rec in disp:
        r = rec.get("result") or []
        if len(r) < 3:
            continue
        dx, dy, dz = r[0], r[1], r[2]
        d = math.sqrt(dx * dx + dz * dz)
        max_drift_raw = max(max_drift_raw, d)
        max_vert_raw = max(max_vert_raw, abs(dy))

    # ---- UNIT CONVERSION FIX ----
    # If raw is > 1.0, it's in inches. If > 100, it's in mm.
    # Otherwise, it's already in meters.
    if max_drift_raw > 100.0:
        max_drift_m = max_drift_raw / 1000.0   # mm to m
        max_vert_m = max_vert_raw / 1000.0
    elif max_drift_raw > 1.0:
        max_drift_m = max_drift_raw * 0.0254   # inches to m
        max_vert_m = max_vert_raw * 0.0254
    else:
        max_drift_m = max_drift_raw            # already meters
        max_vert_m = max_vert_raw

    # Normalise
    drift_ratio_total = max_drift_m / total_h if total_h > 0 else inf
    drift_ratio_storey = max_drift_m / storey_h if storey_h > 0 else inf
    max_drift_ratio = max(drift_ratio_total, drift_ratio_storey)

    # Span: worst beam length in the model, or 5 m fallback
    span = max(beam_lengths) if beam_lengths else 5.0
    deflection_ratio = max_vert_m / span if span > 0 else inf

    return dict(
        max_drift_ratio=round(max_drift_ratio, 6),
        max_deflection_ratio=round(deflection_ratio, 6),
        drift_limit=DRIFT_LIMIT,
        deflection_limit=DEFLECTION_LIMIT,
        serviceability_status="OK",
    )


# ======================================================================
# 4. EVALUATE ONE CANDIDATE
# ======================================================================
def evaluate(base):
    """base: Path without extension, e.g. Path('.../candidate_001')."""
    base = Path(base)

    nodes, members, sections, fc, fy = read_std(base.with_suffix(".STD"))
    vol, col_ids, missing, beam_lengths = concrete_volumes(
        nodes, members, sections
    )
    grade = f"M{fc:g}"
    steel_grade = f"Fe{fy:g}"
    V = vol["beam"] + vol["column"]

    out = dict(
        candidate=base.name,
        concrete_grade=grade,
        steel_grade=steel_grade,
        beam_volume_m3=round(vol["beam"], 3),
        column_volume_m3=round(vol["column"], 3),
        members_without_section=missing,
    )

    anl = base.with_suffix(".ANL")
    if not anl.exists():
        out["status"] = "NO .ANL FILE: analyse + design in STAAD first"
        return out

    steel = steel_from_anl(anl, col_ids)
    W = steel["beam_steel_kg"] + steel["column_steel_kg"]

    if INCLUDE_SLAB:
        Vs = SLAB_AREA_M2 * SLAB_LEVELS * SLAB_THICK_M
        V += Vs
        W += Vs * SLAB_STEEL_KG_M3

    if grade not in CONCRETE:
        out["status"] = f"UNKNOWN CONCRETE GRADE {grade}"
        return out
    if steel_grade not in STEEL:
        out["status"] = f"UNKNOWN STEEL GRADE {steel_grade}"
        return out

    c = CONCRETE[grade]
    s = STEEL[steel_grade]

    strength_ok = (
        steel["fail_messages"] == 0
        and steel["max_column_interaction_ratio"] <= 1.0
        and steel["blocks_skipped"] == 0
    )

    service = serviceability_checks(base, beam_lengths)
    drift_ok = service["max_drift_ratio"] <= service["drift_limit"]
    deflection_ok = (
        service["max_deflection_ratio"] <= service["deflection_limit"]
    )
    serviceability_ok = drift_ok and deflection_ok

    out.update(
        steel,
        concrete_volume_m3=round(V, 3),
        steel_kg=round(W, 1),
        steel_kg_per_m3=round(W / V, 1) if V > 0 else 0.0,
        cost_inr=round(V * c["cost"] + W * s["cost"]),
        carbon_kgco2e=round(
            V * CONCRETE_DENSITY * c["co2"] + W * s["co2"]
        ),
        max_drift_ratio=service["max_drift_ratio"],
        drift_limit=service["drift_limit"],
        max_deflection_ratio=service["max_deflection_ratio"],
        deflection_limit=service["deflection_limit"],
        strength_ok=strength_ok,
        serviceability_ok=serviceability_ok,
        feasible_staad_design=(strength_ok and serviceability_ok),
        status=(
            "OK"
            if (strength_ok and serviceability_ok)
            else "INFEASIBLE:"
            + (" strength" if not strength_ok else "")
            + (" serviceability" if not serviceability_ok else "")
        ),
    )
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python candidate_evaluator.py candidate_models/candidate_001")
        sys.exit(1)
    base = Path(sys.argv[1])
    res = evaluate(base)
    print(json.dumps(res, indent=2))
    base.with_name(base.name + "_evaluation.json").write_text(
        json.dumps(res, indent=2)
    )