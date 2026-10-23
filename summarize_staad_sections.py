
from collections import defaultdict
from openstaadpy.os_analytical import connect

MODEL_PATH = r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"

staad = connect(filePath=MODEL_PATH)
geometry = staad.Geometry
prop = staad.Property

groups = defaultdict(list)

for member_id in geometry.GetBeamList():
    member_id = int(member_id)

    try:
        name = prop.GetBeamSectionDisplayName(member_id)
        property_id = prop.GetBeamSectionPropertyRefNo(member_id)
        material = prop.GetBeamMaterialName(member_id)

        key = (str(name), str(property_id), str(material))
        groups[key].append(member_id)

    except Exception as error:
        print(f"Could not inspect member {member_id}: {error}")

print("Connected model:", staad.GetSTAADFile())
print("Total members:", geometry.GetMemberCount())
print("\nSECTION SUMMARY")
print("=" * 65)

for (name, property_id, material), members in sorted(groups.items()):
    print(f"\nSection: {name}")
    print(f"Property ID: {property_id}")
    print(f"Material: {material}")
    print(f"Number of members: {len(members)}")
    print(f"Member IDs: {members}")

print("\nRead-only summary completed.")
