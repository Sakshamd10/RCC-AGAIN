
# read_member_properties.py
# Read existing member properties without changing the STAAD model

from openstaadpy.os_analytical import connect

MODEL_PATH = (
    r"C:\Users\Corecard\Desktop\G+3 Staad"
    r"\G+3 RCC FINAL.STD"
)

def main():
    staad = connect(filePath=MODEL_PATH)
    geometry = staad.Geometry
    prop = staad.Property

    print("Connected model:", staad.GetSTAADFile())
    print("Base units:", staad.GetBaseUnit())

    member_ids = list(geometry.GetBeamList())

    print("\nTotal members:", len(member_ids))
    print("\nFirst 15 member properties")
    print("-" * 60)

    for member_id in member_ids[:15]:
        print(f"\nMember ID: {member_id}")

        for label, method in [
            ("Section name", prop.GetBeamSectionDisplayName),
            ("Section property ID", prop.GetBeamSectionPropertyRefNo),
            ("Section dimensions/values",
             prop.GetBeamSectionPropertyValuesEx),
            ("Material", prop.GetBeamMaterialName),
        ]:
            try:
                print(f"{label}: {method(int(member_id))}")
            except Exception as error:
                print(f"{label}: Could not retrieve ({error})")

    print("\nRead-only inspection complete.")
    print("No properties or loads were changed.")

if __name__ == "__main__":
    main()

