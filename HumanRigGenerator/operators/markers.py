# operators/markers.py
import bpy
import mathutils
from ..utils.naming import get_opposite_side_name

HUMAN_MARKERS = {
    "Mkr_pelvis":    (0.0, 0.0, 0.95),
    "Mkr_spine":     (0.0, 0.0, 1.05),
    "Mkr_spine_003": (0.0, 0.0, 1.48),
    "Mkr_neck":      (0.0, -0.02, 1.62),
    "Mkr_head":      (0.0, -0.01, 1.88),
    "Mkr_shoulder.L":  (0.16, -0.03, 1.43),
    "Mkr_elbow.L":     (0.42, 0.04, 1.42),
    "Mkr_wrist.L":     (0.68, -0.05, 1.42),
    "Mkr_thigh.L":     (0.12, -0.02, 0.86),
    "Mkr_knee.L":      (0.13, -0.08, 0.48),
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
    "Mkr_pinky_tip.L": (0.84, -0.01, 1.41),
    
    # Face Markers (Left side and center)
    "Mkr_eye.L":          (0.035, -0.08, 1.76),
    "Mkr_eyelid.upper.L": (0.035, -0.11, 1.78),
    "Mkr_eyelid.lower.L": (0.035, -0.11, 1.74),
    "Mkr_eye_corner_inner.L": (0.015, -0.09, 1.76),
    "Mkr_eye_corner_outer.L": (0.055, -0.09, 1.76),
    "Mkr_eyebrow.01.L":   (0.015, -0.10, 1.80),
    "Mkr_eyebrow.02.L":   (0.035, -0.10, 1.81),
    "Mkr_eyebrow.03.L":   (0.055, -0.09, 1.80),
    "Mkr_cheek.L":        (0.050, -0.07, 1.70),
    "Mkr_lip.corner.L":    (0.020, -0.10, 1.655),
    "Mkr_jaw":            (0.0, -0.12, 1.60)
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

class OBJECT_OT_spawn_markers(bpy.types.Operator):
    """Spawns 3D Empty markers to align the rig to a character mesh."""
    bl_idname = "object.spawn_markers"
    bl_label = "Spawn Alignment Markers"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Analyze active object if it is a Mesh
        from ..utils.bones import find_character_mesh, calculate_mesh_landmarks
        mesh_obj = find_character_mesh(context)
        
        # Determine prefix and collection name based on mesh name
        if mesh_obj:
            prefix = f"{mesh_obj.name}_"
            coll_name = f"{mesh_obj.name}_Markers"
        else:
            prefix = ""
            coll_name = "Rig_Markers"
            
        # 1. Create or get collection
        coll = bpy.data.collections.get(coll_name)
        if not coll:
            coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(coll)
            
        # Clear existing markers starting with the prefix inside the collection
        for m_obj in list(coll.objects):
            if m_obj.name.startswith(f"{prefix}Mkr_") or (not prefix and m_obj.name.startswith("Mkr_")):
                bpy.data.objects.remove(m_obj, do_unlink=True)
            
        # 2. Select coordinate set based on scene property
        rig_type = context.scene.hrg_rig_type
        if rig_type == 'ANIMAL':
            markers_data = ANIMAL_MARKERS
            base_height, base_width, base_depth = 0.95, 0.36, 1.65
        elif rig_type == 'BIRD':
            markers_data = BIRD_MARKERS
            base_height, base_width, base_depth = 0.90, 1.40, 0.72
        else:
            markers_data = HUMAN_MARKERS
            base_height, base_width, base_depth = 1.88, 1.36, 0.32
            
        landmark_positions = {}
        mkr_size = 0.05
        
        if mesh_obj and mesh_obj.type == 'MESH' and len(mesh_obj.data.vertices) > 0:
            landmark_positions = calculate_mesh_landmarks(mesh_obj, rig_type)
            # Calculate dynamic empty display size based on mesh height (2.5% of mesh height)
            vertices = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
            v_top = max(vertices, key=lambda v: v.z)
            v_bottom = min(vertices, key=lambda v: v.z)
            mesh_height = v_top.z - v_bottom.z
            if mesh_height > 0.0:
                mkr_size = max(0.002, mesh_height * 0.025)
            
        context.scene.hrg_marker_size = mkr_size
            
        # 3. Spawn markers
        for name, pos in markers_data.items():
            mkr_name = f"{prefix}{name}"
            obj = bpy.data.objects.new(mkr_name, None)
            obj.empty_display_type = 'SPHERE'
            obj.empty_display_size = context.scene.hrg_marker_size
            obj.show_name = context.scene.hrg_show_marker_names
            coll.objects.link(obj)
            
            if name in landmark_positions:
                obj.location = landmark_positions[name]
            else:
                obj.location = mathutils.Vector(pos)
            
            # Also generate right side counterparts automatically on spawn
            if name.endswith(".L"):
                r_name = get_opposite_side_name(name)
                mkr_r_name = f"{prefix}{r_name}"
                r_obj = bpy.data.objects.new(mkr_r_name, None)
                r_obj.empty_display_type = 'SPHERE'
                r_obj.empty_display_size = context.scene.hrg_marker_size
                r_obj.show_name = context.scene.hrg_show_marker_names
                coll.objects.link(r_obj)
                
                r_pos = obj.location.copy()
                r_pos.x = -r_pos.x
                r_obj.location = r_pos
                
        self.report({'INFO'}, f"Spawned {rig_type} rig alignment markers with prefix '{prefix}'. Position them on your mesh!")
        return {'FINISHED'}

class OBJECT_OT_mirror_markers(bpy.types.Operator):
    """Mirrors the positions of left markers (.L) to the right side (.R)."""
    bl_idname = "object.mirror_markers"
    bl_label = "Mirror Left Markers"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        import re
        mirrored_count = 0
        coll = bpy.data.collections.get("Rig_Markers")
        if not coll:
            coll = context.scene.collection
            
        for obj in context.scene.objects:
            if "Mkr_" in obj.name:
                idx = obj.name.find("Mkr_")
                prefix = obj.name[:idx]
                name_clean = obj.name[idx:]
                
                # Parse duplicate suffixes (e.g., .001)
                suffix = ""
                suffix_match = re.search(r'\.\d{3}$', name_clean)
                if suffix_match:
                    suffix = suffix_match.group(0)
                    name_clean = name_clean[:-4]
                    
                if name_clean.endswith(".L"):
                    r_base = name_clean[:-2] + ".R"
                    r_name = prefix + r_base + suffix
                    
                    r_obj = context.scene.objects.get(r_name)
                    if not r_obj:
                        # Determine correct collection based on prefix
                        coll_name = f"{prefix[:-1]}_Markers" if prefix else "Rig_Markers"
                        r_coll = bpy.data.collections.get(coll_name)
                        if not r_coll:
                            r_coll = coll
                            
                        # Re-create the right-side marker if it was deleted
                        r_obj = bpy.data.objects.new(r_name, None)
                        r_obj.empty_display_type = obj.empty_display_type
                        r_obj.empty_display_size = obj.empty_display_size
                        r_obj.show_name = obj.show_name
                        r_coll.objects.link(r_obj)
                        
                    r_pos = obj.location.copy()
                    r_pos.x = -r_pos.x
                    r_obj.location = r_pos
                    mirrored_count += 1
                    
        self.report({'INFO'}, f"Mirrored and aligned {mirrored_count} markers successfully!")
        return {'FINISHED'}

# PLACEMENT SEQUENCE for Interactive Marker Placement
PLACEMENT_SEQUENCE = [
    ("Mkr_pelvis", "Pelvis"),
    ("Mkr_spine", "Spine Base"),
    ("Mkr_spine_003", "Chest / Upper Spine"),
    ("Mkr_neck", "Neck Joint"),
    ("Mkr_head", "Head Top / Center"),
    ("Mkr_jaw", "Jaw Joint"),
    ("Mkr_shoulder.L", "Left Shoulder"),
    ("Mkr_elbow.L", "Left Elbow"),
    ("Mkr_wrist.L", "Left Wrist"),
    
    # Thumb
    ("Mkr_thumb.01.L", "Left Thumb Base"),
    ("Mkr_thumb_tip.L", "Left Thumb Tip"),
    
    # Index
    ("Mkr_index.01.L", "Left Index Knuckle"),
    ("Mkr_index.02.L", "Left Index Joint 2"),
    ("Mkr_index.03.L", "Left Index Joint 3"),
    ("Mkr_index_tip.L", "Left Index Tip"),
    
    # Middle
    ("Mkr_middle.01.L", "Left Middle Knuckle"),
    ("Mkr_middle.02.L", "Left Middle Joint 2"),
    ("Mkr_middle.03.L", "Left Middle Joint 3"),
    ("Mkr_middle_tip.L", "Left Middle Tip"),
    
    # Ring
    ("Mkr_ring.01.L", "Left Ring Knuckle"),
    ("Mkr_ring.02.L", "Left Ring Joint 2"),
    ("Mkr_ring.03.L", "Left Ring Joint 3"),
    ("Mkr_ring_tip.L", "Left Ring Tip"),
    
    # Pinky
    ("Mkr_pinky.01.L", "Left Pinky Knuckle"),
    ("Mkr_pinky.02.L", "Left Pinky Joint 2"),
    ("Mkr_pinky.03.L", "Left Pinky Joint 3"),
    ("Mkr_pinky_tip.L", "Left Pinky Tip"),
    
    # Legs
    ("Mkr_thigh.L", "Left Hip / Thigh"),
    ("Mkr_knee.L", "Left Knee"),
    ("Mkr_ankle.L", "Left Ankle"),
    ("Mkr_foot_toe.L", "Left Toe Joint"),
    
    # Face
    ("Mkr_eye.L", "Left Eye Center"),
    ("Mkr_eyelid.upper.L", "Left Upper Eyelid"),
    ("Mkr_eyelid.lower.L", "Left Lower Eyelid"),
    ("Mkr_eye_corner_inner.L", "Left Eye Inner Corner"),
    ("Mkr_eye_corner_outer.L", "Left Eye Outer Corner"),
    ("Mkr_eyebrow.01.L", "Left Eyebrow Inner"),
    ("Mkr_eyebrow.02.L", "Left Eyebrow Middle"),
    ("Mkr_eyebrow.03.L", "Left Eyebrow Outer"),
    ("Mkr_cheek.L", "Left Cheek"),
    ("Mkr_lip.corner.L", "Left Mouth Corner"),
]

MARKER_CONNECTIONS = [
    # Spine / Head
    ("Mkr_pelvis", "Mkr_spine"),
    ("Mkr_spine", "Mkr_spine_003"),
    ("Mkr_spine_003", "Mkr_neck"),
    ("Mkr_neck", "Mkr_head"),
    ("Mkr_head", "Mkr_jaw"),
    
    # Left Leg
    ("Mkr_pelvis", "Mkr_thigh.L"),
    ("Mkr_thigh.L", "Mkr_knee.L"),
    ("Mkr_knee.L", "Mkr_ankle.L"),
    ("Mkr_ankle.L", "Mkr_foot_toe.L"),
    
    # Right Leg
    ("Mkr_pelvis", "Mkr_thigh.R"),
    ("Mkr_thigh.R", "Mkr_knee.R"),
    ("Mkr_knee.R", "Mkr_ankle.R"),
    ("Mkr_ankle.R", "Mkr_foot_toe.R"),
    
    # Left Arm
    ("Mkr_spine_003", "Mkr_shoulder.L"),
    ("Mkr_shoulder.L", "Mkr_elbow.L"),
    ("Mkr_elbow.L", "Mkr_wrist.L"),
    
    # Right Arm
    ("Mkr_spine_003", "Mkr_shoulder.R"),
    ("Mkr_shoulder.R", "Mkr_elbow.R"),
    ("Mkr_elbow.R", "Mkr_wrist.R"),
    
    # Left Fingers
    ("Mkr_wrist.L", "Mkr_thumb.01.L"),
    ("Mkr_thumb.01.L", "Mkr_thumb_tip.L"),
    
    ("Mkr_wrist.L", "Mkr_index.01.L"),
    ("Mkr_index.01.L", "Mkr_index.02.L"),
    ("Mkr_index.02.L", "Mkr_index.03.L"),
    ("Mkr_index.03.L", "Mkr_index_tip.L"),
    
    ("Mkr_wrist.L", "Mkr_middle.01.L"),
    ("Mkr_middle.01.L", "Mkr_middle.02.L"),
    ("Mkr_middle.02.L", "Mkr_middle.03.L"),
    ("Mkr_middle.03.L", "Mkr_middle_tip.L"),
    
    ("Mkr_wrist.L", "Mkr_ring.01.L"),
    ("Mkr_ring.01.L", "Mkr_ring.02.L"),
    ("Mkr_ring.02.L", "Mkr_ring.03.L"),
    ("Mkr_ring.03.L", "Mkr_ring_tip.L"),
    
    ("Mkr_wrist.L", "Mkr_pinky.01.L"),
    ("Mkr_pinky.01.L", "Mkr_pinky.02.L"),
    ("Mkr_pinky.02.L", "Mkr_pinky.03.L"),
    ("Mkr_pinky.03.L", "Mkr_pinky_tip.L"),
    
    # Right Fingers
    ("Mkr_wrist.R", "Mkr_thumb.01.R"),
    ("Mkr_thumb.01.R", "Mkr_thumb_tip.R"),
    
    ("Mkr_wrist.R", "Mkr_index.01.R"),
    ("Mkr_index.01.R", "Mkr_index.02.R"),
    ("Mkr_index.02.R", "Mkr_index.03.R"),
    ("Mkr_index.03.R", "Mkr_index_tip.R"),
    
    ("Mkr_wrist.R", "Mkr_middle.01.R"),
    ("Mkr_middle.01.R", "Mkr_middle.02.R"),
    ("Mkr_middle.02.R", "Mkr_middle.03.R"),
    ("Mkr_middle.03.R", "Mkr_middle_tip.R"),
    
    ("Mkr_wrist.R", "Mkr_ring.01.R"),
    ("Mkr_ring.01.R", "Mkr_ring.02.R"),
    ("Mkr_ring.02.R", "Mkr_ring.03.R"),
    ("Mkr_ring.03.R", "Mkr_ring_tip.R"),
    
    ("Mkr_wrist.R", "Mkr_pinky.01.R"),
    ("Mkr_pinky.01.R", "Mkr_pinky.02.R"),
    ("Mkr_pinky.02.R", "Mkr_pinky.03.R"),
    ("Mkr_pinky.03.R", "Mkr_pinky_tip.R"),
    
    # Face features (Left)
    ("Mkr_head", "Mkr_eye.L"),
    ("Mkr_eye.L", "Mkr_eye_corner_inner.L"),
    ("Mkr_eye.L", "Mkr_eye_corner_outer.L"),
    ("Mkr_eye_corner_inner.L", "Mkr_eyelid.upper.L"),
    ("Mkr_eyelid.upper.L", "Mkr_eye_corner_outer.L"),
    ("Mkr_eye_corner_inner.L", "Mkr_eyelid.lower.L"),
    ("Mkr_eyelid.lower.L", "Mkr_eye_corner_outer.L"),
    ("Mkr_head", "Mkr_eyebrow.01.L"),
    ("Mkr_eyebrow.01.L", "Mkr_eyebrow.02.L"),
    ("Mkr_eyebrow.02.L", "Mkr_eyebrow.03.L"),
    ("Mkr_head", "Mkr_cheek.L"),
    ("Mkr_head", "Mkr_lip.corner.L"),
    
    # Face features (Right)
    ("Mkr_head", "Mkr_eye.R"),
    ("Mkr_eye.R", "Mkr_eye_corner_inner.R"),
    ("Mkr_eye.R", "Mkr_eye_corner_outer.R"),
    ("Mkr_eye_corner_inner.R", "Mkr_eyelid.upper.R"),
    ("Mkr_eyelid.upper.R", "Mkr_eye_corner_outer.R"),
    ("Mkr_eye_corner_inner.R", "Mkr_eyelid.lower.R"),
    ("Mkr_eyelid.lower.R", "Mkr_eye_corner_outer.R"),
    ("Mkr_head", "Mkr_eyebrow.01.R"),
    ("Mkr_eyebrow.01.R", "Mkr_eyebrow.02.R"),
    ("Mkr_eyebrow.02.R", "Mkr_eyebrow.03.R"),
    ("Mkr_head", "Mkr_cheek.R"),
    ("Mkr_head", "Mkr_lip.corner.R"),
]

# Viewport Skeleton drawing callback using the gpu module (prevents depsgraph recursion loop)
_draw_handle_skeleton = None

def draw_skeleton_callback():
    import bpy
    if not getattr(bpy.context.scene, "hrg_show_marker_lines", True):
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    
    # 1. Scan for active marker prefixes in the scene
    prefixes = set()
    for obj in bpy.data.objects:
        if "Mkr_" in obj.name and obj.type == 'EMPTY':
            idx = obj.name.find("Mkr_")
            prefixes.add(obj.name[:idx])
            
    if not prefixes:
        return
        
    # 2. Draw lines between existing markers
    for prefix in prefixes:
        points = []
        for m1_name, m2_name in MARKER_CONNECTIONS:
            o1 = bpy.data.objects.get(f"{prefix}{m1_name}")
            o2 = bpy.data.objects.get(f"{prefix}{m2_name}")
            if o1 and o2:
                points.append(o1.location)
                points.append(o2.location)
                
        if not points:
            continue
            
        # Get compatible shader
        try:
            shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        except:
            try:
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            except:
                shader = gpu.shader.from_builtin('FLAT_COLOR')
                
        batch = batch_for_shader(shader, 'LINES', {"pos": points})
        shader.bind()
        shader.uniform_float("color", (0.0, 1.0, 1.0, 1.0)) # Cyan
        
        # Set line width
        try:
            gpu.state.line_width_set(3.0)
        except:
            pass
            
        batch.draw(shader)

def register_skeleton_draw():
    global _draw_handle_skeleton
    if _draw_handle_skeleton is None:
        try:
            _draw_handle_skeleton = bpy.types.SpaceView3D.draw_handler_add(
                draw_skeleton_callback, (), 'WINDOW', 'POST_VIEW'
            )
        except Exception as e:
            print(f"[Rig Generator] Failed to register skeleton draw callback: {str(e)}")

def unregister_skeleton_draw():
    global _draw_handle_skeleton
    if _draw_handle_skeleton is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle_skeleton, 'WINDOW')
        except Exception as e:
            print(f"[Rig Generator] Failed to remove skeleton draw callback: {str(e)}")
        _draw_handle_skeleton = None

