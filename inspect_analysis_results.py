
import inspect
from openstaadpy.os_analytical import connect


def main():
    print("=" * 60)
    print("INSPECT STAAD.PRO ANALYSIS RESULTS API")
    print("=" * 60)

    try:
        staad = connect()

        if staad is None:
            print("ERROR: Could not connect to STAAD.Pro.")
            return

        print("\nSTAAD version:", staad.GetApplicationVersion())
        print("Active model:", staad.GetSTAADFile())

        # Inspect analysis status and diagnostic methods.
        print("\n--- ANALYSIS STATUS METHODS ---")

        methods = [
            "GetAnalysisStatus",
            "GetAnalysisErrorMessages",
            "GetAnalysisWarningMessages",
            "IsAnalyzing",
        ]

        for name in methods:
            method = getattr(staad, name, None)
            print(f"\n{name}:")

            if not callable(method):
                print("Not available")
                continue

            try:
                print("Signature:", inspect.signature(method))
            except (TypeError, ValueError):
                print("Signature unavailable")

            print("Documentation:", inspect.getdoc(method))

        # Inspect result-retrieval methods.
        print("\n--- OUTPUT INTERFACE ---")
        output = getattr(staad, "Output", None)

        if output is None:
            print("Output interface unavailable.")
            return

        for name, obj in inspect.getmembers(output):
            if name.startswith("_") or not callable(obj):
                continue

            try:
                signature = inspect.signature(obj)
            except (TypeError, ValueError):
                signature = "(signature unavailable)"

            print(f"{name}{signature}")

        print("\nInspection completed.")
        print("No model was opened or modified.")
        print("No analysis was started.")

    except Exception as error:
        print("\nInspection failed:", repr(error))


if __name__ == "__main__":
    main()
