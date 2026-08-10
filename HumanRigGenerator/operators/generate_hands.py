# operators/generate_hands.py
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_deform_name, get_org_name
from ..utils.mirror import mirror_bone

def generate_hand_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates finger bones in EDIT mode (Left and Right)."""
    # Interpolate intermediate thumb markers if base and tip exist in marker_positions
    if marker_positions:
        for side in [".L", ".R"]:
            mkr_base = f"Mkr_thumb.01{side}"
            mkr_tip = f"Mkr_thumb_tip{side}"
            if mkr_base in marker_positions and mkr_tip in marker_positions:
                p_base = marker_positions[mkr_base]
                p_tip = marker_positions[mkr_tip]
                marker_positions[f"Mkr_thumb.02{side}"] = p_base + (p_tip - p_base) * 0.33
                marker_positions[f"Mkr_thumb.03{side}"] = p_base + (p_tip - p_base) * 0.66
                
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.85
    
    # Read markers for scale and rotation reference
    default_shoulder = mathutils.Vector((0.16 * w_scale, -0.03 * w_scale, 1.43 * h_scale))
    p_shoulder = get_marker_pos("Mkr_shoulder.L", default_shoulder, marker_positions)
    
    default_elbow = mathutils.Vector((0.42 * w_scale, -0.06 * w_scale, 1.42 * h_scale))
    p_elbow = get_marker_pos("Mkr_elbow.L", default_elbow, marker_positions)
    
    default_wrist = mathutils.Vector((0.68 * w_scale, -0.05 * w_scale, 1.42 * h_scale))
    current_wrist = get_marker_pos("Mkr_wrist.L", default_wrist, marker_positions)
    
    # Calculate scale factor
    default_len = (default_wrist - default_shoulder).length
    actual_len = (current_wrist - p_shoulder).length
    hand_scale = actual_len / default_len if default_len > 0 else 1.0
    
    # Calculate rotation from default hand direction (+X) to actual hand direction
    default_dir = mathutils.Vector((1.0, 0.0, 0.0))
    actual_dir = (current_wrist - p_elbow).normalized()
    if actual_dir.length_squared == 0:
        actual_dir = default_dir.copy()
    rot_q = default_dir.rotation_difference(actual_dir)
    
    # Left side baseline finger bone coordinates (Marker Head, Marker Tail, Default Head, Default Tail, Roll)
    baseline_coords = {
        # Thumb
        "thumb.01.L": ("Mkr_thumb.01.L", "Mkr_thumb.02.L", (0.70 * w_scale, -0.08 * w_scale, 1.42 * h_scale), (0.74 * w_scale, -0.10 * w_scale, 1.41 * h_scale), 0.0),
        "thumb.02.L": ("Mkr_thumb.02.L", "Mkr_thumb.03.L", (0.74 * w_scale, -0.10 * w_scale, 1.41 * h_scale), (0.78 * w_scale, -0.11 * w_scale, 1.405 * h_scale), 0.0),
        "thumb.03.L": ("Mkr_thumb.03.L", "Mkr_thumb_tip.L", (0.78 * w_scale, -0.11 * w_scale, 1.405 * h_scale), (0.81 * w_scale, -0.115 * w_scale, 1.40 * h_scale), 0.0),
        
        # Index
        "index.01.L": ("Mkr_index.01.L", "Mkr_index.02.L", (0.76 * w_scale, -0.07 * w_scale, 1.425 * h_scale), (0.80 * w_scale, -0.07 * w_scale, 1.425 * h_scale), 0.0),
        "index.02.L": ("Mkr_index.02.L", "Mkr_index.03.L", (0.80 * w_scale, -0.07 * w_scale, 1.425 * h_scale), (0.83 * w_scale, -0.07 * w_scale, 1.425 * h_scale), 0.0),
        "index.03.L": ("Mkr_index.03.L", "Mkr_index_tip.L", (0.83 * w_scale, -0.07 * w_scale, 1.425 * h_scale), (0.85 * w_scale, -0.07 * w_scale, 1.425 * h_scale), 0.0),
        
        # Middle
        "middle.01.L": ("Mkr_middle.01.L", "Mkr_middle.02.L", (0.76 * w_scale, -0.05 * w_scale, 1.42 * h_scale), (0.81 * w_scale, -0.05 * w_scale, 1.42 * h_scale), 0.0),
        "middle.02.L": ("Mkr_middle.02.L", "Mkr_middle.03.L", (0.81 * w_scale, -0.05 * w_scale, 1.42 * h_scale), (0.85 * w_scale, -0.05 * w_scale, 1.42 * h_scale), 0.0),
        "middle.03.L": ("Mkr_middle.03.L", "Mkr_middle_tip.L", (0.85 * w_scale, -0.05 * w_scale, 1.42 * h_scale), (0.87 * w_scale, -0.05 * w_scale, 1.42 * h_scale), 0.0),
        
        # Ring
        "ring.01.L": ("Mkr_ring.01.L", "Mkr_ring.02.L", (0.76 * w_scale, -0.03 * w_scale, 1.415 * h_scale), (0.80 * w_scale, -0.03 * w_scale, 1.415 * h_scale), 0.0),
        "ring.02.L": ("Mkr_ring.02.L", "Mkr_ring.03.L", (0.80 * w_scale, -0.03 * w_scale, 1.415 * h_scale), (0.83 * w_scale, -0.03 * w_scale, 1.415 * h_scale), 0.0),
        "ring.03.L": ("Mkr_ring.03.L", "Mkr_ring_tip.L", (0.83 * w_scale, -0.03 * w_scale, 1.415 * h_scale), (0.85 * w_scale, -0.03 * w_scale, 1.415 * h_scale), 0.0),
        
        # Pinky
        "pinky.01.L": ("Mkr_pinky.01.L", "Mkr_pinky.02.L", (0.75 * w_scale, -0.01 * w_scale, 1.41 * h_scale), (0.79 * w_scale, -0.01 * w_scale, 1.41 * h_scale), 0.0),
        "pinky.02.L": ("Mkr_pinky.02.L", "Mkr_pinky.03.L", (0.79 * w_scale, -0.01 * w_scale, 1.41 * h_scale), (0.82 * w_scale, -0.01 * w_scale, 1.41 * h_scale), 0.0),
        "pinky.03.L": ("Mkr_pinky.03.L", "Mkr_pinky_tip.L", (0.82 * w_scale, -0.01 * w_scale, 1.41 * h_scale), (0.84 * w_scale, -0.01 * w_scale, 1.41 * h_scale), 0.0),
    }
    
    # Calculate hand normal for left side roll alignment
    p_index_base = get_marker_pos("Mkr_index.01.L", current_wrist + rot_q @ (mathutils.Vector((0.08 * w_scale, -0.02 * w_scale, 0.005 * h_scale)) * hand_scale), marker_positions)
    p_pinky_base = get_marker_pos("Mkr_pinky.01.L", current_wrist + rot_q @ (mathutils.Vector((0.07 * w_scale, 0.04 * w_scale, -0.01 * h_scale)) * hand_scale), marker_positions)
    p_middle_base = get_marker_pos("Mkr_middle.01.L", current_wrist + rot_q @ (mathutils.Vector((0.08 * w_scale, 0.0 * w_scale, 0.0 * h_scale)) * hand_scale), marker_positions)
    
    dir_y = (p_middle_base - current_wrist).normalized()
    dir_x = (p_index_base - p_pinky_base).normalized()
    hand_normal = dir_y.cross(dir_x).normalized()

    # Scale and rotate relative coordinates based on wrist placement and arm direction
    finger_coords = {}
    for bone_name, (mkr_head, mkr_tail, head, tail, roll) in baseline_coords.items():
        if marker_positions and mkr_head in marker_positions and mkr_tail in marker_positions:
            scaled_head = marker_positions[mkr_head].copy()
            scaled_tail = marker_positions[mkr_tail].copy()
        else:
            rel_head = mathutils.Vector(head) - default_wrist
            rel_tail = mathutils.Vector(tail) - default_wrist
            scaled_head = current_wrist + rot_q @ (rel_head * hand_scale)
            scaled_tail = current_wrist + rot_q @ (rel_tail * hand_scale)
        
        finger_coords[bone_name] = (
            scaled_head,
            scaled_tail,
            roll
        )
    
    # Bone parenting mapping
    parent_map = {
        "thumb.01.L": "hand.L",
        "thumb.02.L": "thumb.01.L",
        "thumb.03.L": "thumb.02.L",
        
        "index.01.L": "hand.L",
        "index.02.L": "index.01.L",
        "index.03.L": "index.02.L",
        
        "middle.01.L": "hand.L",
        "middle.02.L": "middle.01.L",
        "middle.03.L": "middle.02.L",
        
        "ring.01.L": "hand.L",
        "ring.02.L": "ring.01.L",
        "ring.03.L": "ring.02.L",
        
        "pinky.01.L": "hand.L",
        "pinky.02.L": "pinky.01.L",
        "pinky.03.L": "pinky.02.L",
    }
    
    # 1. Generate ORG- left bones
    left_org_names = []
    for base_name, (head, tail, roll) in finger_coords.items():
        org_name = get_org_name(base_name)
        
        parent_base = parent_map.get(base_name)
        parent_org = get_org_name(parent_base) if parent_base else None
        
        # Connect if it is NOT the first segment
        use_connect = False
        if parent_base and ".01." not in base_name and "thumb.01." not in base_name:
            use_connect = True
            
        bone = create_bone(
            arm_data,
            org_name,
            mathutils.Vector(head),
            mathutils.Vector(tail),
            roll,
            parent_name=parent_org,
            use_connect=use_connect,
            is_deform=False
        )
        if hand_normal.length_squared > 0:
            bone.align_roll(hand_normal)
            
        assign_to_collection(arm_data, org_name, "Fingers Org")
        left_org_names.append(org_name)
        
    # 2. Mirror ORG- bones to right side
    right_org_names = []
    for left_org in left_org_names:
        right_bone = mirror_bone(arm_data, left_org)
        if right_bone:
            right_org_names.append(right_bone.name)
            assign_to_collection(arm_data, right_bone.name, "Fingers Org")
            
    # 3. Generate DEF- bones for both sides
    for side in [".L", ".R"]:
        for base_name in finger_coords.keys():
            # Get base name without the side suffix
            core_name = base_name[:-2] # e.g. "index.01"
            
            def_name = get_deform_name(f"{core_name}{side}")
            org_name = get_org_name(f"{core_name}{side}")
            
            org_bone = arm_data.edit_bones.get(org_name)
            if not org_bone:
                continue
                
            parent_base = parent_map.get(base_name)
            # Remove .L and add current side suffix
            parent_side_name = f"{parent_base[:-2]}{side}" if parent_base else None
            parent_def = get_deform_name(parent_side_name) if parent_side_name else None
            
            use_connect = False
            if parent_base and ".01." not in base_name and "thumb.01." not in base_name:
                use_connect = True
                
            create_bone(
                arm_data,
                def_name,
                org_bone.head.copy(),
                org_bone.tail.copy(),
                org_bone.roll,
                parent_name=parent_def,
                use_connect=use_connect,
                is_deform=True
            )
            assign_to_collection(arm_data, def_name, "Deform")
