# utils/bones.py
import bpy
import mathutils

def get_edit_bone(arm_data, name):
    """Retrieves an edit bone from the armature data. Armature must be in EDIT mode."""
    return arm_data.edit_bones.get(name)

def get_pose_bone(obj, name):
    """Retrieves a pose bone from the armature object. Object must be in POSE mode."""
    return obj.pose.bones.get(name)

def create_bone(arm_data, name, head, tail, roll=0.0, parent_name=None, use_connect=False, is_deform=True, bbone_segments=1, bbone_easein=0.0, bbone_easeout=0.0):
    """Creates a new edit bone in the armature. Armature must be in EDIT mode."""
    # If bone already exists, return it
    bone = arm_data.edit_bones.get(name)
    if bone is None:
        bone = arm_data.edit_bones.new(name)
        
    bone.head = head
    bone.tail = tail
    bone.roll = roll
    bone.use_deform = is_deform
    
    if parent_name:
        parent_bone = arm_data.edit_bones.get(parent_name)
        if parent_bone:
            bone.parent = parent_bone
            bone.use_connect = use_connect
            
    if bbone_segments > 1:
        bone.bbone_segments = bbone_segments
        bone.bbone_easein = bbone_easein
        bone.bbone_easeout = bbone_easeout
            
    return bone

def set_parent(arm_data, bone_name, parent_name, use_connect=False):
    """Sets parent of a bone. Armature must be in EDIT mode."""
    bone = arm_data.edit_bones.get(bone_name)
    parent_bone = arm_data.edit_bones.get(parent_name)
    if bone and parent_bone:
        bone.parent = parent_bone
        bone.use_connect = use_connect

_pending_collection_assignments = []

def assign_to_collection(arm_data, bone_name, collection_name):
    """Queues or assigns a bone to a bone collection. Works in EDIT or POSE mode."""
    # In Edit Mode, arm_data.bones is unpopulated. Queue the assignment to apply once in Pose Mode.
    if arm_data.is_editmode or bpy.context.mode == 'EDIT_ARMATURE':
        _pending_collection_assignments.append((arm_data.name, bone_name, collection_name))
    else:
        bone = arm_data.bones.get(bone_name)
        if bone:
            coll = arm_data.collections.get(collection_name)
            if not coll:
                coll = arm_data.collections.new(collection_name)
            coll.assign(bone)

def apply_queued_collections(arm_data):
    """Applies all queued bone collection assignments once out of Edit Mode."""
    global _pending_collection_assignments
    remaining = []
    for arm_name, bone_name, coll_name in _pending_collection_assignments:
        if arm_name == arm_data.name:
            bone = arm_data.bones.get(bone_name)
            if bone:
                coll = arm_data.collections.get(coll_name)
                if not coll:
                    coll = arm_data.collections.new(coll_name)
                coll.assign(bone)
        else:
            remaining.append((arm_name, bone_name, coll_name))
    _pending_collection_assignments = remaining

def add_constraint(pose_bone, constraint_type, name, target_obj, target_bone=None, **properties):
    """Adds a constraint to a pose bone. Object must be in POSE mode."""
    constraint = pose_bone.constraints.get(name)
    if not constraint:
        constraint = pose_bone.constraints.new(type=constraint_type)
        constraint.name = name
        
    constraint.target = target_obj
    if target_bone and hasattr(constraint, 'subtarget'):
        constraint.subtarget = target_bone
        
    for prop, val in properties.items():
        setattr(constraint, prop, val)
        
    return constraint

