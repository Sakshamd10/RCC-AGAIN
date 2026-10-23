


import inspect
from pathlib import Path

from openstaadpy.os_analytical import connect


EXPECTED_MODEL = Path(
    r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"
)


def main():
    print("=" * 60)
    print("STAAD.PRO AUTOMATION CONNECTION TEST")
    print("=" * 60)

    try:
        # Connect to the currently active STAAD.Pro session.
        staad = connect()

        if staad is None:
            print("ERROR: No connection object returned.")
            print("Open STAAD.Pro and load a model first.")
            return

        print("\nConnection successful.")
        print("Object type:", type(staad))

        # Read STAAD.Pro session information.
        for label, method_name in [
            ("STAAD version", "GetApplicationVersion"),
            ("Active model path", "GetSTAADFile"),
            ("Model folder", "GetSTAADFileFolder"),
            ("Base units", "GetBaseUnit"),
        ]:
            method = getattr(staad, method_name, None)

            if callable(method):
                try:
                    print(f"{label}: {method()}")
                except Exception as error:
                    print(f"{label}: Could not read ({error})")
            else:
                print(f"{label}: API method unavailable")

        # Inspect available interfaces.
        print("\nAvailable interfaces:")
        for name in dir(staad):
            if not name.startswith("_"):
                print(" ", name)

        # Inspect Geometry methods without calling them.
        geometry = getattr(staad, "Geometry", None)

        if geometry is not None:
            print("\nGeometry interface:", type(geometry))
            print("Available Geometry methods:")

            for name, obj in inspect.getmembers(geometry):
                if name.startswith("_"):
                    continue

                if callable(obj):
                    try:
                        signature = inspect.signature(obj)
                    except (TypeError, ValueError):
                        signature = "(signature unavailable)"

                    print(f"  {name}{signature}")
        else:
            print("\nGeometry interface is unavailable.")

        print("\nConnection test completed.")
        print("No model changes were made.")

    except Exception as error:
        print("\nCONNECTION FAILED")
        print(repr(error))
        print(
            "Check that STAAD.Pro is running and a model "
            "is open in the active session."
        )


if __name__ == "__main__":
    main()
