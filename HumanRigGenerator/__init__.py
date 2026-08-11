# __init__.py

bl_info = {
    "name": "RigAnim Studio: Character, Rigging & World Suite",
    "author": "Antigravity",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > RigAnim Studio",
    "description": "Professional 3D character rigging, auto-skinning, animation sequencing, multi-actor crowds, prop attacher, and world asset spawner.",
    "category": "Animation",
}

# Support recursive reloading for developer convenience
if "registration" in locals():
    import importlib
    importlib.reload(registration)
    importlib.reload(panel)
    importlib.reload(create_rig)
    importlib.reload(generate_spine)
    importlib.reload(generate_arms)
    importlib.reload(generate_hands)
    importlib.reload(generate_legs)
    importlib.reload(generate_feet)
    importlib.reload(generate_face)
    importlib.reload(generate_ik)
    importlib.reload(generate_fk)
    importlib.reload(constraints)
    importlib.reload(controllers)
    importlib.reload(markers)
    importlib.reload(animation)
    importlib.reload(generate_animal)
    importlib.reload(generate_bird)
    importlib.reload(auto_skin)
    importlib.reload(naming)
    importlib.reload(math)
    importlib.reload(bones)
    importlib.reload(mirror)
    importlib.reload(widgets)
    try:
        from . import mocap
        importlib.reload(mocap)
    except Exception:
        pass
else:
    import bpy
    from . import registration
    from .ui import panel
    from .operators import create_rig, generate_spine, generate_arms, generate_hands, generate_legs, generate_feet, generate_face, generate_ik, generate_fk, constraints, controllers, markers, animation, generate_animal, generate_bird, auto_skin
    from .utils import naming, math, bones, mirror, widgets
    try:
        from . import mocap
    except Exception:
        mocap = None

def register():
    registration.register()
    try:
        from . import mocap
        if hasattr(mocap, "register"):
            mocap.register()
    except Exception as e:
        print("[RigAnim Studio] Mocap module registration note:", e)

def unregister():
    try:
        from . import mocap
        if hasattr(mocap, "unregister"):
            mocap.unregister()
    except Exception:
        pass
    registration.unregister()

if __name__ == "__main__":
    register()
