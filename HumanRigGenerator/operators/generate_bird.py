# operators/generate_bird.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_org_name, get_mch_name, get_control_name, get_deform_name
from ..utils.mirror import mirror_bone

def generate_bird_bones(arm_data, marker_positions=None):
    """Generates the bird (avian) core skeleton (ORG and DEF) bones in Edit Mode."""
    # 1. Gather Marker coordinates
    pelvis_pos = get_marker_pos("Mkr_pelvis", (0.0, -0.15, 0.50), marker_positions)
    spine_pos = get_marker_pos("Mkr_spine", (0.0, 0.00, 0.55), marker_positions)
    chest_pos = get_marker_pos("Mkr_spine_003", (0.0, 0.15, 0.60), marker_positions)
    neck_pos = get_marker_pos("Mkr_neck", (0.0, 0.25, 0.75), marker_positions)
    head_pos = get_marker_pos("Mkr_head", (0.0, 0.32, 0.90), marker_positions)
    head_end = head_pos + mathutils.Vector((0.0, 0.08, 0.05))
    
    tail_base = get_marker_pos("Mkr_tail_base", (0.0, -0.22, 0.52), marker_positions)
    tail_tip = get_marker_pos("Mkr_tail_tip", (0.0, -0.40, 0.45), marker_positions)
    
    shoulder_pos = get_marker_pos("Mkr_shoulder.L", (0.08, 0.10, 0.60), marker_positions)
    elbow_pos = get_marker_pos("Mkr_elbow.L", (0.35, -0.05, 0.65), marker_positions)
    wrist_pos = get_marker_pos("Mkr_wrist.L", (0.70, -0.25, 0.55), marker_positions)
    wing_end = wrist_pos + mathutils.Vector((0.08, -0.08, -0.05))
    
    thigh_pos = get_marker_pos("Mkr_thigh.L", (0.08, -0.10, 0.45), marker_positions)
    knee_pos = get_marker_pos("Mkr_knee.L", (0.09, -0.15, 0.25), marker_positions)
    ankle_pos = get_marker_pos("Mkr_ankle.L", (0.09, -0.08, 0.08), marker_positions)
    toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.09, 0.08, 0.02), marker_positions)
    
    # 2. Define coordinates dictionary for all bones
    coords = {
        # Central bones
        "pelvis":     (pelvis_pos, spine_pos, 0.0, None),
        "spine":      (spine_pos, chest_pos, 0.0, "pelvis"),
        "spine.003":  (chest_pos, neck_pos, 0.0, "spine"),
        "neck":       (neck_pos, head_pos, 0.0, "spine.003"),
        "head":       (head_pos, head_end, 0.0, "neck"),
        
        "tail.001":   (pelvis_pos, tail_base, 0.0, "pelvis"),
        "tail.002":   (tail_base, tail_tip, 0.0, "tail.001"),
        
        # Left side wings
        "clavicle.L":  (chest_pos, shoulder_pos, 0.0, "spine.003"),
        "upper_arm.L": (shoulder_pos, elbow_pos, 0.0, "clavicle.L"),
        "forearm.L":   (elbow_pos, wrist_pos, 0.0, "upper_arm.L"),
        "hand.L":      (wrist_pos, wing_end, 0.0, "forearm.L"),
        
        # Left side legs
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
        if name in ["pelvis", "spine", "spine.003", "neck", "head", "tail.001", "tail.002"]:
            col_type = "Torso ORG"
        assign_to_collection(arm_data, org_name, col_type)
        
    # 4. Create DEF- bones
    for name, (head, tail, roll, parent) in coords.items():
        def_name = get_deform_name(name)
        parent_def = get_deform_name(parent) if parent else None
        
        # Check B-Bone segments based on bone type
        bb_segments = 1
        bb_easein = 0.0
        bb_easeout = 0.0
        scene = bpy.context.scene
        if "thigh" in name or "shin" in name or "foot" in name:
            if scene.hrg_use_bbone_legs:
                bb_segments = scene.hrg_bbone_segments_legs
                if "thigh" in name:
                    bb_easein = 1.0
                else: # shin or foot
                    bb_easeout = 1.0
        elif "upper_arm" in name or "forearm" in name or "hand" in name:
            if scene.hrg_use_bbone_arms:
                bb_segments = scene.hrg_bbone_segments_arms
                if "upper_arm" in name:
                    bb_easein = 1.0
                else: # forearm or hand
                    bb_easeout = 1.0
        elif "spine" in name or "neck" in name or "tail" in name:
            if scene.hrg_use_bbone_spine:
                bb_segments = scene.hrg_bbone_segments_spine
                
        create_bone(
            arm_data, 
            def_name, 
            head, 
            tail, 
            roll, 
            parent_name=parent_def, 
            use_connect=(parent_def is not None and "pelvis" not in name and "clavicle" not in name and "thigh" not in name), 
            is_deform=True,
            bbone_segments=bb_segments,
            bbone_easein=bb_easein,
            bbone_easeout=bb_easeout
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
