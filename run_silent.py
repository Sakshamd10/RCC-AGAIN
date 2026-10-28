import subprocess
import glob
import os
from pathlib import Path

# 1. Define the most common paths where SProStaad.exe lives
# We check 2026, 2025, 2024, 2023, and CONNECT Edition
possible_folders = [
    r"C:\Program Files\Bentley\Engineering\STAAD.Pro 2026\STAAD\SProStaad",
    r"C:\Program Files\Bentley\Engineering\STAAD.Pro 2025\STAAD\SProStaad",
    r"C:\Program Files\Bentley\Engineering\STAAD.Pro 2024\STAAD\SProStaad",
    r"C:\Program Files\Bentley\Engineering\STAAD.Pro 2023\STAAD\SProStaad",
    r"C:\Program Files\Bentley\Engineering\STAAD.Pro CONNECT Edition\STAAD\SProStaad",
]

STAAD_EXE = None
for folder in possible_folders:
    exe_path = os.path.join(folder, "SProStaad.exe")
    if os.path.exists(exe_path):
        STAAD_EXE = exe_path
        break

if not STAAD_EXE:
    print("ERROR: Could not find SProStaad.exe in the default Bentley folders.")
    print("Please open File Explorer, navigate to your Bentley Engineering folder,")
    print("find the 'SProStaad' folder inside your STAAD.Pro version, and copy the path.")
    exit()

print(f"Found STAAD Engine at: {STAAD_EXE}")

# 2. Find all your models
models = glob.glob(r"C:\RCC AGAIN\candidate_models\candidate_*.STD")

for std_file in models:
    anl_file = std_file.replace(".STD", ".ANL")
    
    if os.path.exists(anl_file):
        print(f"[SKIP] Already done: {os.path.basename(std_file)}")
        continue
        
    print(f"[RUNNING] Analyzing {os.path.basename(std_file)} ...")
    
    # 3. THE CRITICAL FIX: We must pass 'STAAD' before the file path, 
    # and use the /s flag for silent operation.
    # Syntax: SProStaad.exe STAAD "filename.std" /s
    try:
        subprocess.run(
            [STAAD_EXE, "STAAD", std_file, "/s"], 
            check=True, 
            stdout=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        print(f"  -> Error running STAAD on {os.path.basename(std_file)}")

print("\nAll done!")