def draw_placement_callback(self, context):
    import blf
    font_id = 0
    
    # HUD title
    blf.size(font_id, 20)
    blf.color(font_id, 0.0, 1.0, 1.0, 1.0) # Cyan
    x = 30
    y = 70
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, "Rig Generator Interactive Placement HUD")
    
    # Joint Instruction
    if self.current_idx < len(PLACEMENT_SEQUENCE):
        mkr_key, mkr_label = PLACEMENT_SEQUENCE[self.current_idx]
        blf.size(font_id, 16)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0) # White
        blf.position(font_id, x, y - 25, 0)
        blf.draw(font_id, f">> LEFT-CLICK Mesh to place: {mkr_label} ({self.current_idx + 1}/{len(PLACEMENT_SEQUENCE)})")
    
    # Guides
    blf.size(font_id, 12)
    blf.color(font_id, 0.7, 0.7, 0.7, 1.0) # Gray
    blf.position(font_id, x, y - 48, 0)
    blf.draw(font_id, "[Left-Click: Place | Ctrl+Z: Undo | Tab: Skip | ESC: Exit]")

class OBJECT_OT_interactive_marker_place(bpy.types.Operator):
    """Interactively place rig alignment markers step-by-step by clicking on mesh."""
    bl_idname = "object.interactive_marker_place"
    bl_label = "Click to Place Markers"
    bl_options = {'REGISTER', 'UNDO'}
    
    _handle = None
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        # Explicitly check for escape to exit immediately at the very top of event loop!
        if event.type == 'ESC' and event.value == 'PRESS':
            self.cleanup(context)
            self.report({'INFO'}, "Interactive marker placement completed.")
            return {'FINISHED'}
            
        # Intercept Ctrl+Z inside placement mode to undo the last placed marker!
        if event.ctrl and event.type == 'Z' and event.value == 'PRESS':
            if self.current_idx > 0:
                self.current_idx -= 1
                mkr_key, mkr_label = PLACEMENT_SEQUENCE[self.current_idx]
                mkr_name = f"{self.prefix}{mkr_key}"
                obj = bpy.data.objects.get(mkr_name)
                if obj:
                    bpy.data.objects.remove(obj, do_unlink=True)
                if mkr_key.endswith(".L"):
                    r_key = get_opposite_side_name(mkr_key)
                    r_name = f"{self.prefix}{r_key}"
                    r_obj = bpy.data.objects.get(r_name)
                    if r_obj:
                        bpy.data.objects.remove(r_obj, do_unlink=True)
                context.area.tag_redraw()
                self.update_status(context)
                self.report({'INFO'}, f"Undo: Back to placing {mkr_label}")
                return {'RUNNING_MODAL'}
            return {'RUNNING_MODAL'}
            
        if not context.scene.objects:
            self.cleanup(context)
            return {'FINISHED'}
            
        # Allow standard navigation to pass through
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NDOF_MOTION'} or event.shift or event.ctrl or event.alt:
            return {'PASS_THROUGH'}
            
        # Allow other events to pass through so the user can orbit, pan, select, and grab
        if event.type not in {'LEFTMOUSE', 'TAB'}:
            return {'PASS_THROUGH'}
            
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            import bpy_extras.view3d_utils
            event_pos = (event.mouse_region_x, event.mouse_region_y)
            region = context.region
            rv3d = context.region_data
            
            ray_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, event_pos)
            ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, event_pos)
            
            mesh_obj = bpy.data.objects.get(self.mesh_obj_name)
            if mesh_obj and mesh_obj.type == 'MESH':
                matrix_inv = mesh_obj.matrix_world.inverted()
                ray_origin_local = matrix_inv @ ray_origin
                ray_vector_local = matrix_inv.to_3x3() @ ray_vector
                
                success, location, normal, face_index = mesh_obj.ray_cast(ray_origin_local, ray_vector_local)
                if success:
                    world_loc = mesh_obj.matrix_world @ location
                    
                    mkr_key, mkr_label = PLACEMENT_SEQUENCE[self.current_idx]
                    mkr_name = f"{self.prefix}{mkr_key}"
                    
                    # Create empty marker
                    obj = bpy.data.objects.get(mkr_name)
                    if not obj:
                        obj = bpy.data.objects.new(mkr_name, None)
                        obj.empty_display_type = 'SPHERE'
                        obj.empty_display_size = context.scene.hrg_marker_size
                        obj.show_name = context.scene.hrg_show_marker_names
                        self.coll.objects.link(obj)
                        
                    obj.location = world_loc
                    
                    # Real-time left-to-right mirroring symmetry
                    if mkr_key.endswith(".L"):
                        r_key = get_opposite_side_name(mkr_key)
                        r_name = f"{self.prefix}{r_key}"
                        
                        r_obj = bpy.data.objects.get(r_name)
                        if not r_obj:
                            r_obj = bpy.data.objects.new(r_name, None)
                            r_obj.empty_display_type = 'SPHERE'
                            r_obj.empty_display_size = context.scene.hrg_marker_size
                            r_obj.show_name = context.scene.hrg_show_marker_names
                            self.coll.objects.link(r_obj)
                            
                        r_pos = world_loc.copy()
                        r_pos.x = -r_pos.x
                        r_obj.location = r_pos
                        
                    # Redraw viewport to update skeleton visualizer lines
                    context.area.tag_redraw()
                    
                    self.current_idx += 1
                    if self.current_idx >= len(PLACEMENT_SEQUENCE):
                        self.cleanup(context)
                        self.report({'INFO'}, "All markers placed successfully!")
                        return {'FINISHED'}
                        
                    self.update_status(context)
                    return {'RUNNING_MODAL'}
            
            # If click was not on the mesh, let Blender select objects/markers normally!
            return {'PASS_THROUGH'}
                
        if event.type == 'TAB' and event.value == 'PRESS':
            self.current_idx += 1
            if self.current_idx >= len(PLACEMENT_SEQUENCE):
                self.cleanup(context)
                self.report({'INFO'}, "Marker placement finished.")
                return {'FINISHED'}
            self.update_status(context)
            return {'RUNNING_MODAL'}
            
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'WARNING'}, "Please select the active character mesh first!")
            return {'CANCELLED'}
            
        # Lock placement raycasts onto this specific mesh object
        self.mesh_obj_name = mesh_obj.name
            
        # Determine prefix based on mesh name
        self.prefix = f"{mesh_obj.name}_"
        self.coll_name = f"{mesh_obj.name}_Markers"
        
        # Initialize collection
        self.coll = bpy.data.collections.get(self.coll_name)
        if not self.coll:
            self.coll = bpy.data.collections.new(self.coll_name)
            context.scene.collection.children.link(self.coll)
            
        # Set dynamic display size
        mkr_size = 0.05
        vertices = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
        if vertices:
            v_top = max(vertices, key=lambda v: v.z)
            v_bottom = min(vertices, key=lambda v: v.z)
            mesh_height = v_top.z - v_bottom.z
            if mesh_height > 0.0:
                mkr_size = max(0.002, mesh_height * 0.025)
        context.scene.hrg_marker_size = mkr_size
        
        # Remove legacy skeleton mesh if exists to prevent duplicate guidelines
        try:
            skeleton_name = f"{self.prefix}Rig_Markers_Skeleton"
            legacy_obj = bpy.data.objects.get(skeleton_name)
            if legacy_obj:
                bpy.data.objects.remove(legacy_obj, do_unlink=True)
            legacy_mesh = bpy.data.meshes.get(skeleton_name)
            if legacy_mesh:
                bpy.data.meshes.remove(legacy_mesh)
        except:
            pass
            
        # Scan for existing markers in sequence to resume drawing where left off!
        self.current_idx = 0
        for i, (mkr_key, mkr_label) in enumerate(PLACEMENT_SEQUENCE):
            mkr_name = f"{self.prefix}{mkr_key}"
            if bpy.data.objects.get(mkr_name) is not None:
                self.current_idx = i + 1
            else:
                self.current_idx = i
                break
        if self.current_idx >= len(PLACEMENT_SEQUENCE):
            self.current_idx = 0
            
        self.update_status(context)
        
        # Add draw callback to 3D viewport
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_placement_callback, (self, context), 'WINDOW', 'POST_PIXEL'
        )
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
        
    def update_status(self, context):
        mkr_key, mkr_label = PLACEMENT_SEQUENCE[self.current_idx]
        msg = f"PLACING MARKER [{self.current_idx + 1}/{len(PLACEMENT_SEQUENCE)}]: Click to place {mkr_label}. (Tab-Key to Skip, ESC to Exit)"
        context.workspace.status_text_set_internal(msg)
        
    def cleanup(self, context):
        try:
            context.workspace.status_text_set_internal(None)
        except:
            pass
        if self._handle:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except Exception as e:
                print(f"[Rig Generator] Failed to remove draw handler: {str(e)}")
            self._handle = None

