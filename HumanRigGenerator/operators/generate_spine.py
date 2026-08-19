# operators/generate_spine.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, get_marker_pos
from ..utils.naming import get_deform_name, get_org_name

def generate_spine_bones(arm_data, gender="MALE", marker_positions=None):
    """Generates the spine bone structure in EDIT mode."""
    # Define proportions base factors
    h_scale = 1.0 if gender == "MALE" else 0.9
    
    # Read marker positions (or use baseline defaults)
    p_pelvis = get_marker_pos("Mkr_pelvis", (0.0, 0.0, 0.95 * h_scale), marker_positions)
    p_spine = get_marker_pos("Mkr_spine", (0.0, 0.0, 1.05 * h_scale), marker_positions)
    p_spine_003 = get_marker_pos("Mkr_spine_003", (0.0, 0.0, 1.48 * h_scale), marker_positions)
    p_neck = get_marker_pos("Mkr_neck", (0.0, -0.02, 1.62 * h_scale), marker_positions)
    p_head = get_marker_pos("Mkr_head", (0.0, -0.01, 1.88 * h_scale), marker_positions)
    
    # Calculate subdivisions for spine segments
    diff = p_spine_003 - p_spine
    p_s1 = p_spine + diff * (1.0 / 3.0)
    p_s2 = p_spine + diff * (2.0 / 3.0)
    
    # Bone coordinates (Head, Tail, Roll)
    coords = {
        "pelvis":     (p_pelvis, p_pelvis + mathutils.Vector((0.0, -0.05, -0.1 * h_scale)), 0.0),
        "spine":      (p_pelvis, p_spine, 0.0),
        "spine.001":  (p_spine, p_s1, 0.0),
        "spine.002":  (p_s1, p_s2, 0.0),
        "spine.003":  (p_s2, p_spine_003, 0.0),
        "neck":       (p_spine_003, p_neck, 0.0),
        "head":       (p_neck, p_head, 0.0)
    }
    
    # We will generate original ORG- bones and deformation DEF- bones
    # The ORG- bones form the core framework of the spine.
    # The DEF- bones mirror them and do the skin binding.
    
    # 1. ORG- bones
    org_bones = {}
    for name, (head, tail, roll) in coords.items():
        org_name = get_org_name(name)
        
        # Parenting relationship mapping
        parent = None
        if name == "spine":
            parent = None
        elif name == "pelvis":
            parent = get_org_name("spine")
        elif name == "spine.001":
            parent = get_org_name("spine")
        elif name == "spine.002":
            parent = get_org_name("spine.001")
        elif name == "spine.003":
            parent = get_org_name("spine.002")
        elif name == "neck":
            parent = get_org_name("spine.003")
        elif name == "head":
            parent = get_org_name("neck")
            
        bone = create_bone(
            arm_data, 
            org_name, 
            mathutils.Vector(head), 
            mathutils.Vector(tail), 
            roll, 
            parent_name=parent, 
            use_connect=(parent is not None and name != "pelvis" and name != "spine.001"),
            is_deform=False
        )
        org_bones[name] = org_name
        assign_to_collection(arm_data, org_name, "Spine Org")
        
    # 2. DEF- bones
    for name, (head, tail, roll) in coords.items():
        def_name = get_deform_name(name)
        # Parent matches ORG parenting but using DEF names
        parent = None
        if name == "spine":
            parent = None
        elif name == "pelvis":
            parent = get_deform_name("spine")
        elif name == "spine.001":
            parent = get_deform_name("spine")
        elif name == "spine.002":
            parent = get_deform_name("spine.001")
        elif name == "spine.003":
            parent = get_deform_name("spine.002")
        elif name == "neck":
            parent = get_deform_name("spine.003")
        elif name == "head":
            parent = get_deform_name("neck")
            
        spine_segments = 1
        if bpy.context.scene.hrg_use_bbone_spine and name in ["spine", "spine.001", "spine.002", "spine.003", "neck"]:
            spine_segments = bpy.context.scene.hrg_bbone_segments_spine
            
        bone = create_bone(
            arm_data,
            def_name,
            mathutils.Vector(head),
            mathutils.Vector(tail),
            roll,
            parent_name=parent,
            use_connect=(parent is not None and name != "pelvis" and name != "spine.001"),
            is_deform=True,
            bbone_segments=spine_segments
        )
        assign_to_collection(arm_data, def_name, "Deform")
        
    return org_bones
