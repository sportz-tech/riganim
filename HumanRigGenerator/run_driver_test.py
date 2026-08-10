import sys
import os
import shutil

addon_dir = "f:\\blenderaddon"
if addon_dir not in sys.path:
    sys.path.append(addon_dir)
    
sub_dir = "f:\\blenderaddon\\HumanRigGenerator"
if sub_dir not in sys.path:
    sys.path.append(sub_dir)

import bpy

def main():
    user_addons_dir = bpy.utils.user_resource('SCRIPTS', path="addons")
    target_dir = os.path.join(user_addons_dir, "HumanRigGenerator")
    
    # Copy modified files
    src_dir = "f:\\blenderaddon\\HumanRigGenerator"
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(src_dir, target_dir)
    print("Successfully copied modified files to Blender AppData addons directory!")
    
    bpy.ops.preferences.addon_disable(module="HumanRigGenerator")
    import HumanRigGenerator
    import importlib
    importlib.reload(HumanRigGenerator)
    bpy.ops.preferences.addon_enable(module="HumanRigGenerator")
    
    # Get all meshes we want to skin: body, eye, teeth, tongue
    mesh_names = ["CC_Base_Body", "CC_Base_Eye", "CC_Base_Teeth", "CC_Base_Tongue"]
    meshes = []
    bpy.ops.object.select_all(action='DESELECT')
    for name in mesh_names:
        obj = bpy.data.objects.get(name)
        if obj:
            meshes.append(obj)
            obj.select_set(True)
            
    if not meshes:
        print("No meshes found to skin!")
        return
        
    print(f"Selected meshes for skinning: {[m.name for m in meshes]}")
    # Make active mesh CC_Base_Body to trigger generate
    body_obj = bpy.data.objects.get("CC_Base_Body")
    bpy.context.view_layer.objects.active = body_obj
    
    # Run generate rig (this triggers auto_skin_mesh internally on all selected objects)
    bpy.ops.object.generate_human_rig()
    
    rig_obj = bpy.data.objects.get("CC_Base_Body_Rig")
    if not rig_obj:
        print("Rig not found!")
        return
        
    print("\n=== VERIFYING PARENTING & VERTEX GROUPS ===")
    for obj in meshes:
        print(f"\nMesh: {obj.name}")
        print(f"  Parent: {obj.parent.name if obj.parent else 'None'}")
        print(f"  Parent Type: {obj.parent_type}")
        
        # Print vertex groups and counts
        vg_counts = {}
        for vg in obj.vertex_groups:
            vg_counts[vg.name] = 0
        for v in obj.data.vertices:
            for g in v.groups:
                vg_name = obj.vertex_groups[g.group].name
                if g.weight > 0.0:
                    vg_counts[vg_name] = vg_counts.get(vg_name, 0) + 1
                    
        for vg_name, count in sorted(vg_counts.items()):
            if count > 0:
                print(f"  Group: {vg_name}, Vertices: {count}")

if __name__ == "__main__":
    main()
