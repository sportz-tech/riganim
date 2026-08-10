import sys
import os

addon_dir = "f:\\blenderaddon"
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

import bpy
import mathutils

def main():
    import HumanRigGenerator
    try:
        HumanRigGenerator.register()
    except:
        pass
        
    mesh_obj = bpy.data.objects.get("CC_Base_Body")
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    
    bpy.ops.object.generate_human_rig()
    rig_obj = bpy.data.objects.get("CC_Base_Body_Rig")
    
    if not rig_obj:
        print("Rig not found!")
        return
        
    print("=== COMPARING REST BONE VS POSE BONE ===")
    for name in ["DEF-head", "DEF-eye.L"]:
        b_rest = rig_obj.data.bones.get(name)
        b_pose = rig_obj.pose.bones.get(name)
        
        if b_rest and b_pose:
            print(f"Bone: {name}")
            print(f"  Rest Bone Head: {list(b_rest.head)}")
            print(f"  Pose Bone Head: {list(b_pose.head)}")
            print(f"  Rest Bone Matrix Local translation: {list(b_rest.matrix_local.to_translation())}")

if __name__ == "__main__":
    main()