HUMAN_MARKERS = {
    "Mkr_pelvis":    (0.0, 0.0, 0.95),
    "Mkr_spine":     (0.0, 0.0, 1.05),
    "Mkr_spine_003": (0.0, 0.0, 1.48),
    "Mkr_neck":      (0.0, -0.02, 1.62),
    "Mkr_head":      (0.0, -0.01, 1.88),
    "Mkr_shoulder.L":  (0.16, -0.03, 1.43),
    "Mkr_elbow.L":     (0.42, -0.06, 1.42),
    "Mkr_wrist.L":     (0.68, -0.05, 1.42),
    "Mkr_thigh.L":     (0.12, -0.02, 0.86),
    "Mkr_knee.L":      (0.13, 0.03, 0.48),
    "Mkr_ankle.L":     (0.13, -0.05, 0.09),
    "Mkr_foot_toe.L":  (0.13, 0.16, 0.02),
    
    # Thumb
    "Mkr_thumb.01.L": (0.70, -0.08, 1.42),
    "Mkr_thumb_tip.L": (0.81, -0.115, 1.40),
    
    # Index
    "Mkr_index.01.L": (0.76, -0.07, 1.425),
    "Mkr_index.02.L": (0.80, -0.07, 1.425),
    "Mkr_index.03.L": (0.83, -0.07, 1.425),
    "Mkr_index_tip.L": (0.85, -0.07, 1.425),
    
    # Middle
    "Mkr_middle.01.L": (0.76, -0.05, 1.42),
    "Mkr_middle.02.L": (0.81, -0.05, 1.42),
    "Mkr_middle.03.L": (0.85, -0.05, 1.42),
    "Mkr_middle_tip.L": (0.87, -0.05, 1.42),
    
    # Ring
    "Mkr_ring.01.L": (0.76, -0.03, 1.415),
    "Mkr_ring.02.L": (0.80, -0.03, 1.415),
    "Mkr_ring.03.L": (0.83, -0.03, 1.415),
    "Mkr_ring_tip.L": (0.85, -0.03, 1.415),
    
    # Pinky
    "Mkr_pinky.01.L": (0.75, -0.01, 1.41),
    "Mkr_pinky.02.L": (0.79, -0.01, 1.41),
    "Mkr_pinky.03.L": (0.82, -0.01, 1.41),
    "Mkr_pinky_tip.L": (0.84, -0.01, 1.41)
}

ANIMAL_MARKERS = {
    "Mkr_pelvis":    (0.0, -0.60, 0.70),
    "Mkr_spine":     (0.0, -0.30, 0.75),
    "Mkr_spine_003": (0.0, 0.00, 0.75),
    "Mkr_neck":      (0.0, 0.35, 0.82),
    "Mkr_head":      (0.0, 0.50, 0.95),
    "Mkr_tail_base": (0.0, -0.65, 0.75),
    "Mkr_tail_mid":  (0.0, -0.90, 0.65),
    "Mkr_tail_tip":  (0.0, -1.15, 0.50),
    "Mkr_shoulder.L":  (0.18, 0.20, 0.70),
    "Mkr_elbow.L":     (0.18, 0.18, 0.38),
    "Mkr_wrist.L":     (0.18, 0.18, 0.12),
    "Mkr_finger_tip.L": (0.18, 0.28, 0.02),
    "Mkr_thigh.L":     (0.18, -0.55, 0.70),
    "Mkr_knee.L":      (0.18, -0.62, 0.42),
    "Mkr_ankle.L":     (0.18, -0.52, 0.15),
    "Mkr_foot_toe.L":  (0.18, -0.42, 0.02)
}

BIRD_MARKERS = {
    "Mkr_pelvis":      (0.0, -0.15, 0.50),
    "Mkr_spine":       (0.0, 0.00, 0.55),
    "Mkr_spine_003":   (0.0, 0.15, 0.60),
    "Mkr_neck":        (0.0, 0.25, 0.75),
    "Mkr_head":        (0.0, 0.32, 0.90),
    "Mkr_tail_base":   (0.0, -0.22, 0.52),
    "Mkr_tail_tip":    (0.0, -0.40, 0.45),
    "Mkr_shoulder.L":  (0.08, 0.10, 0.60),
    "Mkr_elbow.L":     (0.35, -0.05, 0.65),
    "Mkr_wrist.L":     (0.70, -0.25, 0.55),
    "Mkr_thigh.L":     (0.08, -0.10, 0.45),
    "Mkr_knee.L":      (0.09, -0.15, 0.25),
    "Mkr_ankle.L":     (0.09, -0.08, 0.08),
    "Mkr_foot_toe.L":  (0.09, 0.08, 0.02)
}

def get_marker_pos(name, default_pos, marker_positions=None):
    """Retrieves the position of a viewport marker object if it exists; otherwise returns default."""
    if marker_positions and name in marker_positions:
        return marker_positions[name].copy()
    
    # Try suffix matching to handle prefixes like mukesh_Mkr_
    for obj in bpy.data.objects:
        if obj.name.endswith(name) and ("Mkr_" in obj.name or obj.name.startswith("Mkr_")):
            return obj.location.copy()
            
    # Check if we should search for mirrored name
    if name.endswith(".R"):
        left_name = name[:-2] + ".L"
        if marker_positions and left_name in marker_positions:
            l_pos = marker_positions[left_name].copy()
            l_pos.x = -l_pos.x
            return l_pos
        for obj in bpy.data.objects:
            if obj.name.endswith(left_name) and ("Mkr_" in obj.name or obj.name.startswith("Mkr_")):
                l_pos = obj.location.copy()
                l_pos.x = -l_pos.x
                return l_pos
                
    return mathutils.Vector(default_pos)

