import os
import zipfile

addon_name = "MotionCaptureTransfer"
zip_path = f"../{addon_name}.zip"

if os.path.exists(zip_path):
    try:
        os.remove(zip_path)
    except PermissionError:
        print(f"Warning: Could not delete the existing {zip_path}. Overwriting...")

print(f"Packaging {addon_name}...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        # Exclude pycache and hidden directories
        if any(x in root for x in ['__pycache__', '.git', '.github']):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            # Exclude script itself, logs, and zip files
            if file == 'zip_addon.py' or file.endswith('.log') or file.endswith('.zip'):
                continue
            
            # The top-level folder inside zip must be addon_name for Blender to install it correctly
            arcname = os.path.join(addon_name, os.path.relpath(file_path, '.')).replace('\\', '/')
            zipf.write(file_path, arcname)
            print(f"  Added: {arcname}")

print(f"Addon packaged successfully to: {os.path.abspath(zip_path)}")