# App Depsgraph Update Post Handler for real-time automatic visual skeleton and mirror coordinate updates
@bpy.app.handlers.persistent
def on_depsgraph_update(scene, depsgraph):
    try:
        ctx = bpy.context
        active = ctx.active_object
        if active and "Mkr_" in active.name:
            idx = active.name.find("Mkr_")
            prefix = active.name[:idx]
            
            # Mirror the left side to right side in real-time if dragging or adjusting
            if active.name.endswith(".L"):
                from .naming import get_opposite_side_name
                r_key = get_opposite_side_name(active.name[idx:])
                r_name = prefix + r_key
                r_obj = bpy.data.objects.get(r_name)
                if r_obj:
                    r_pos = active.location.copy()
                    r_pos.x = -r_pos.x
                    r_obj.location = r_pos
                    
            # Mirror the right side to left side in real-time if dragging or adjusting
            elif active.name.endswith(".R"):
                from .naming import get_opposite_side_name
                l_key = get_opposite_side_name(active.name[idx:])
                l_name = prefix + l_key
                l_obj = bpy.data.objects.get(l_name)
                if l_obj:
                    l_pos = active.location.copy()
                    l_pos.x = -l_pos.x
                    l_obj.location = l_pos
                    
            # Request redraw to update GPU skeleton visualizer lines in real-time
            ctx.area.tag_redraw()
    except Exception:
        pass
