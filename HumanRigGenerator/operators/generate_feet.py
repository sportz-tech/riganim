# operators/generate_feet.py
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_mch_name
from ..utils.mirror import mirror_bone

def generate_foot_mechanism_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates the mechanism bones for foot roll (Left and Right)."""
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.85
    
    # Read markers
    ankle_pos = get_marker_pos("Mkr_ankle.L", (0.13 * w_scale, -0.05 * w_scale, 0.09 * h_scale), marker_positions)
    toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.13 * w_scale, 0.16 * w_scale, 0.02 * h_scale), marker_positions)
    
    # Calculate ball and heel pivots
    ball_pos = mathutils.Vector((
        toe_pos.x,
        ankle_pos.y * 0.5 + toe_pos.y * 0.5,
        toe_pos.z
    ))
    heel_pos = mathutils.Vector((
        ankle_pos.x,
        ankle_pos.y - 0.07 * w_scale,
        toe_pos.z
    ))
    
    # 1. Left side bones
    # Heel: from heel_pos to ball_pos
    create_bone(arm_data, get_mch_name("foot_roll_heel.L"), heel_pos, ball_pos, 0.0, is_deform=False)
    # Toe: from toe_pos to heel_pos
    create_bone(arm_data, get_mch_name("foot_roll_toe.L"), toe_pos, heel_pos, 0.0, is_deform=False)
    # Ball: from ball_pos to ankle_pos
    create_bone(arm_data, get_mch_name("foot_roll_ball.L"), ball_pos, ankle_pos, 0.0, is_deform=False)
    # Ankle helper: from ankle_pos upward (serves as the head-target for shin_IK)
    ankle_tail = ankle_pos.copy()
    ankle_tail.z += 0.05
    create_bone(arm_data, get_mch_name("foot_roll_ankle.L"), ankle_pos, ankle_tail, 0.0, is_deform=False)
    
    # Hierarchy setup
    # Parent heel to toe
    arm_data.edit_bones[get_mch_name("foot_roll_heel.L")].parent = arm_data.edit_bones[get_mch_name("foot_roll_toe.L")]
    # Parent ball to heel
    arm_data.edit_bones[get_mch_name("foot_roll_ball.L")].parent = arm_data.edit_bones[get_mch_name("foot_roll_heel.L")]
    # Parent ankle helper to ball
    arm_data.edit_bones[get_mch_name("foot_roll_ankle.L")].parent = arm_data.edit_bones[get_mch_name("foot_roll_ball.L")]
    arm_data.edit_bones[get_mch_name("foot_roll_ankle.L")].use_connect = True
    
    for name in ["foot_roll_heel.L", "foot_roll_toe.L", "foot_roll_ball.L", "foot_roll_ankle.L"]:
        assign_to_collection(arm_data, get_mch_name(name), "Legs MCH")
        
    # 2. Mirror to right side
    for name in ["foot_roll_toe.L", "foot_roll_heel.L", "foot_roll_ball.L", "foot_roll_ankle.L"]:
        mch_left = get_mch_name(name)
        right_bone = mirror_bone(arm_data, mch_left)
        if right_bone:
            assign_to_collection(arm_data, right_bone.name, "Legs MCH")
