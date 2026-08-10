import os
import zipfile

zip_path = '../HumanRigGenerator.zip'
if os.path.exists(zip_path):
    try:
        os.remove(zip_path)
    except PermissionError:
        print("Warning: Could not delete the existing zip file because it is locked by Blender. Trying to overwrite it directly...")

print("Packaging HumanRigGenerator...")
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
            arcname = os.path.relpath(file_path, '..').replace('\\', '/')
            zipf.write(file_path, arcname)
            print(f"  Added: {arcname}")

print("Addon packaged successfully to:", os.path.abspath(zip_path))
