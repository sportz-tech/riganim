# operators/generate_legs.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_deform_name, get_org_name
from ..utils.mirror import mirror_bone

def generate_leg_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates thigh, shin, foot, toe, and twist bones in EDIT mode (Left and Right)."""
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.9  # Keep hips wide for female

    # Read markers
    p_thigh = get_marker_pos("Mkr_thigh.L", (0.12 * w_scale, -0.02, 0.86 * h_scale), marker_positions)
    p_knee = get_marker_pos("Mkr_knee.L", (0.13 * w_scale, 0.03, 0.48 * h_scale), marker_positions)
    p_ankle = get_marker_pos("Mkr_ankle.L", (0.13 * w_scale, -0.05, 0.09 * h_scale), marker_positions)
    p_toe_tip = get_marker_pos("Mkr_foot_toe.L", (0.13 * w_scale, 0.16, 0.02 * h_scale), marker_positions)
    
    # Calculate foot ball position (halfway between ankle and toe tip on Z-level of toe tip)
    p_ball = mathutils.Vector((
        p_toe_tip.x,
        p_ankle.y * 0.5 + p_toe_tip.y * 0.5,
        p_toe_tip.z
    ))

    # Left side coordinates
    coords_left = {
        "thigh.L":      (p_thigh, p_knee, 0.0),
        "shin.L":       (p_knee, p_ankle, 0.0),
        "foot.L":       (p_ankle, p_ball, 0.0),
        "toe.L":        (p_ball, p_toe_tip, 0.0),
    }

    # Generate ORG- left bones
    left_org_names = []
    for base_name, (head, tail, roll) in coords_left.items():
        org_name = get_org_name(base_name)

        # Parent mapping
        parent = None
        if base_name == "thigh.L":
            parent = get_org_name("pelvis")
        elif base_name == "shin.L":
            parent = get_org_name("thigh.L")
        elif base_name == "foot.L":
            parent = get_org_name("shin.L")
        elif base_name == "toe.L":
            parent = get_org_name("foot.L")

        bone = create_bone(
            arm_data,
            org_name,
            mathutils.Vector(head),
            mathutils.Vector(tail),
            roll,
            parent_name=parent,
            use_connect=(parent is not None and base_name != "thigh.L" and base_name != "foot.L"),
            is_deform=False
        )
        assign_to_collection(arm_data, org_name, "Legs Org")
        left_org_names.append(org_name)

    # Mirror ORG- bones to right side
    right_org_names = []
    for left_org in left_org_names:
        right_bone = mirror_bone(arm_data, left_org)
        if right_bone:
            right_org_names.append(right_bone.name)
            assign_to_collection(arm_data, right_bone.name, "Legs Org")

    # Generate DEF- bones for both sides
    for side in [".L", ".R"]:
        side_suffix = side

        # Thigh
        thigh_segments = bpy.context.scene.hrg_bbone_segments_legs if bpy.context.scene.hrg_use_bbone_legs else 1
        def_thigh = get_deform_name(f"thigh{side_suffix}")
        org_thigh = get_org_name(f"thigh{side_suffix}")
        thigh_bone = arm_data.edit_bones.get(org_thigh)
        
        create_bone(arm_data, def_thigh, thigh_bone.head.copy(), thigh_bone.tail.copy(), thigh_bone.roll,
                    parent_name=get_deform_name("pelvis"), use_connect=False, is_deform=True, 
                    bbone_segments=thigh_segments, bbone_easein=1.0, bbone_easeout=0.0)
        assign_to_collection(arm_data, def_thigh, "Deform")
        
        # Shin
        shin_segments = bpy.context.scene.hrg_bbone_segments_legs if bpy.context.scene.hrg_use_bbone_legs else 1
        def_shin = get_deform_name(f"shin{side_suffix}")
        org_shin = get_org_name(f"shin{side_suffix}")
        shin_bone = arm_data.edit_bones.get(org_shin)
        
        create_bone(arm_data, def_shin, shin_bone.head.copy(), shin_bone.tail.copy(), shin_bone.roll,
                    parent_name=def_thigh, use_connect=False, is_deform=True, 
                    bbone_segments=shin_segments, bbone_easein=0.0, bbone_easeout=1.0)
        assign_to_collection(arm_data, def_shin, "Deform")
        
        # Foot
        def_foot = get_deform_name(f"foot{side_suffix}")
        org_foot = get_org_name(f"foot{side_suffix}")
        foot_bone = arm_data.edit_bones.get(org_foot)
        create_bone(arm_data, def_foot, foot_bone.head.copy(), foot_bone.tail.copy(), foot_bone.roll,
                    parent_name=def_shin, use_connect=False, is_deform=True)
        assign_to_collection(arm_data, def_foot, "Deform")
        
        # Toe
        def_toe = get_deform_name(f"toe{side_suffix}")
        org_toe = get_org_name(f"toe{side_suffix}")
        toe_bone = arm_data.edit_bones.get(org_toe)
        create_bone(arm_data, def_toe, toe_bone.head.copy(), toe_bone.tail.copy(), toe_bone.roll,
                    parent_name=def_foot, use_connect=False, is_deform=True)
        assign_to_collection(arm_data, def_toe, "Deform")
