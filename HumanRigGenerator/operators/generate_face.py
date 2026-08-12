import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_deform_name, get_org_name
from ..utils.mirror import mirror_bone

def generate_face_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates facial bones in EDIT mode (Left and Right)."""
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.85
    
    # Read neck and head marker positions to anchor face bones
    p_neck = get_marker_pos("Mkr_neck", (0.0, -0.02, 1.62 * h_scale), marker_positions)
    p_head = get_marker_pos("Mkr_head", (0.0, -0.01, 1.88 * h_scale), marker_positions)
    
    # Calculate scale factor based on neck-to-head height
    head_h = p_head.z - p_neck.z
    if head_h <= 0.0:
        head_h = 0.26 * h_scale  # Fallback to standard head height
    scale = head_h / (0.26 * h_scale)
    
    # Resolve chin/jaw target chin marker location
    p_jaw_target = get_marker_pos("Mkr_jaw", mathutils.Vector((0.0, p_neck.y - 0.09 * scale, p_neck.z - 0.02 * scale)), marker_positions)
    
    # Resolve lip corner marker location first so upper and lower lip bones match it equally
    p_lip_corner = get_marker_pos("Mkr_lip.corner.L", mathutils.Vector((0.020 * scale, p_neck.y - 0.08 * scale, p_neck.z + 0.035 * scale)), marker_positions)
    
    # Distribute upper and lower lip bones half and half equally relative to the lip corner marker
    lip_offset_z = 0.015 * scale
    p_lip_up_center = mathutils.Vector((0.0, p_lip_corner.y, p_lip_corner.z + lip_offset_z))
    p_lip_low_center = mathutils.Vector((0.0, p_lip_corner.y, p_lip_corner.z - lip_offset_z))
    
    # 1. Central face bones (anchored to head and jaw, relative to p_neck)
    center_coords = {
        "face_root": ((0.0, p_neck.y - 0.05 * scale, p_neck.z + 0.12 * scale), (0.0, p_neck.y - 0.06 * scale, p_neck.z + 0.16 * scale), 0.0),
        "mouth_root": ((0.0, p_neck.y - 0.07 * scale, p_neck.z + 0.04 * scale), (0.0, p_neck.y - 0.08 * scale, p_neck.z + 0.08 * scale), 0.0),
        "jaw":   ((0.0, p_neck.y - 0.0 * scale, p_neck.z + 0.06 * scale), (0.0, p_neck.y - 0.07 * scale, p_neck.z + 0.02 * scale), 0.0),
        "chin":  ((0.0, p_neck.y - 0.07 * scale, p_neck.z + 0.02 * scale), p_jaw_target, 0.0),
        "nose":  ((0.0, p_neck.y - 0.07 * scale, p_neck.z + 0.14 * scale), (0.0, p_neck.y - 0.10 * scale, p_neck.z + 0.10 * scale), 0.0),
        "lip.upper": (p_lip_up_center, p_lip_up_center + mathutils.Vector((0.0, -0.015 * scale, 0.005 * scale)), 0.0),
        "lip.lower": (p_lip_low_center, p_lip_low_center + mathutils.Vector((0.0, -0.015 * scale, -0.005 * scale)), 0.0),
    }
    
    for name, (head, tail, roll) in center_coords.items():
        org_name = get_org_name(name)
        def_name = get_deform_name(name)
        
        parent_org = get_org_name("face_root")
        parent_def = get_deform_name("face_root")
        if name == "chin":
            parent_org = get_org_name("jaw")
            parent_def = get_deform_name("jaw")
        elif name == "jaw":
            parent_org = get_org_name("head")
            parent_def = get_deform_name("head")
        elif name == "face_root":
            parent_org = get_org_name("head")
            parent_def = get_deform_name("head")
        elif name == "mouth_root":
            parent_org = get_org_name("face_root")
            parent_def = get_deform_name("face_root")
        elif name == "lip.upper":
            parent_org = "CTRL-lip.upper"
            parent_def = get_deform_name("mouth_root")
        elif name == "lip.lower":
            parent_org = "CTRL-lip.lower"
            parent_def = get_deform_name("jaw")
            
        # Create ORG- bone
        create_bone(arm_data, org_name, mathutils.Vector(head), mathutils.Vector(tail), roll,
                    parent_name=parent_org, use_connect=False, is_deform=False)
        assign_to_collection(arm_data, org_name, "Face Org")
        
        # Create DEF- bone
        create_bone(arm_data, def_name, mathutils.Vector(head), mathutils.Vector(tail), roll,
                    parent_name=parent_def, use_connect=False, is_deform=True)
        assign_to_collection(arm_data, def_name, "Deform")
        
    # Resolve left marker coordinates with get_marker_pos
    p_eye = get_marker_pos("Mkr_eye.L", mathutils.Vector((0.035 * scale, p_neck.y - 0.06 * scale, p_neck.z + 0.14 * scale)), marker_positions)
    p_eyelid_up = get_marker_pos("Mkr_eyelid.upper.L", p_eye + mathutils.Vector((0.0, -0.03 * scale, 0.02 * scale)), marker_positions)
    p_eyelid_low = get_marker_pos("Mkr_eyelid.lower.L", p_eye + mathutils.Vector((0.0, -0.03 * scale, -0.02 * scale)), marker_positions)
    p_corner_inner = get_marker_pos("Mkr_eye_corner_inner.L", p_eye + mathutils.Vector((-0.02 * scale, -0.01 * scale, 0.0)), marker_positions)
    p_corner_outer = get_marker_pos("Mkr_eye_corner_outer.L", p_eye + mathutils.Vector((0.02 * scale, -0.01 * scale, 0.0)), marker_positions)
    p_brow1 = get_marker_pos("Mkr_eyebrow.01.L", mathutils.Vector((0.015 * scale, p_neck.y - 0.08 * scale, p_neck.z + 0.18 * scale)), marker_positions)
    p_brow2 = get_marker_pos("Mkr_eyebrow.02.L", mathutils.Vector((0.035 * scale, p_neck.y - 0.08 * scale, p_neck.z + 0.19 * scale)), marker_positions)
    p_brow3 = get_marker_pos("Mkr_eyebrow.03.L", mathutils.Vector((0.055 * scale, p_neck.y - 0.07 * scale, p_neck.z + 0.18 * scale)), marker_positions)
    p_cheek = get_marker_pos("Mkr_cheek.L", mathutils.Vector((0.050 * scale, p_neck.y - 0.05 * scale, p_neck.z + 0.08 * scale)), marker_positions)
    p_ear = mathutils.Vector((0.075 * scale, p_neck.y - 0.00 * scale, p_neck.z + 0.10 * scale))
    
    # 2. Create Eyebrow and Lip Viewport Control Bones first so detail bones can be parented to them
    # CTRL-eyebrow.L
    create_bone(arm_data, "CTRL-eyebrow.L", p_brow2, p_brow2 + mathutils.Vector((0.0, -0.02 * scale, 0.0)), 0.0,
                parent_name=get_org_name("face_root"), use_connect=False, is_deform=False)
    assign_to_collection(arm_data, "CTRL-eyebrow.L", "Face CTRL")
    
    # Mirror CTRL-eyebrow.L to CTRL-eyebrow.R
    right_brow = mirror_bone(arm_data, "CTRL-eyebrow.L")
    if right_brow:
        assign_to_collection(arm_data, right_brow.name, "Face CTRL")
        
    # CTRL-lip.upper
    create_bone(arm_data, "CTRL-lip.upper", p_lip_up_center, p_lip_up_center + mathutils.Vector((0.0, -0.02 * scale, 0.0)), 0.0,
                parent_name=get_org_name("mouth_root"), use_connect=False, is_deform=False)
    assign_to_collection(arm_data, "CTRL-lip.upper", "Face CTRL")
    
    # CTRL-lip.lower
    create_bone(arm_data, "CTRL-lip.lower", p_lip_low_center, p_lip_low_center + mathutils.Vector((0.0, -0.02 * scale, 0.0)), 0.0,
                parent_name=get_org_name("jaw"), use_connect=False, is_deform=False)
    assign_to_collection(arm_data, "CTRL-lip.lower", "Face CTRL")
    
    # Curved Eyelid Arc Support Points
    p_lid_up_01 = (p_corner_inner * 0.45 + p_eyelid_up * 0.55)
    p_lid_up_03 = (p_corner_outer * 0.45 + p_eyelid_up * 0.55)
    
    p_lid_low_01 = (p_corner_inner * 0.45 + p_eyelid_low * 0.55)
    p_lid_low_03 = (p_corner_outer * 0.45 + p_eyelid_low * 0.55)

    # Distribute upper and lower mid-lip support points half and half equally to the lip corner
    p_lip_up_mid = p_lip_up_center * 0.50 + p_lip_corner * 0.50
    p_lip_low_mid = p_lip_low_center * 0.50 + p_lip_corner * 0.50

    # 3. Left face bones
    left_coords = {
        "eye.L":             (p_eye, p_eye + mathutils.Vector((0.0, -0.05 * scale, 0.0)), 0.0),
        "eyelid.upper.01.L": (p_eye, p_lid_up_01, 0.0),
        "eyelid.upper.02.L": (p_eye, p_eyelid_up, 0.0),
        "eyelid.upper.03.L": (p_eye, p_lid_up_03, 0.0),
        "eyelid.upper.L":    (p_eye, p_eyelid_up, 0.0),
        "eyelid.lower.01.L": (p_eye, p_lid_low_01, 0.0),
        "eyelid.lower.02.L": (p_eye, p_eyelid_low, 0.0),
        "eyelid.lower.03.L": (p_eye, p_lid_low_03, 0.0),
        "eyelid.lower.L":    (p_eye, p_eyelid_low, 0.0),
        "eye_corner.inner.L":(p_eye, p_corner_inner, 0.0),
        "eye_corner.outer.L":(p_eye, p_corner_outer, 0.0),
        "eyebrow.01.L":      (p_brow1, p_brow1 + mathutils.Vector((0.0, -0.01 * scale, 0.01 * scale)), 0.0),
        "eyebrow.02.L":      (p_brow2, p_brow2 + mathutils.Vector((0.0, -0.01 * scale, 0.01 * scale)), 0.0),
        "eyebrow.03.L":      (p_brow3, p_brow3 + mathutils.Vector((0.0, -0.01 * scale, 0.00 * scale)), 0.0),
        "cheek.L":           (p_cheek, p_cheek + mathutils.Vector((0.010 * scale, -0.03 * scale, 0.0)), 0.0),
        "lip.corner.L":      (p_lip_corner, p_lip_corner + mathutils.Vector((0.005 * scale, -0.01 * scale, 0.0)), 0.0),
        "lip.upper.01.L":    (p_lip_up_mid, p_lip_up_mid + mathutils.Vector((0.0, -0.015 * scale, 0.005 * scale)), 0.0),
        "lip.lower.01.L":    (p_lip_low_mid, p_lip_low_mid + mathutils.Vector((0.0, -0.015 * scale, -0.005 * scale)), 0.0),
        "ear.L":             (p_ear, p_ear + mathutils.Vector((0.015 * scale, 0.0, 0.02 * scale)), 0.0)
    }
    
    left_org_names = []
    for name, (head, tail, roll) in left_coords.items():
        org_name = get_org_name(name)
        
        # Parent detail bones to CTRL bones to inherit translations, else to face_root
        parent_org = get_org_name("face_root")
        if "eyebrow" in name:
            parent_org = "CTRL-eyebrow.L"
        elif "lip" in name:
            if "corner" in name:
                parent_org = get_org_name("mouth_root")
            elif "upper" in name:
                parent_org = "CTRL-lip.upper"
            else:
                parent_org = "CTRL-lip.lower"
            
        bone = create_bone(arm_data, org_name, mathutils.Vector(head), mathutils.Vector(tail), roll,
                    parent_name=parent_org, use_connect=False, is_deform=False)
        if "eyelid" in name or "eye_corner" in name:
            bone.align_roll(mathutils.Vector((0, 0, 1)))
        assign_to_collection(arm_data, org_name, "Face Org")
        left_org_names.append(org_name)
        
    # Parent right ORG bones properly when mirroring (handled by mirror_bone using opposite side names)
    right_org_names = []
    for left_org in left_org_names:
        right_bone = mirror_bone(arm_data, left_org)
        if right_bone:
            right_org_names.append(right_bone.name)
            assign_to_collection(arm_data, right_bone.name, "Face Org")
            if "eyelid" in right_bone.name or "eye_corner" in right_bone.name:
                right_bone.align_roll(mathutils.Vector((0, 0, 1)))
            
    # Generate DEF- bones for both sides parented to deform anchors (face_root/mouth_root/jaw)
    for side in [".L", ".R"]:
        for name in left_coords.keys():
            core_name = name[:-2] # e.g. "eye"
            
            def_name = get_deform_name(f"{core_name}{side}")
            org_name = get_org_name(f"{core_name}{side}")
            
            org_bone = arm_data.edit_bones.get(org_name)
            if not org_bone:
                continue
                
            parent_def = get_deform_name("face_root")
            if "lip.lower" in name:
                parent_def = get_deform_name("jaw")
            elif "lip" in name:
                parent_def = get_deform_name("mouth_root")
                
            def_bone = create_bone(arm_data, def_name, org_bone.head.copy(), org_bone.tail.copy(), org_bone.roll,
                        parent_name=parent_def, use_connect=False, is_deform=True)
            if "eyelid" in name or "eye_corner" in name:
                def_bone.align_roll(mathutils.Vector((0, 0, 1)))
            assign_to_collection(arm_data, def_name, "Deform")
