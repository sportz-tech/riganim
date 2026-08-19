# operators/generate_arms.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_deform_name, get_org_name
from ..utils.mirror import mirror_bone

def generate_arm_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates the clavicle, upper arm, forearm, hand, and twist bones in EDIT mode (Left and Right)."""
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.85
    
    # Read markers
    p_spine_003 = get_marker_pos("Mkr_spine_003", (0.0, 0.0, 1.48 * h_scale), marker_positions)
    p_shoulder = get_marker_pos("Mkr_shoulder.L", (0.16 * w_scale, -0.03 * w_scale, 1.43 * h_scale), marker_positions)
    p_elbow = get_marker_pos("Mkr_elbow.L", (0.42 * w_scale, 0.04 * w_scale, 1.42 * h_scale), marker_positions)
    p_wrist = get_marker_pos("Mkr_wrist.L", (0.68 * w_scale, -0.03 * w_scale, 1.42 * h_scale), marker_positions)
    
    # Calculate hand direction and tail offset
    hand_dir = (p_wrist - p_elbow).normalized()
    default_hand_tail = p_wrist + hand_dir * (0.08 * w_scale)
    p_hand_tail = get_marker_pos("Mkr_middle.01.L", default_hand_tail, marker_positions)
    
    # Left side coordinates
    coords_left = {
        "shoulder.L":      (p_spine_003, p_shoulder, 0.0),
        "upper_arm.L":     (p_shoulder, p_elbow, 0.0),
        "forearm.L":       (p_elbow, p_wrist, 0.0),
        "hand.L":          (p_wrist, p_hand_tail, 0.0),
    }
    
    # Generate ORG- left bones
    left_org_names = []
    for base_name, (head, tail, roll) in coords_left.items():
        org_name = get_org_name(base_name)
        
        # Parent mapping
        parent = None
        if base_name == "shoulder.L":
            parent = get_org_name("spine.003")
        elif base_name == "upper_arm.L":
            parent = get_org_name("shoulder.L")
        elif base_name == "forearm.L":
            parent = get_org_name("upper_arm.L")
        elif base_name == "hand.L":
            parent = get_org_name("forearm.L")
            
        bone = create_bone(
            arm_data,
            org_name,
            mathutils.Vector(head),
            mathutils.Vector(tail),
            roll,
            parent_name=parent,
            use_connect=(parent is not None and base_name != "shoulder.L" and base_name != "upper_arm.L"),
            is_deform=False
        )
        
        if base_name == "hand.L":
            # Calculate hand normal for left side roll alignment
            p_index_base = get_marker_pos("Mkr_index.01.L", p_wrist + mathutils.Vector((0.08 * w_scale, -0.02 * w_scale, 0.005 * h_scale)), marker_positions)
            p_pinky_base = get_marker_pos("Mkr_pinky.01.L", p_wrist + mathutils.Vector((0.07 * w_scale, 0.04 * w_scale, -0.01 * h_scale)), marker_positions)
            dir_y = (p_hand_tail - p_wrist).normalized()
            dir_x = (p_index_base - p_pinky_base).normalized()
            hand_normal = dir_y.cross(dir_x).normalized()
            if hand_normal.length_squared > 0:
                bone.align_roll(hand_normal)
                
        assign_to_collection(arm_data, org_name, "Arms Org")
        left_org_names.append(org_name)
        
    # Mirror ORG- bones to right side
    right_org_names = []
    for left_org in left_org_names:
        right_bone = mirror_bone(arm_data, left_org)
        if right_bone:
            right_org_names.append(right_bone.name)
            assign_to_collection(arm_data, right_bone.name, "Arms Org")
            
    # Generate DEF- bones for both sides
    for side in [".L", ".R"]:
        side_suffix = side
        
        # Clavicle
        def_shoulder = get_deform_name(f"shoulder{side_suffix}")
        org_shoulder = get_org_name(f"shoulder{side_suffix}")
        sh_bone = arm_data.edit_bones.get(org_shoulder)
        create_bone(arm_data, def_shoulder, sh_bone.head.copy(), sh_bone.tail.copy(), sh_bone.roll, 
                    parent_name=get_deform_name("spine.003"), use_connect=False, is_deform=True)
        assign_to_collection(arm_data, def_shoulder, "Deform")
        
        # Upper Arm
        uarm_segments = bpy.context.scene.hrg_bbone_segments_arms if bpy.context.scene.hrg_use_bbone_arms else 1
        def_uarm = get_deform_name(f"upper_arm{side_suffix}")
        org_uarm = get_org_name(f"upper_arm{side_suffix}")
        uarm_bone = arm_data.edit_bones.get(org_uarm)
        
        create_bone(arm_data, def_uarm, uarm_bone.head.copy(), uarm_bone.tail.copy(), uarm_bone.roll,
                    parent_name=def_shoulder, use_connect=False, is_deform=True, 
                    bbone_segments=uarm_segments, bbone_easein=1.0, bbone_easeout=0.0)
        assign_to_collection(arm_data, def_uarm, "Deform")
        
        # Forearm
        farm_segments = bpy.context.scene.hrg_bbone_segments_arms if bpy.context.scene.hrg_use_bbone_arms else 1
        def_farm = get_deform_name(f"forearm{side_suffix}")
        org_farm = get_org_name(f"forearm{side_suffix}")
        farm_bone = arm_data.edit_bones.get(org_farm)
        
        create_bone(arm_data, def_farm, farm_bone.head.copy(), farm_bone.tail.copy(), farm_bone.roll,
                    parent_name=def_uarm, use_connect=False, is_deform=True, 
                    bbone_segments=farm_segments, bbone_easein=0.0, bbone_easeout=1.0)
        assign_to_collection(arm_data, def_farm, "Deform")
        
        # Hand
        def_hand = get_deform_name(f"hand{side_suffix}")
        org_hand = get_org_name(f"hand{side_suffix}")
        hand_bone = arm_data.edit_bones.get(org_hand)
        create_bone(arm_data, def_hand, hand_bone.head.copy(), hand_bone.tail.copy(), hand_bone.roll,
                    parent_name=def_farm, use_connect=False, is_deform=True)
        assign_to_collection(arm_data, def_hand, "Deform")