def calculate_mesh_landmarks(mesh_obj, rig_type):
    """Calculates coordinates for all landmarks based on the active mesh's bounding box."""
    if not mesh_obj or mesh_obj.type != 'MESH' or len(mesh_obj.data.vertices) == 0:
        return {}
        
    # Extract world-space vertex locations
    vertices = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    
    v_top = max(vertices, key=lambda v: v.z)
    v_bottom = min(vertices, key=lambda v: v.z)
    v_left = max(vertices, key=lambda v: v.x) # Screen left (positive X)
    v_right = min(vertices, key=lambda v: v.x)
    v_front = max(vertices, key=lambda v: v.y)
    v_back = min(vertices, key=lambda v: v.y)
    
    mesh_height = v_top.z - v_bottom.z
    mesh_width = v_left.x - v_right.x
    mesh_depth = v_front.y - v_back.y
    
    center_x = (v_left.x + v_right.x) * 0.5
    center_y = (v_front.y + v_back.y) * 0.5
    
    positions = {}
    
    if rig_type == 'ANIMAL':
        positions = {
            "Mkr_pelvis":      mathutils.Vector((center_x, center_y - mesh_depth * 0.35, v_bottom.z + mesh_height * 0.73)),
            "Mkr_spine":       mathutils.Vector((center_x, center_y - mesh_depth * 0.15, v_bottom.z + mesh_height * 0.78)),
            "Mkr_spine_003":   mathutils.Vector((center_x, center_y + mesh_depth * 0.15, v_bottom.z + mesh_height * 0.78)),
            "Mkr_neck":        mathutils.Vector((center_x, center_y + mesh_depth * 0.35, v_bottom.z + mesh_height * 0.86)),
            "Mkr_head":        mathutils.Vector((center_x, center_y + mesh_depth * 0.50, v_bottom.z + mesh_height * 0.98)),
            "Mkr_tail_base":   mathutils.Vector((center_x, center_y - mesh_depth * 0.40, v_bottom.z + mesh_height * 0.78)),
            "Mkr_tail_mid":    mathutils.Vector((center_x, center_y - mesh_depth * 0.60, v_bottom.z + mesh_height * 0.68)),
            "Mkr_tail_tip":    mathutils.Vector((center_x, center_y - mesh_depth * 0.80, v_bottom.z + mesh_height * 0.52)),
            
            "Mkr_shoulder.L":  mathutils.Vector((center_x + mesh_width * 0.25, center_y + mesh_depth * 0.20, v_bottom.z + mesh_height * 0.73)),
            "Mkr_elbow.L":     mathutils.Vector((center_x + mesh_width * 0.25, center_y + mesh_depth * 0.18, v_bottom.z + mesh_height * 0.40)),
            "Mkr_wrist.L":     mathutils.Vector((center_x + mesh_width * 0.25, center_y + mesh_depth * 0.18, v_bottom.z + mesh_height * 0.12)),
            "Mkr_finger_tip.L": mathutils.Vector((center_x + mesh_width * 0.25, center_y + mesh_depth * 0.28, v_bottom.z + mesh_height * 0.02)),
            
            "Mkr_thigh.L":     mathutils.Vector((center_x + mesh_width * 0.25, center_y - mesh_depth * 0.30, v_bottom.z + mesh_height * 0.73)),
            "Mkr_knee.L":      mathutils.Vector((center_x + mesh_width * 0.25, center_y - mesh_depth * 0.35, v_bottom.z + mesh_height * 0.42)),
            "Mkr_ankle.L":     mathutils.Vector((center_x + mesh_width * 0.25, center_y - mesh_depth * 0.28, v_bottom.z + mesh_height * 0.15)),
            "Mkr_foot_toe.L":  mathutils.Vector((center_x + mesh_width * 0.25, center_y - mesh_depth * 0.20, v_bottom.z + mesh_height * 0.02))
        }
    elif rig_type == 'BIRD':
        sh_pos = mathutils.Vector((center_x + mesh_width * 0.10, center_y + mesh_depth * 0.15, v_bottom.z + mesh_height * 0.66))
        wr_pos = mathutils.Vector((center_x + mesh_width * 0.50, center_y - mesh_depth * 0.25, v_bottom.z + mesh_height * 0.55))
        el_pos = (sh_pos + wr_pos) * 0.5
        el_pos.y -= mesh_depth * 0.1
        
        th_pos = mathutils.Vector((center_x + mesh_width * 0.10, center_y - mesh_depth * 0.10, v_bottom.z + mesh_height * 0.5))
        ak_pos = mathutils.Vector((center_x + mesh_width * 0.10, center_y - mesh_depth * 0.10, v_bottom.z + mesh_height * 0.08))
        kn_pos = (th_pos + ak_pos) * 0.5
        kn_pos.y -= mesh_depth * 0.08
        
        positions = {
            "Mkr_pelvis":      mathutils.Vector((center_x, center_y - mesh_depth * 0.15, v_bottom.z + mesh_height * 0.55)),
            "Mkr_spine":       mathutils.Vector((center_x, center_y + mesh_depth * 0.05, v_bottom.z + mesh_height * 0.61)),
            "Mkr_spine_003":   mathutils.Vector((center_x, center_y + mesh_depth * 0.25, v_bottom.z + mesh_height * 0.66)),
            "Mkr_neck":        mathutils.Vector((center_x, center_y + mesh_depth * 0.35, v_bottom.z + mesh_height * 0.83)),
            "Mkr_head":        mathutils.Vector((center_x, center_y + mesh_depth * 0.45, v_top.z)),
            "Mkr_tail_base":   mathutils.Vector((center_x, center_y - mesh_depth * 0.25, v_bottom.z + mesh_height * 0.57)),
            "Mkr_tail_tip":    mathutils.Vector((center_x, center_y - mesh_depth * 0.50, v_bottom.z + mesh_height * 0.5)),
            
            "Mkr_shoulder.L":  sh_pos,
            "Mkr_elbow.L":     el_pos,
            "Mkr_wrist.L":     wr_pos,
            
            "Mkr_thigh.L":     th_pos,
            "Mkr_knee.L":      kn_pos,
            "Mkr_ankle.L":     ak_pos,
            "Mkr_foot_toe.L":  mathutils.Vector((center_x + mesh_width * 0.10, center_y + mesh_depth * 0.10, v_bottom.z + mesh_height * 0.02))
        }
    else: # HUMAN
        half_width = (v_left.x - v_right.x) * 0.5
        sh_pos = mathutils.Vector((center_x + half_width * 0.23, center_y - 0.03 * mesh_depth, v_bottom.z + mesh_height * 0.76))
        wr_pos = mathutils.Vector((center_x + half_width * 0.88, center_y - 0.05 * mesh_depth, v_bottom.z + mesh_height * 0.75))
        # Keep elbow bent slightly back for arm IK solver
        el_pos = (sh_pos + wr_pos) * 0.5
        el_pos.y += mesh_depth * 0.08
        
        th_pos = mathutils.Vector((center_x + half_width * 0.17, center_y - 0.02 * mesh_depth, v_bottom.z + mesh_height * 0.46))
        ak_pos = mathutils.Vector((center_x + half_width * 0.18, center_y + 0.05 * mesh_depth, v_bottom.z + mesh_height * 0.05))
        # Keep knee bent slightly forward for leg IK solver to bend forward
        kn_pos = (th_pos + ak_pos) * 0.5
        kn_pos.y -= mesh_depth * 0.08
        
        # Calculate dynamic hand scale and rotation based on arm length/direction
        default_sh = mathutils.Vector((0.16, -0.03, 1.43))
        default_wr = mathutils.Vector((0.68, -0.05, 1.42))
        d_len = (default_wr - default_sh).length
        a_len = (wr_pos - sh_pos).length
        hand_scale = a_len / d_len if d_len > 0 else 1.0
        
        default_dir = mathutils.Vector((1.0, 0.0, 0.0))
        actual_dir = (wr_pos - el_pos).normalized()
        if actual_dir.length_squared == 0:
            actual_dir = default_dir.copy()
        rot_q = default_dir.rotation_difference(actual_dir)
        
        finger_defaults = {
            "Mkr_thumb.01.L": (0.70, -0.08, 1.42),
            "Mkr_thumb_tip.L": (0.81, -0.115, 1.40),
            
            "Mkr_index.01.L": (0.76, -0.07, 1.425),
            "Mkr_index.02.L": (0.80, -0.07, 1.425),
            "Mkr_index.03.L": (0.83, -0.07, 1.425),
            "Mkr_index_tip.L": (0.85, -0.07, 1.425),
            
            "Mkr_middle.01.L": (0.76, -0.05, 1.42),
            "Mkr_middle.02.L": (0.81, -0.05, 1.42),
            "Mkr_middle.03.L": (0.85, -0.05, 1.42),
            "Mkr_middle_tip.L": (0.87, -0.05, 1.42),
            
            "Mkr_ring.01.L": (0.76, -0.03, 1.415),
            "Mkr_ring.02.L": (0.80, -0.03, 1.415),
            "Mkr_ring.03.L": (0.83, -0.03, 1.415),
            "Mkr_ring_tip.L": (0.85, -0.03, 1.415),
            
            "Mkr_pinky.01.L": (0.75, -0.01, 1.41),
            "Mkr_pinky.02.L": (0.79, -0.01, 1.41),
            "Mkr_pinky.03.L": (0.82, -0.01, 1.41),
            "Mkr_pinky_tip.L": (0.84, -0.01, 1.41),
        }
        
        positions = {
            "Mkr_pelvis":      mathutils.Vector((center_x, center_y, v_bottom.z + mesh_height * 0.48)),
            "Mkr_spine":       mathutils.Vector((center_x, center_y, v_bottom.z + mesh_height * 0.56)),
            "Mkr_spine_003":   mathutils.Vector((center_x, center_y, v_bottom.z + mesh_height * 0.76)),
            "Mkr_neck":        mathutils.Vector((center_x, center_y - 0.02 * mesh_depth, v_bottom.z + mesh_height * 0.85)),
            "Mkr_head":        mathutils.Vector((center_x, center_y - 0.01 * mesh_depth, v_top.z)),
            
            "Mkr_shoulder.L":  sh_pos,
            "Mkr_elbow.L":     el_pos,
            "Mkr_wrist.L":     wr_pos,
            
            "Mkr_thigh.L":     th_pos,
            "Mkr_knee.L":      kn_pos,
            "Mkr_ankle.L":     ak_pos,
            "Mkr_foot_toe.L":  mathutils.Vector((center_x + half_width * 0.18, center_y - 0.16 * mesh_depth, v_bottom.z + mesh_height * 0.01))
        }
        
        # Calculate face markers dynamically relative to head/neck
        p_neck = positions["Mkr_neck"]
        p_head = positions["Mkr_head"]
        head_h = p_head.z - p_neck.z
        if head_h <= 0.0:
            head_h = 0.26
        face_scale = head_h / 0.26
        
        positions["Mkr_eye.L"] = mathutils.Vector((center_x + 0.035 * face_scale, p_neck.y - 0.06 * face_scale, p_neck.z + 0.14 * face_scale))
        positions["Mkr_eyelid.upper.L"] = positions["Mkr_eye.L"] + mathutils.Vector((0.0, -0.03 * face_scale, 0.02 * face_scale))
        positions["Mkr_eyelid.lower.L"] = positions["Mkr_eye.L"] + mathutils.Vector((0.0, -0.03 * face_scale, -0.02 * face_scale))
        positions["Mkr_eye_corner_inner.L"] = positions["Mkr_eye.L"] + mathutils.Vector((-0.02 * face_scale, -0.01 * face_scale, 0.0))
        positions["Mkr_eye_corner_outer.L"] = positions["Mkr_eye.L"] + mathutils.Vector((0.02 * face_scale, -0.01 * face_scale, 0.0))
        positions["Mkr_eyebrow.01.L"] = mathutils.Vector((center_x + 0.015 * face_scale, p_neck.y - 0.08 * face_scale, p_neck.z + 0.18 * face_scale))
        positions["Mkr_eyebrow.02.L"] = mathutils.Vector((center_x + 0.035 * face_scale, p_neck.y - 0.08 * face_scale, p_neck.z + 0.19 * face_scale))
        positions["Mkr_eyebrow.03.L"] = mathutils.Vector((center_x + 0.055 * face_scale, p_neck.y - 0.07 * face_scale, p_neck.z + 0.18 * face_scale))
        positions["Mkr_cheek.L"] = mathutils.Vector((center_x + 0.050 * face_scale, p_neck.y - 0.05 * face_scale, p_neck.z + 0.08 * face_scale))
        positions["Mkr_lip.corner.L"] = mathutils.Vector((center_x + 0.020 * face_scale, p_neck.y - 0.08 * face_scale, p_neck.z + 0.035 * face_scale))
        positions["Mkr_jaw"] = mathutils.Vector((center_x, p_neck.y - 0.09 * face_scale, p_neck.z - 0.02 * face_scale))
        
        # Add finger marker locations scaled and rotated relative to the wrist
        for mkr_name, def_pos in finger_defaults.items():
            rel_pos = mathutils.Vector(def_pos) - default_wr
            positions[mkr_name] = wr_pos + rot_q @ (rel_pos * hand_scale)
        
    # Generate right counterparts
    right_positions = {}
    for name, pos in positions.items():
        if name.endswith(".L"):
            r_name = name[:-2] + ".R"
            r_pos = pos.copy()
            r_pos.x = -r_pos.x
            right_positions[r_name] = r_pos
            
    positions.update(right_positions)
    return positions

