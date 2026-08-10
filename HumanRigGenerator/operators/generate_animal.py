# operators/generate_animal.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_org_name, get_mch_name, get_control_name, get_deform_name
from ..utils.mirror import mirror_bone

def generate_animal_bones(arm_data, marker_positions=None):
    """Generates the animal (quadruped) core skeleton (ORG and DEF) bones in Edit Mode."""
    # 1. Gather Marker coordinates
    pelvis_pos = get_marker_pos("Mkr_pelvis", (0.0, -0.60, 0.70), marker_positions)
    spine_pos = get_marker_pos("Mkr_spine", (0.0, -0.30, 0.75), marker_positions)
    chest_pos = get_marker_pos("Mkr_spine_003", (0.0, 0.00, 0.75), marker_positions)
    neck_pos = get_marker_pos("Mkr_neck", (0.0, 0.35, 0.82), marker_positions)
    head_pos = get_marker_pos("Mkr_head", (0.0, 0.50, 0.95), marker_positions)
    head_end = head_pos + mathutils.Vector((0.0, 0.15, 0.0))
    
    tail_base = get_marker_pos("Mkr_tail_base", (0.0, -0.65, 0.75), marker_positions)
    tail_mid = get_marker_pos("Mkr_tail_mid", (0.0, -0.90, 0.65), marker_positions)
    tail_tip = get_marker_pos("Mkr_tail_tip", (0.0, -1.15, 0.50), marker_positions)
    
    shoulder_pos = get_marker_pos("Mkr_shoulder.L", (0.18, 0.20, 0.70), marker_positions)
    elbow_pos = get_marker_pos("Mkr_elbow.L", (0.18, 0.18, 0.38), marker_positions)
    wrist_pos = get_marker_pos("Mkr_wrist.L", (0.18, 0.18, 0.12), marker_positions)
    finger_tip = get_marker_pos("Mkr_finger_tip.L", (0.18, 0.28, 0.02), marker_positions)
    
    thigh_pos = get_marker_pos("Mkr_thigh.L", (0.18, -0.55, 0.70), marker_positions)
    knee_pos = get_marker_pos("Mkr_knee.L", (0.18, -0.62, 0.42), marker_positions)
    ankle_pos = get_marker_pos("Mkr_ankle.L", (0.18, -0.52, 0.15), marker_positions)
    toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.18, -0.42, 0.02), marker_positions)
    
    # 2. Define coordinates dictionary for all bones
    coords = {
        # Central bones
        "pelvis":     (pelvis_pos, spine_pos, 0.0, None),
        "spine":      (spine_pos, chest_pos, 0.0, "pelvis"),
        "spine.003":  (chest_pos, neck_pos, 0.0, "spine"),
        "neck":       (neck_pos, head_pos, 0.0, "spine.003"),
        "head":       (head_pos, head_end, 0.0, "neck"),
        
        "tail.001":   (pelvis_pos, tail_base, 0.0, "pelvis"),
        "tail.002":   (tail_base, tail_mid, 0.0, "tail.001"),
        "tail.003":   (tail_mid, tail_tip, 0.0, "tail.002"),
        
        # Left side forelegs
        "clavicle.L":  (chest_pos, shoulder_pos, 0.0, "spine.003"),
        "upper_arm.L": (shoulder_pos, elbow_pos, 0.0, "clavicle.L"),
        "forearm.L":   (elbow_pos, wrist_pos, 0.0, "upper_arm.L"),
        "hand.L":      (wrist_pos, finger_tip, 0.0, "forearm.L"),
        
        # Left side rearlegs
        "thigh.L":     (pelvis_pos, thigh_pos, 0.0, "pelvis"),
        "shin.L":      (thigh_pos, knee_pos, 0.0, "thigh.L"),
        "foot.L":      (knee_pos, ankle_pos, 0.0, "shin.L"),
        "toe.L":       (ankle_pos, toe_pos, 0.0, "foot.L")
    }
    
    # 3. Create ORG- bones
    for name, (head, tail, roll, parent) in coords.items():
        org_name = get_org_name(name)
        parent_org = get_org_name(parent) if parent else None
        
        create_bone(
            arm_data, 
            org_name, 
            head, 
            tail, 
            roll, 
            parent_name=parent_org, 
            use_connect=(parent_org is not None and "pelvis" not in name and "clavicle" not in name and "thigh" not in name), 
            is_deform=False
        )
        
        # Collections organization
        col_type = "Arms ORG" if "arm" in name or "hand" in name or "clavicle" in name else "Legs ORG"
        if name in ["pelvis", "spine", "spine.003", "neck", "head", "tail.001", "tail.002", "tail.003"]:
            col_type = "Torso ORG"
        assign_to_collection(arm_data, org_name, col_type)
        
    # 4. Create DEF- bones
    for name, (head, tail, roll, parent) in coords.items():
        def_name = get_deform_name(name)
        parent_def = get_deform_name(parent) if parent else None
        
        create_bone(
            arm_data, 
            def_name, 
            head, 
            tail, 
            roll, 
            parent_name=parent_def, 
            use_connect=(parent_def is not None and "pelvis" not in name and "clavicle" not in name and "thigh" not in name), 
            is_deform=True
        )
        assign_to_collection(arm_data, def_name, "Deform")
        
    # 5. Mirror Left Limbs to Right (both ORG and DEF)
    limbs_to_mirror = [
        "clavicle.L", "upper_arm.L", "forearm.L", "hand.L",
        "thigh.L", "shin.L", "foot.L", "toe.L"
    ]
    
    for name in limbs_to_mirror:
        # Mirror ORG-
        org_name = get_org_name(name)
        right_org = mirror_bone(arm_data, org_name)
        if right_org:
            col_type = "Arms ORG" if "arm" in right_org.name or "hand" in right_org.name or "clavicle" in right_org.name else "Legs ORG"
            assign_to_collection(arm_data, right_org.name, col_type)
            
        # Mirror DEF-
        def_name = get_deform_name(name)
        right_def = mirror_bone(arm_data, def_name)
        if right_def:
            assign_to_collection(arm_data, right_def.name, "Deform")
