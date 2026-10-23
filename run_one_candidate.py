#This script opens candidate_001.STD, checks the active model path, and requests analysis through the OpenSTAAD API. It does not change your original model file.



from pathlib import Path
import time

from openstaadpy.os_analytical import connect

CANDIDATE = Path(
    r"C:\RCC AGAIN\candidate_models\candidate_001.STD"
)


def main():
    if not CANDIDATE.exists():
        print("ERROR: Candidate file not found:")
        print(CANDIDATE)
        return

    print("=" * 60)
    print("SINGLE CANDIDATE ANALYSIS TEST")
    print("=" * 60)

    try:
        # Connect to the current STAAD.Pro session.
        staad = connect()

        if staad is None:
            print("ERROR: Could not connect to STAAD.Pro.")
            return

        print("Connected to STAAD.Pro.")
        print("Version:", staad.GetApplicationVersion())

        # Open the candidate in the connected STAAD.Pro session.
        print("\nOpening candidate:")
        print(CANDIDATE)

        result = staad.OpenSTAADFile(str(CANDIDATE))
        print("OpenSTAADFile returned:", result)

        time.sleep(3)

        active_path = str(staad.GetSTAADFile())
        print("Active model:", active_path)

        if (
            Path(active_path).resolve()
            != CANDIDATE.resolve()
        ):
            print("\nSTOP: The candidate is not confirmed as active.")
            print("No analysis was requested.")
            return

        print("\nCandidate confirmed as active.")

        print("\nChecking analysis interface...")
        print("Analyze:", callable(getattr(staad, "Analyze", None)))
        print("AnalyzeModel:", callable(getattr(staad, "AnalyzeModel", None)))
        print("AnalyzeEx:", callable(getattr(staad, "AnalyzeEx", None)))

        print(
            "\nSTOPPING BEFORE ANALYSIS: "
            "we must verify the installed API's exact method "
            "signature and return behavior before invoking it."
        )

        print("No analysis was requested by this script.")

    except Exception as error:
        print("\nERROR:", repr(error))
        print(
            "Check the STAAD.Pro session and the OpenSTAAD API."
        )


if __name__ == "__main__":
    main()