def get_all_marker_positions(context, rig_type, gender="MALE", mesh_obj=None):
    """Scans existing markers in scene, or calculates mesh landmarks, or returns scaled defaults."""
    if not mesh_obj:
        mesh_obj = find_character_mesh(context)
        
    prefix = f"{mesh_obj.name}_" if mesh_obj else ""
    
    # 1. Look for existing marker objects starting with prefix or standard Mkr_
    marker_objs = [obj for obj in context.scene.objects if obj.name.startswith(f"{prefix}Mkr_") or (not prefix and obj.name.startswith("Mkr_"))]
    if len(marker_objs) > 0:
        positions = {}
        for obj in marker_objs:
            # Strip the prefix to get the base marker name (e.g. "Mkr_wrist.L")
            base_name = obj.name[len(prefix):] if obj.name.startswith(prefix) else obj.name
            
            # Clean duplicate suffixes (like .001) from the base name key
            import re
            base_name_clean = re.sub(r'\.\d{3}$', '', base_name)
            positions[base_name_clean] = obj.location.copy()
        
        # Ensure right sides exist by mirroring
        right_positions = {}
        for name, pos in positions.items():
            if name.endswith(".L"):
                r_name = name[:-2] + ".R"
                if r_name not in positions:
                    r_pos = pos.copy()
                    r_pos.x = -r_pos.x
                    right_positions[r_name] = r_pos
        positions.update(right_positions)
        return positions

    # 2. Check active or passed mesh object to calculate automatic positions
    if not mesh_obj:
        mesh_obj = find_character_mesh(context)
    if mesh_obj and mesh_obj.type == 'MESH' and len(mesh_obj.data.vertices) > 0:
        return calculate_mesh_landmarks(mesh_obj, rig_type)

    # 3. Fallback to default scaled positions
    h_scale = 1.0 if gender == "MALE" else 0.9
    w_scale = 1.0 if gender == "MALE" else 0.9
    
    if rig_type == 'ANIMAL':
        markers_data = ANIMAL_MARKERS
    elif rig_type == 'BIRD':
        markers_data = BIRD_MARKERS
    else:
        markers_data = HUMAN_MARKERS
        
    positions = {}
    for name, pos in markers_data.items():
        pos_vec = mathutils.Vector(pos)
        # Apply scaling
        if name.endswith(".L") or name.endswith(".R"):
            pos_vec.x *= w_scale
            # For feet/arms/shoulders we scale height
            pos_vec.z *= h_scale
        else:
            pos_vec.z *= h_scale
        positions[name] = pos_vec
        
    # Handle right side mirrors
    right_positions = {}
    for name, pos in positions.items():
        if name.endswith(".L"):
            r_name = name[:-2] + ".R"
            r_pos = pos.copy()
            r_pos.x = -r_pos.x
            right_positions[r_name] = r_pos
    positions.update(right_positions)
    
    return positions

def find_character_mesh(context):
    """Finds the most likely character mesh in the scene."""
    # 1. Check active object
    active = context.active_object
    if active and active.type == 'MESH' and not active.name.startswith("Wgt_"):
        return active
        
    # 2. Check selected objects
    selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH' and not obj.name.startswith("Wgt_")]
    if selected_meshes:
        return selected_meshes[0]
        
    # 3. Scan all meshes in the scene and pick the one with the most vertices
    all_meshes = [obj for obj in context.scene.objects if obj.type == 'MESH' and not obj.name.startswith("Wgt_")]
    if all_meshes:
        # Sort by vertex count descending to find the main character mesh
        all_meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
        return all_meshes[0]
        
    return None

