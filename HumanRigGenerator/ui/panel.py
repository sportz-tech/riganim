# ui/panel.py
import bpy
from ..utils.naming import get_control_name

class VIEW3D_PT_human_rig_generator(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar."""
    bl_label = "Human Rig Generator"
    bl_idname = "VIEW3D_PT_human_rig_generator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Human Rig'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object
        
        # Actor Manager Section
        box_actor = layout.box()
        row_act = box_actor.row(align=True)
        icon_act = 'TRIA_DOWN' if scene.hrg_show_actor else 'TRIA_RIGHT'
        row_act.prop(scene, "hrg_show_actor", text="Actor Manager (Clones & Cleanup)", icon=icon_act, emboss=False)
        if scene.hrg_show_actor:
            col_actor = box_actor.column(align=True)
            col_actor.prop(scene, "hrg_active_actor", text="Active Actor")
            col_actor.separator()
            
            row_clone = col_actor.row(align=True)
            row_clone.prop(scene, "hrg_clone_count", text="Count")
            row_clone.operator("object.clone_character_actor", text="Clone Actor", icon='DUPLICATE')
            
            col_actor.separator()
            col_actor.operator("object.reset_rig_to_origin", text="Snap Rig to Origin (0,0,0)", icon='SNAP_GRID')
            
            row_clean = col_actor.row(align=True)
            row_clean.operator("object.delete_character_actor", text="Delete Actor & Clean", icon='TRASH')
            row_clean.operator("object.purge_unused_collections", text="Clean Collections", icon='BRUSH_DATA')

        # Dedicated Surface Spawn Points & Travel Section
        box_spawn = layout.box()
        row_spawn_hdr = box_spawn.row(align=True)
        icon_sp = 'TRIA_DOWN' if getattr(scene, "hrg_show_spawn", True) else 'TRIA_RIGHT'
        row_spawn_hdr.prop(scene, "hrg_show_spawn", text="Surface Spawn Points & Travel", icon=icon_sp, emboss=False)
        if getattr(scene, "hrg_show_spawn", True):
            col_sp = box_spawn.column(align=True)
            
            row_sp_btns = col_sp.row(align=True)
            row_sp_btns.operator("object.interactive_spawn_point_place", text="Click to Mark Points", icon='RESTRICT_SELECT_OFF')
            row_sp_btns.operator("object.add_spawn_point_at_cursor", text="Add at Cursor", icon='CURSOR')
            
            col_sp.operator("object.clone_to_spawn_points", text="Clone Character to Marked Points", icon='OUTLINER_OB_ARMATURE')
            
            # Keyframe Travel to Marked Point / Cursor
            box_travel = col_sp.box()
            box_travel.label(text="Keyframe Travel to Point / Cursor:", icon='PLAY')
            row_trav_set = box_travel.row(align=True)
            row_trav_set.prop(scene, "hrg_travel_duration", text="Frames")
            row_trav_set.prop(scene, "hrg_travel_mode", text="")
            
            op_move = box_travel.operator("object.keyframe_move_to_point", text="Move / Animate Rig to Point", icon='FORWARD')
            op_move.duration = scene.hrg_travel_duration
            op_move.mode = scene.hrg_travel_mode
            
            col_sp.operator("object.clear_spawn_points", text="Clear Spawn Points", icon='X')

        # Prop & Tool Attacher
        box_prop = layout.box()
        row_prop = box_prop.row(align=True)
        icon_prop = 'TRIA_DOWN' if scene.hrg_show_props else 'TRIA_RIGHT'
        row_prop.prop(scene, "hrg_show_props", text="Prop & Tool Attacher", icon=icon_prop, emboss=False)
        if scene.hrg_show_props:
            col_prop = box_prop.column(align=True)
            col_prop.prop(scene, "hrg_prop_object", text="Prop")
            col_prop.prop(scene, "hrg_prop_target_actor", text="Holder Actor")
            col_prop.prop(scene, "hrg_prop_slot", text="Slot")
            col_prop.separator()
            
            row_att = col_prop.row(align=True)
            row_att.operator("object.attach_prop", text="Attach Prop", icon='CONSTRAINT')
            row_att.operator("object.detach_prop", text="Detach", icon='X')
            
            box_anim_prop = col_prop.box()
            box_anim_prop.label(text="Timeline Grab & Drop:", icon='TIME')
            row_grab = box_anim_prop.row(align=True)
            row_grab.operator("object.keyframe_prop_pickup", text="Grab at Frame", icon='HAND')
            row_grab.operator("object.keyframe_prop_drop", text="Drop at Frame", icon='UNPINNED')

        # 1. Alignment Marker Options
        box_mkr = layout.box()
        row_mkr = box_mkr.row(align=True)
        icon_mkr = 'TRIA_DOWN' if scene.hrg_show_markers else 'TRIA_RIGHT'
        row_mkr.prop(scene, "hrg_show_markers", text="Marker Alignment (Optional)", icon=icon_mkr, emboss=False)
        if scene.hrg_show_markers:
            col_mkr = box_mkr.column(align=True)
            col_mkr.operator("object.spawn_markers", text="Spawn Alignment Markers", icon='ADD')
            col_mkr.operator("object.interactive_marker_place", text="Click to Place Markers", icon='HAND')
            col_mkr.operator("object.mirror_markers", text="Mirror Left Markers", icon='MOD_MIRROR')
            
            # Check if markers exist in the scene to show display size slider
            has_markers = any("Mkr_" in obj.name for obj in context.scene.objects)
            if has_markers:
                col_mkr.separator()
                col_mkr.prop(scene, "hrg_marker_size", text="Marker Display Size", slider=True)
                col_mkr.prop(scene, "hrg_show_marker_names", text="Show Marker Names")
                col_mkr.prop(scene, "hrg_show_marker_lines", text="Show Marker Lines")
            
        # 2. Generator Section
        box = layout.box()
        row_gen = box.row(align=True)
        icon_gen = 'TRIA_DOWN' if scene.hrg_show_generator else 'TRIA_RIGHT'
        row_gen.prop(scene, "hrg_show_generator", text="Generator Options", icon=icon_gen, emboss=False)
        if scene.hrg_show_generator:
            col = box.column(align=True)
            col.prop(scene, "hrg_rig_type", text="Rig Type")
            col.operator("object.generate_human_rig", text="Generate Rig", icon='ARMATURE_DATA')
            col.separator()
            col.operator("object.auto_skin_mesh", text="Auto-Skin Mesh to Rig", icon='MOD_ARMATURE')
        
        # 3. Animation Presets (visible when rig is selected)
        if obj and obj.type == 'ARMATURE':
            # Section A: Animation Sequencer
            box_anim = layout.box()
            row_anim = box_anim.row(align=True)
            icon_anim = 'TRIA_DOWN' if scene.hrg_show_sequencer else 'TRIA_RIGHT'
            row_anim.prop(scene, "hrg_show_sequencer", text="Animation Sequencer", icon=icon_anim, emboss=False)
            if scene.hrg_show_sequencer:
                col_anim = box_anim.column(align=True)
                col_anim.prop(scene, "hrg_preset", text="Preset")
                col_anim.prop(scene, "hrg_start_frame", text="Start Frame")
                col_anim.prop(scene, "hrg_preset_duration", text="Duration (Frames)")
                col_anim.prop(scene, "hrg_set_timeline_range", text="Auto-Fit Timeline Range")
                col_anim.prop(scene, "hrg_anim_speed", text="Speed Modifier", slider=True)
                
                if scene.hrg_preset in ['WALK', 'RUN']:
                    col_anim.prop(scene, "hrg_walk_direction", text="Direction")
                    col_anim.prop(scene, "hrg_walk_style", text="Style")
                    
                col_anim.separator()
                
                # Apply Button
                col_anim.operator("object.apply_animation_preset", text="Apply Preset", icon='PLAY')
                
                col_anim.separator()
                col_anim.operator("object.clear_rig_animation", text="Clear All Keyframes", icon='X')
                
                row_act = col_anim.row(align=True)
                row_act.operator("object.delete_active_action", text="Delete Action", icon='TRASH')
                row_act.operator("object.purge_unused_actions", text="Purge Actions", icon='BRUSH_DATA')
                
                # Timing & Smoothing Tools
                col_anim.separator()
                col_anim.operator("object.smooth_fcurves", text="Smooth & Fix Jitter", icon='SMOOTHCURVE')
                
                row_speed = col_anim.row(align=True)
                op_slow = row_speed.operator("object.scale_animation_timing", text="0.5x Slower", icon='REW')
                op_slow.factor = 0.5
                op_fast = row_speed.operator("object.scale_animation_timing", text="2x Faster", icon='FF')
                op_fast.factor = 2.0
                
                col_anim.separator()
                col_anim.operator("object.audio_lip_sync", text="Audio Lip Sync", icon='SOUND')
            
            # Section B: Path Walker Sync
            box_path = layout.box()
            row_path = box_path.row(align=True)
            icon_path = 'TRIA_DOWN' if scene.hrg_show_path_sync else 'TRIA_RIGHT'
            row_path.prop(scene, "hrg_show_path_sync", text="Path Walker Sync", icon=icon_path, emboss=False)
            if scene.hrg_show_path_sync:
                col_path = box_path.column(align=True)
                col_path.prop(scene, "hrg_path_curve_obj", text="Path Curve")
                col_path.prop(scene, "hrg_path_facing", text="Facing Axis")
                col_path.prop(scene, "hrg_path_duration", text="Duration (Frames)")
                col_path.prop(scene, "hrg_path_reverse", text="Start at End Point")
                
                col_path.operator("object.bind_rig_to_path", text="Bind Rig to Path", icon='CON_FOLLOWPATH')
                col_path.operator("object.unbind_rig_from_path", text="Reset Path", icon='X')
            
            # Section C: Interactive Pose Mixer
            box_mixer = layout.box()
            row_mixer = box_mixer.row(align=True)
            icon_mixer = 'TRIA_DOWN' if scene.hrg_show_pose_mixer else 'TRIA_RIGHT'
            row_mixer.prop(scene, "hrg_show_pose_mixer", text="Interactive Pose Mixer", icon=icon_mixer, emboss=False)
            if scene.hrg_show_pose_mixer:
                col_mix = box_mixer.column(align=True)
                col_mix.prop(obj, "hrg_pose_walk_blend", text="Walk Pose", slider=True)
                col_mix.prop(obj, "hrg_pose_run_blend", text="Run Pose", slider=True)
                col_mix.prop(obj, "hrg_pose_talk_blend", text="Talk Pose", slider=True)
                
                # Show face mixer sliders only if the rig has face controls
                has_jaw = obj.pose.bones.get(get_control_name("jaw")) is not None
                has_eyes = obj.pose.bones.get(get_control_name("eyes_look")) is not None
                
                if has_jaw or has_eyes:
                    col_mix.separator()
                    if has_jaw:
                        col_mix.prop(obj, "hrg_jaw_open", text="Open Jaw / Mouth", slider=True)
                    if has_eyes:
                        col_mix.prop(obj, "hrg_eye_blink_l", text="Left Eye Blink", slider=True)
                        col_mix.prop(obj, "hrg_eye_blink_r", text="Right Eye Blink", slider=True)
                    
                    col_mix.prop(obj, "hrg_brow_raise_l", text="Left Brow Raise", slider=True)
                    col_mix.prop(obj, "hrg_brow_raise_r", text="Right Brow Raise", slider=True)
                    col_mix.prop(obj, "hrg_mouth_smile_l", text="Left Mouth Smile", slider=True)
                    col_mix.prop(obj, "hrg_mouth_smile_r", text="Right Mouth Smile", slider=True)
                    
                    if has_eyes:
                        col_mix.separator()
                        col_mix.prop(obj, "hrg_eye_target", text="Eye Target Object")
                        col_mix.prop(obj, "hrg_eye_influence", text="Eye Tracking", slider=True)
                        
                col_mix.separator()
                col_mix.operator("object.reset_pose_mixer", text="Reset Pose Mixer", icon='LOOP_BACK')
            
            # Section D: Acting Poses & Expressions
            box_library = layout.box()
            row_lib = box_library.row(align=True)
            icon_lib = 'TRIA_DOWN' if scene.hrg_show_library else 'TRIA_RIGHT'
            row_lib.prop(scene, "hrg_show_library", text="Acting Poses & Expressions", icon=icon_lib, emboss=False)
            if scene.hrg_show_library:
                col_lib = box_library.column(align=True)
                has_jaw = obj.pose.bones.get(get_control_name("jaw")) is not None
                has_eyes = obj.pose.bones.get(get_control_name("eyes_look")) is not None
                
                # Expressions Grid (only if jaw or eyes are present)
                if has_jaw or has_eyes:
                    box_exp = box_library.box()
                    box_exp.label(text="Facial Expressions", icon='FACE_MAPS')
                    col_exp = box_exp.column(align=True)
                    
                    row1 = col_exp.row(align=True)
                    op_happy = row1.operator("object.apply_face_expression", text="Happy")
                    op_happy.expression = 'HAPPY'
                    op_sad = row1.operator("object.apply_face_expression", text="Sad")
                    op_sad.expression = 'SAD'
                    
                    row2 = col_exp.row(align=True)
                    op_angry = row2.operator("object.apply_face_expression", text="Angry")
                    op_angry.expression = 'ANGRY'
                    op_surprise = row2.operator("object.apply_face_expression", text="Surprise")
                    op_surprise.expression = 'SURPRISED'
                    
                    row3 = col_exp.row(align=True)
                    op_smirk = row3.operator("object.apply_face_expression", text="Smirk")
                    op_smirk.expression = 'SMIRK'
                    op_neutral = row3.operator("object.apply_face_expression", text="Reset Face", icon='LOOP_BACK')
                    op_neutral.expression = 'NEUTRAL'
                
                # Quick Body Posing presets (Collapsible)
                box_body = box_library.box()
                row_body_hdr = box_body.row(align=True)
                icon_body = 'TRIA_DOWN' if scene.hrg_show_body_presets else 'TRIA_RIGHT'
                row_body_hdr.prop(scene, "hrg_show_body_presets", text="Body Poses Presets", icon=icon_body, emboss=False)
                if scene.hrg_show_body_presets:
                    col_body = box_body.column(align=True)
                    col_body.prop(scene, "hrg_active_pose_selector", text="Select Pose")
                    col_body.separator()
                    
                    op_pose = col_body.operator("object.apply_body_pose", text="Apply Preset Pose", icon='POSE_HLT')
                    op_pose.pose = scene.hrg_active_pose_selector
                    col_body.separator()

            # Section E: Live Hand Adjustments
            box_hand = layout.box()
            row_hand = box_hand.row(align=True)
            icon_hand = 'TRIA_DOWN' if scene.hrg_show_hand else 'TRIA_RIGHT'
            row_hand.prop(scene, "hrg_show_hand", text="Live Hand Adjustments", icon=icon_hand, emboss=False)
            if scene.hrg_show_hand:
                col_hand = box_hand.column(align=True)
                col_hand.prop(scene, "hrg_wrist_pitch", text="Wrist Pitch Angle")
                col_hand.separator()
                col_hand.label(text="Walk Pose Base:")
                col_hand.prop(scene, "hrg_walk_hand_x", text="Width (X)")
                col_hand.prop(scene, "hrg_walk_hand_z", text="Height (Z)")
                col_hand.separator()
                col_hand.label(text="Run Pose Base:")
                col_hand.prop(scene, "hrg_run_hand_x", text="Width (X)")
                col_hand.prop(scene, "hrg_run_hand_z", text="Height (Z)")
                col_hand.separator()
                col_hand.label(text="Idle/Talk Pose Base:")
                col_hand.prop(scene, "hrg_hand_x_offset", text="Width (X)")
                col_hand.prop(scene, "hrg_hand_z_offset", text="Height (Z)")

            # Section F: NLA Track Mixer
            box_nla = layout.box()
            row_nla = box_nla.row(align=True)
            icon_nla = 'TRIA_DOWN' if scene.hrg_show_nla else 'TRIA_RIGHT'
            row_nla.prop(scene, "hrg_show_nla", text="NLA Track Mixer", icon=icon_nla, emboss=False)
            if scene.hrg_show_nla:
                col_nla = box_nla.column(align=True)
                col_nla.operator("object.push_to_nla", text="Push Action to NLA Track", icon='NLA_PUSHDOWN')
                
            # Section G: Camera Controller & Film Setup
            box_cam = layout.box()
            row_cam_header = box_cam.row(align=True)
            icon_cam = 'TRIA_DOWN' if scene.hrg_show_camera else 'TRIA_RIGHT'
            row_cam_header.prop(scene, "hrg_show_camera", text="Camera Controller & Film Setup", icon=icon_cam, emboss=False)
            if scene.hrg_show_camera:
                col_cam = box_cam.column(align=True)
                
                # Group 1: Target Actor & Camera
                col_cam.label(text="1. Target & Camera:", icon='CAMERA_DATA')
                col_cam.prop(scene, "hrg_cam_target_actor", text="Target Actor")
                
                row_cam = col_cam.row(align=True)
                row_cam.prop(scene, "hrg_active_camera", text="Active Cam")
                row_cam.operator("object.add_scene_camera", text="Add Cam", icon='ADD')
                
                # Direct Camera Rename Field
                active_cam_obj = bpy.data.objects.get(scene.hrg_active_camera)
                if not active_cam_obj and scene.camera:
                    active_cam_obj = scene.camera
                if active_cam_obj:
                    row_rename = col_cam.row(align=True)
                    row_rename.prop(active_cam_obj, "name", text="Rename Cam", icon='FONT_DATA')
                
                col_cam.prop(scene, "hrg_show_camera_names", text="Show Camera Names in 3D View")
                col_cam.separator()
                
                # Group 2: Framing & Angles
                col_cam.label(text="2. Framing & Angles:", icon='VIEW_CAMERA')
                col_cam.prop(scene, "hrg_cam_shot", text="Shot Size")
                col_cam.prop(scene, "hrg_cam_angle", text="View Angle")
                col_cam.prop(scene, "hrg_cam_orbit", text="Orbit Angle", slider=True)
                col_cam.prop(scene, "hrg_cam_distance_factor", text="Zoom Distance", slider=True)
                col_cam.separator()
                
                # Group 3: Camera Movement / Tracking
                col_cam.label(text="3. Movement / Tracking:", icon='ORIENTATION_GIMBAL')
                col_cam.prop(scene, "hrg_cam_follow", text="Tracking Mode")
                col_cam.separator()
                
                col_cam.operator("object.setup_scene_camera", text="Align & View Camera", icon='CAMERA_DATA')
                col_cam.separator()
                
                # Sub-Section: Timeline Cuts / Sequencer (Collapsible)
                box_cuts = box_cam.box()
                row_cuts_hdr = box_cuts.row(align=True)
                icon_cuts = 'TRIA_DOWN' if scene.hrg_show_cuts else 'TRIA_RIGHT'
                row_cuts_hdr.prop(scene, "hrg_show_cuts", text="Timeline Cuts (Sequencer)", icon=icon_cuts, emboss=False)
                if scene.hrg_show_cuts:
                    col_cuts = box_cuts.column(align=True)
                    col_cuts.operator("object.bind_camera_to_frame", text="Cut to Active Camera at Frame", icon='KEY_HLT')
                    
                    # List timeline cut markers
                    has_cuts = False
                    for marker in sorted(scene.timeline_markers, key=lambda m: m.frame):
                        if marker.camera:
                            has_cuts = True
                            row_cut = col_cuts.row(align=True)
                            row_cut.label(text=f"F-{marker.frame}: {marker.camera.name}", icon='CAMERA_DATA')
                            op_del = row_cut.operator("object.delete_timeline_marker", text="", icon='TRASH')
                            op_del.marker_name = marker.name
                            
                    if not has_cuts:
                        col_cuts.label(text="No timeline camera cuts set.", icon='INFO')
                    
                col_cuts_sep = box_cam.column(align=True)
                col_cuts_sep.separator()
                
                # Sub-Section: Dialogue OTS Camera Rig (Collapsible)
                box_dial = box_cam.box()
                row_dial_hdr = box_dial.row(align=True)
                icon_dial = 'TRIA_DOWN' if scene.hrg_show_dial else 'TRIA_RIGHT'
                row_dial_hdr.prop(scene, "hrg_show_dial", text="Dialogue Over-the-Shoulder Setup", icon=icon_dial, emboss=False)
                if scene.hrg_show_dial:
                    col_dial = box_dial.column(align=True)
                    col_dial.prop(scene, "hrg_dial_actor_a", text="Actor A")
                    col_dial.prop(scene, "hrg_dial_actor_b", text="Actor B")
                    col_dial.separator()
                    
                    op_dial = col_dial.operator("object.setup_dialogue_cameras", text="Generate OTS Dialogue Rigs", icon='CAMERA_DATA')
                    op_dial.actor_a = scene.hrg_dial_actor_a
                    op_dial.actor_b = scene.hrg_dial_actor_b
            
            # Section H: Cinematic Lighting
            box_light = layout.box()
            row_light = box_light.row(align=True)
            icon_light = 'TRIA_DOWN' if scene.hrg_show_lighting else 'TRIA_RIGHT'
            row_light.prop(scene, "hrg_show_lighting", text="Cinematic Lighting & Moods", icon=icon_light, emboss=False)
            if scene.hrg_show_lighting:
                col_light = box_light.column(align=True)
                col_light.prop(scene, "hrg_light_mood", text="Mood Preset")
                col_light.operator("object.setup_auto_lighting", text="Generate Mood Lights Setup", icon='LIGHT')
        
        # 2. Controls Section (visible when the generated rig is selected in Pose Mode)
        if obj and obj.type == 'ARMATURE':
            pose_bones = obj.pose.bones
            
            # Helper to get the active wrist control bone dynamically
            def get_active_wrist_bone(pb_name_side):
                pb_ik = pose_bones.get(get_control_name(f"hand_IK{pb_name_side}"))
                if pb_ik:
                    is_ik = pb_ik.hrg_ik_fk >= 0.5
                    if is_ik:
                        return pb_ik
                    else:
                        return pose_bones.get(get_control_name(f"hand_FK{pb_name_side}"))
                return None

            # Panel 1: Rig Switches (FK/IK) (Collapsible)
            box_switches = layout.box()
            row_sw_hdr = box_switches.row(align=True)
            icon_sw = 'TRIA_DOWN' if scene.hrg_show_switches else 'TRIA_RIGHT'
            row_sw_hdr.prop(scene, "hrg_show_switches", text="Rig Switches & IK/FK", icon=icon_sw, emboss=False)
            if scene.hrg_show_switches:
                col_sw = box_switches.column(align=True)
                pb_larm = pose_bones.get(get_control_name("hand_IK.L"))
                if pb_larm:
                    col_sw.prop(pb_larm, "hrg_ik_fk", text="Left Arm IK/FK", slider=True)
                    
                pb_rarm = pose_bones.get(get_control_name("hand_IK.R"))
                if pb_rarm:
                    col_sw.prop(pb_rarm, "hrg_ik_fk", text="Right Arm IK/FK", slider=True)
                    
                col_sw.separator()
                
                pb_lleg = pose_bones.get(get_control_name("foot_IK.L"))
                if pb_lleg:
                    col_sw.prop(pb_lleg, "hrg_ik_fk", text="Left Leg IK/FK", slider=True)
                    
                pb_rleg = pose_bones.get(get_control_name("foot_IK.R"))
                if pb_rleg:
                    col_sw.prop(pb_rleg, "hrg_ik_fk", text="Right Leg IK/FK", slider=True)
                    
                col_sw.separator()
                col_sw.label(text="0.0 = FK Mode | 1.0 = IK Mode", icon='INFO')

            # Panel 2: Torso & Pelvis Pose (Collapsible)
            pb_pelvis = pose_bones.get(get_control_name("pelvis"))
            if pb_pelvis:
                box_torso = layout.box()
                row_torso_hdr = box_torso.row(align=True)
                icon_torso = 'TRIA_DOWN' if scene.hrg_show_torso else 'TRIA_RIGHT'
                row_torso_hdr.prop(scene, "hrg_show_torso", text="Torso & Pelvis Pose", icon=icon_torso, emboss=False)
                if scene.hrg_show_torso:
                    col = box_torso.column(align=True)
                    col.label(text="Pelvis Location:")
                    row = col.row(align=True)
                    row.prop(pb_pelvis, "location", index=0, text="Left/Right (X)")
                    row.prop(pb_pelvis, "location", index=1, text="Front/Back (Y)")
                    col.prop(pb_pelvis, "location", index=2, text="Height (Z)")
                    
                    col_rot = box_torso.column(align=True)
                    col_rot.label(text="Pelvis Rotation:")
                    row = col_rot.row(align=True)
                    row.prop(pb_pelvis, "rotation_euler", index=0, text="Pitch (X)")
                    row.prop(pb_pelvis, "rotation_euler", index=2, text="Roll (Z)")
                    col_rot.prop(pb_pelvis, "rotation_euler", index=1, text="Yaw (Y)")
                    
                    pb_spine = pose_bones.get(get_control_name("spine"))
                    pb_chest = pose_bones.get(get_control_name("spine.003"))
                    if pb_spine or pb_chest:
                        box_torso.separator()
                        if pb_spine:
                            col_spine = box_torso.column(align=True)
                            col_spine.label(text="Spine Rotation:")
                            row = col_spine.row(align=True)
                            row.prop(pb_spine, "rotation_euler", index=0, text="Pitch")
                            row.prop(pb_spine, "rotation_euler", index=2, text="Roll")
                            col_spine.prop(pb_spine, "rotation_euler", index=1, text="Yaw")
                        if pb_chest:
                            col_chest = box_torso.column(align=True)
                            col_chest.label(text="Chest Rotation:")
                            row = col_chest.row(align=True)
                            row.prop(pb_chest, "rotation_euler", index=0, text="Pitch")
                            row.prop(pb_chest, "rotation_euler", index=2, text="Roll")
                            col_chest.prop(pb_chest, "rotation_euler", index=1, text="Yaw")

            # Panel 3: Head, Neck & Jaw Pose (Collapsible)
            pb_head = pose_bones.get(get_control_name("head"))
            pb_neck = pose_bones.get(get_control_name("neck"))
            pb_lsh = pose_bones.get(get_control_name("shoulder.L"))
            pb_rsh = pose_bones.get(get_control_name("shoulder.R"))
            pb_jaw = pose_bones.get(get_control_name("jaw"))
            
            if pb_head or pb_neck or pb_lsh or pb_rsh or pb_jaw:
                box_head = layout.box()
                row_head_hdr = box_head.row(align=True)
                icon_head = 'TRIA_DOWN' if scene.hrg_show_head_neck else 'TRIA_RIGHT'
                row_head_hdr.prop(scene, "hrg_show_head_neck", text="Head, Neck & Jaw Pose", icon=icon_head, emboss=False)
                if scene.hrg_show_head_neck:
                    if pb_head:
                        col_head = box_head.column(align=True)
                        col_head.label(text="Head Rotation:")
                        row = col_head.row(align=True)
                        row.prop(pb_head, "rotation_euler", index=0, text="Pitch")
                        row.prop(pb_head, "rotation_euler", index=2, text="Roll")
                        col_head.prop(pb_head, "rotation_euler", index=1, text="Yaw")
                        
                    if pb_neck:
                        col_neck = box_head.column(align=True)
                        col_neck.label(text="Neck Rotation:")
                        row = col_neck.row(align=True)
                        row.prop(pb_neck, "rotation_euler", index=0, text="Pitch")
                        row.prop(pb_neck, "rotation_euler", index=2, text="Roll")
                        col_neck.prop(pb_neck, "rotation_euler", index=1, text="Yaw")
                        
                    if pb_lsh or pb_rsh:
                        box_head.separator()
                        box_head.label(text="Shoulders Pitch (Shrug)")
                        row = box_head.row(align=True)
                        if pb_lsh:
                            row.prop(pb_lsh, "rotation_euler", index=0, text="Left")
                        if pb_rsh:
                            row.prop(pb_rsh, "rotation_euler", index=0, text="Right")
                            
                    if pb_jaw:
                        box_head.separator()
                        col_jaw = box_head.column(align=True)
                        col_jaw.label(text="Jaw Rotation:")
                        row = col_jaw.row(align=True)
                        row.prop(pb_jaw, "rotation_euler", index=0, text="Open/Close")
                        row.prop(pb_jaw, "rotation_euler", index=2, text="Side-to-Side")

            # Panel 4: Eyelid Controllers (Collapsible)
            pb_eyes = pose_bones.get(get_control_name("eyes_look"))
            if pb_eyes and ("eye_close.L" in pb_eyes or "eye_close.R" in pb_eyes):
                box_face = layout.box()
                row_face_hdr = box_face.row(align=True)
                icon_face = 'TRIA_DOWN' if scene.hrg_show_eyelids else 'TRIA_RIGHT'
                row_face_hdr.prop(scene, "hrg_show_eyelids", text="Eyelid Controllers", icon=icon_face, emboss=False)
                if scene.hrg_show_eyelids:
                    if "eye_close.L" in pb_eyes:
                        box_face.prop(pb_eyes, '["eye_close.L"]', text="Close Left Eye", slider=True)
                    if "eye_close.R" in pb_eyes:
                        box_face.prop(pb_eyes, '["eye_close.R"]', text="Close Right Eye", slider=True)

            # Panel 5: Wrist Pose Controllers (Collapsible)
            has_wrist_controls = False
            box_wrist = None
            for side in [".L", ".R"]:
                pb_wrist = get_active_wrist_bone(side)
                if pb_wrist:
                    if not has_wrist_controls:
                        box_wrist = layout.box()
                        row_wrist_hdr = box_wrist.row(align=True)
                        icon_wrist = 'TRIA_DOWN' if scene.hrg_show_wrist_ctrl else 'TRIA_RIGHT'
                        row_wrist_hdr.prop(scene, "hrg_show_wrist_ctrl", text="Wrist Pose Controllers", icon=icon_wrist, emboss=False)
                        has_wrist_controls = True
                    if scene.hrg_show_wrist_ctrl and box_wrist:
                        col_wrist = box_wrist.column(align=True)
                        col_wrist.label(text=f"{'Left' if side == '.L' else 'Right'} Hand Wrist:")
                        row = col_wrist.row(align=True)
                        row.prop(pb_wrist, "rotation_euler", index=0, text="Bend (Pitch)")
                        row.prop(pb_wrist, "rotation_euler", index=2, text="Roll")
                        col_wrist.prop(pb_wrist, "rotation_euler", index=1, text="Twist (Yaw)")

            # Panel 6: Finger Pose Controllers (Collapsible)
            pb_lfingers = pose_bones.get(get_control_name("fingers.L"))
            pb_rfingers = pose_bones.get(get_control_name("fingers.R"))
            if pb_lfingers or pb_rfingers:
                box_fingers = layout.box()
                row_fingers_hdr = box_fingers.row(align=True)
                icon_fingers = 'TRIA_DOWN' if scene.hrg_show_finger_ctrl else 'TRIA_RIGHT'
                row_fingers_hdr.prop(scene, "hrg_show_finger_ctrl", text="Finger Pose Controllers", icon=icon_fingers, emboss=False)
                if scene.hrg_show_finger_ctrl:
                    if pb_lfingers:
                        col_l = box_fingers.column(align=True)
                        col_l.label(text="Left Hand:")
                        col_l.prop(pb_lfingers, "hrg_grasp", text="Master Grasp", slider=True)
                        row = col_l.row(align=True)
                        row.prop(pb_lfingers, "hrg_thumb", text="Thumb", slider=True)
                        row.prop(pb_lfingers, "hrg_index", text="Index", slider=True)
                        row = col_l.row(align=True)
                        row.prop(pb_lfingers, "hrg_middle", text="Middle", slider=True)
                        row.prop(pb_lfingers, "hrg_ring", text="Ring", slider=True)
                        row.prop(pb_lfingers, "hrg_pinky", text="Pinky", slider=True)
                        
                    if pb_rfingers:
                        if pb_lfingers:
                            box_fingers.separator()
                        col_r = box_fingers.column(align=True)
                        col_r.label(text="Right Hand:")
                        col_r.prop(pb_rfingers, "hrg_grasp", text="Master Grasp", slider=True)
                        row = col_r.row(align=True)
                        row.prop(pb_rfingers, "hrg_thumb", text="Thumb", slider=True)
                        row.prop(pb_rfingers, "hrg_index", text="Index", slider=True)
                        row = col_r.row(align=True)
                        row.prop(pb_rfingers, "hrg_middle", text="Middle", slider=True)
                        row.prop(pb_rfingers, "hrg_ring", text="Ring", slider=True)
                        row.prop(pb_rfingers, "hrg_pinky", text="Pinky", slider=True)
