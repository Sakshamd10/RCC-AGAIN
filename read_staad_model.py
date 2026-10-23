# connect_G+3_model.py
# Connect to the intended G+3 STAAD model and inspect it

from openstaadpy.os_analytical import connect

MODEL_PATH = r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"

def main():
    try:
        print("Connecting to the specified G+3 model...")

        staad = connect(filePath=MODEL_PATH)

        print("\nSTAAD version:", staad.GetApplicationVersion())
        print("Connected model:", staad.GetSTAADFile())
        print("Model folder:", staad.GetSTAADFileFolder())
        print("Base units:", staad.GetBaseUnit())

        geometry = staad.Geometry

        print("\nNode count:", geometry.GetNodeCount())
        print("Member count:", geometry.GetMemberCount())

        print("\nFirst 10 node IDs:")
        print(list(geometry.GetNodeList())[:10])

        print("\nFirst 10 member IDs:")
        print(list(geometry.GetBeamList())[:10])

        print("\nConnection and read test completed.")
        print("No member properties or loads were changed.")

    except Exception as error:
        print("\nConnection or inspection failed:")
        print(repr(error))


if __name__ == "__main__":
    main()




# 
# inspect_staad_properties.py
# Inspect available property API methods without changing the model

import inspect
from openstaadpy.os_analytical import connect

staad = connect(
    filePath=r"C:\Users\Corecard\Desktop\G+3 Staad\G+3 RCC FINAL.STD"
)

print("Connected model:", staad.GetSTAADFile())

prop = staad.Property

print("\nProperty interface:", type(prop))
print("\nAvailable property methods:")

for name, obj in inspect.getmembers(prop):
    if name.startswith("_"):
        continue

    if callable(obj):
        try:
            signature = inspect.signature(obj)
        except (TypeError, ValueError):
            signature = "(signature unavailable)"

        print(f"{name}{signature}")

print("\nProperty inspection completed.")
print("No model changes were made.")
