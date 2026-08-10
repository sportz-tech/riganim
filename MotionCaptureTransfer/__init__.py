# __init__.py
import sys
import site

# Ensure Blender searches user site-packages where pip --user installs files
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.append(user_site)


bl_info = {
    "name": "Motion Capture & Transfer",
    "author": "Antigravity",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Human Rig",
    "description": "Captures facial and body motion (live camera or pre-recorded video) using OpenCV and MediaPipe and transfers it to the HumanRigGenerator armature.",
    "category": "Animation",
}

# Support recursive reloading for developer convenience
if "dependency_installer" in locals():
    import importlib
    importlib.reload(dependency_installer)
    importlib.reload(mocap_processor)
    importlib.reload(ui_panel)
else:
    from . import dependency_installer
    from . import mocap_processor
    from . import ui_panel

def register():
    dependency_installer.register()
    mocap_processor.register()
    ui_panel.register()

def unregister():
    dependency_installer.unregister()
    mocap_processor.unregister()
    ui_panel.unregister()

if __name__ == "__main__":
    register()
