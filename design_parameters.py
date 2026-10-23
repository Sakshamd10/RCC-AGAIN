# design_parameters.py
# Design variables for G+3 RCC building optimization.
#
# Search space: 7 x 9 x 6 x 6 x 2 (M30,M40) x 2 (Fe500,Fe550)
#             = 1,512 combinations.
#
# M25 and Fe415 are deliberately excluded. If your project brief
# allows M25 / Fe415, add them back — but explain in the methodology
# why the objective is no longer carbon vs cost alone (the optimizer
# will simply pick the lowest grade for carbon).

DESIGN_PARAMETERS = {

    "beam_width_mm": {
        "min": 250,
        "max": 400,
        "step": 25,
    },

    "beam_depth_mm": {
        "min": 400,
        "max": 600,
        "step": 25,
    },

    "column_width_mm": {
        "min": 350,
        "max": 600,
        "step": 50,
    },

    "column_depth_mm": {
        "min": 350,
        "max": 600,
        "step": 50,
    },

    "concrete_grade": {
        "M30": 30,
        "M40": 40,
    },

    "reinforcing_steel_grade": {
        "Fe500": 500,
        "Fe550": 550,
    },
}


if __name__ == "__main__":
    print("G+3 RCC Building — Design Parameters")
    print("=" * 45)
    for name, values in DESIGN_PARAMETERS.items():
        print(f"\n{name}: {values}")
    print("\nLoaded.")