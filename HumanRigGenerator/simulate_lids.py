import bpy
import mathutils

def main():
    print("=== SIMULATING EYELID SOLVER ===")
    
    mesh_obj = bpy.data.objects.get("CC_Base_Body")
    rig_obj = bpy.data.objects.get("CC_Base_Body_Rig")
    
    if not mesh_obj or not rig_obj:
        print("Mesh or Rig not found!")
        return
        
    rig_name = rig_obj.name
    prefix = rig_name[:-3] if rig_name.endswith("Rig") else ""
    print(f"Rig Name: {rig_name}, Prefix: '{prefix}'")
    
    for side in [".L", ".R"]:
        print(f"\n--- SIDE: {side} ---")
        eye_bone_name = f"DEF-eye{side}"
        up_lid_name = f"DEF-eyelid.upper{side}"
        low_lid_name = f"DEF-eyelid.lower{side}"
        head_bone_name = "DEF-head"
        
        eye_bone = rig_obj.data.bones.get(eye_bone_name)
        up_lid_bone = rig_obj.data.bones.get(up_lid_name)
        low_lid_bone = rig_obj.data.bones.get(low_lid_name)
        
        print(f"Bones: eye_bone={eye_bone}, up_lid_bone={up_lid_bone}, low_lid_bone={low_lid_bone}")
        
        if eye_bone and up_lid_bone and low_lid_bone:
            eye_pos = rig_obj.matrix_world @ eye_bone.head
            print(f"Eye position (World): {list(eye_pos)}")
            
            # Retrieve corner markers
            corner_inner_name = f"{prefix}Mkr_eye_corner_inner{side}"
            corner_outer_name = f"{prefix}Mkr_eye_corner_outer{side}"
            corner_inner = bpy.data.objects.get(corner_inner_name)
            corner_outer = bpy.data.objects.get(corner_outer_name)
            
            print(f"Looking for empties: inner={corner_inner_name} (found: {corner_inner is not None}), outer={corner_outer_name} (found: {corner_outer is not None})")
            
            p_inner = eye_pos + mathutils.Vector((-0.02, 0.0, 0.0)) if side == ".L" else eye_pos + mathutils.Vector((0.02, 0.0, 0.0))
            p_outer = eye_pos + mathutils.Vector((0.02, 0.0, 0.0)) if side == ".L" else eye_pos + mathutils.Vector((-0.02, 0.0, 0.0))
            
            if corner_inner:
                p_inner = corner_inner.location.copy()
            if corner_outer:
                p_outer = corner_outer.location.copy()
                
            width_inner = (p_inner - eye_pos).length
            width_outer = (p_outer - eye_pos).length
            
            R_max = max(0.040, max(width_inner, width_outer) * 1.3)
            print(f"width_inner: {width_inner}, width_outer: {width_outer}, R_max: {R_max}")
            
            # Count vertices in range
            mw = mesh_obj.matrix_world
            v_in_range = 0
            for v in mesh_obj.data.vertices:
                v_world = mw @ v.co
                dist = (v_world - eye_pos).length
                if dist < R_max:
                    v_in_range += 1
                    
            print(f"Vertices in range of eye: {v_in_range} / {len(mesh_obj.data.vertices)}")

if __name__ == "__main__":
    main()
