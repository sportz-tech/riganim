# registration.py
import bpy
from .operators.create_rig import OBJECT_OT_generate_human_rig
from .operators.markers import (
    OBJECT_OT_spawn_markers, OBJECT_OT_mirror_markers, 
    OBJECT_OT_interactive_marker_place, on_depsgraph_update,
    register_skeleton_draw, unregister_skeleton_draw
)
from .operators.animation import (
    OBJECT_OT_apply_animation_preset, OBJECT_OT_clear_rig_animation, 
    OBJECT_OT_push_to_nla, OBJECT_OT_bind_rig_to_path, OBJECT_OT_unbind_rig_from_path,
    OBJECT_OT_setup_scene_camera, OBJECT_OT_add_scene_camera, OBJECT_OT_audio_lip_sync,
    OBJECT_OT_reset_pose_mixer, update_pose_mixer, update_eye_target,
    OBJECT_OT_bind_camera_to_frame, OBJECT_OT_delete_timeline_marker,
    OBJECT_OT_setup_dialogue_cameras, OBJECT_OT_setup_auto_lighting,
    OBJECT_OT_apply_face_expression, OBJECT_OT_apply_body_pose,
    OBJECT_OT_delete_active_action, OBJECT_OT_delete_selected_action, OBJECT_OT_purge_unused_actions,
    OBJECT_OT_smooth_fcurves, OBJECT_OT_scale_animation_timing,
    OBJECT_OT_clone_character_actor, OBJECT_OT_reset_rig_to_origin,
    OBJECT_OT_delete_character_actor, OBJECT_OT_purge_unused_collections,
    OBJECT_OT_apply_saved_action, OBJECT_OT_copy_animation_from_actor,
    OBJECT_OT_save_custom_action, OBJECT_OT_import_actions_from_blend, get_scene_actions_items,
    OBJECT_OT_pick_anim_source_rig, OBJECT_OT_pick_anim_target_rig,
    OBJECT_OT_transfer_actor_animation, get_transfer_action_items,
    OBJECT_OT_fix_clone_constraints
)
from .operators.spawn_points import (
    OBJECT_OT_interactive_spawn_point_place,
    OBJECT_OT_add_spawn_point_at_cursor,
    OBJECT_OT_clone_to_spawn_points,
    OBJECT_OT_keyframe_move_to_point,
    OBJECT_OT_clear_spawn_points
)
from .operators.props import (
    OBJECT_OT_attach_prop,
    OBJECT_OT_keyframe_prop_pickup,
    OBJECT_OT_keyframe_prop_drop,
    OBJECT_OT_detach_prop,
    OBJECT_OT_pick_prop_from_selection,
    get_prop_items
)
from .operators.auto_skin import (
    OBJECT_OT_auto_skin_mesh,
    OBJECT_OT_fix_clothing_clipping,
    OBJECT_OT_mask_body_under_clothes
)
from .operators.asset_spawner import (
    OBJECT_OT_interactive_asset_spawner,
    OBJECT_OT_scatter_selected_mesh,
    OBJECT_OT_spawn_mesh_at_cursor,
    OBJECT_OT_clear_spawned_assets,
    OBJECT_OT_import_assets_from_blend
)
from .ui.panel import VIEW3D_PT_human_rig_generator

def get_action_fcurves(action):
    """Returns a list of F-curves from an action, compatible with both legacy and Blender 5.0+ slotted actions."""
    if not action:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    fcurves = []
    if hasattr(action, "layers"):
        for layer in action.layers:
            if hasattr(layer, "strips"):
                for strip in layer.strips:
                    if hasattr(strip, "channelbags"):
                        for cb in strip.channelbags:
                            if hasattr(cb, "fcurves"):
                                fcurves.extend(list(cb.fcurves))
    return fcurves

def remove_action_fcurve(action, fc):
    """Removes an F-curve from an action, compatible with both legacy and Blender 5.0+ slotted actions."""
    if not action or not fc:
        return
    if hasattr(action, "fcurves"):
        try:
            action.fcurves.remove(fc)
            return
        except Exception:
            pass
    if hasattr(action, "layers"):
        for layer in action.layers:
            if hasattr(layer, "strips"):
                for strip in layer.strips:
                    if hasattr(strip, "channelbags"):
                        for cb in strip.channelbags:
                            if hasattr(cb, "fcurves"):
                                if fc in list(cb.fcurves):
                                    try:
                                        cb.fcurves.remove(fc)
                                        return
                                    except Exception:
                                        pass

def update_active_actor(self, context):
    if self.hrg_active_actor != 'NONE':
        obj = bpy.data.objects.get(self.hrg_active_actor)
        if obj:
            # Set active
            context.view_layer.objects.active = obj
            # Select
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

def get_actors_items(self, context):
    items = [('NONE', "None (Select Actor)", "No actor selected")]
    for obj in context.scene.objects:
        if obj.type == 'ARMATURE':
            items.append((obj.name, obj.name, f"Select {obj.name} as active actor"))
    return items

def get_cameras_items(self, context):
    items = [('NONE', "None (Select Camera)", "No camera selected")]
    for obj in context.scene.objects:
        if obj.type == 'CAMERA':
            items.append((obj.name, obj.name, f"Select {obj.name} as active camera"))
    return items

_is_updating_cam = False

def update_active_camera(self, context):
    global _is_updating_cam
    if _is_updating_cam:
        return
    if self.hrg_active_camera != 'NONE':
        cam_obj = bpy.data.objects.get(self.hrg_active_camera)
        if cam_obj:
            context.scene.camera = cam_obj
            update_camera_alignment(self, context)

def update_camera_alignment(self, context):
    global _is_updating_cam
    if _is_updating_cam:
        return
    _is_updating_cam = True
    try:
        if hasattr(bpy.ops.object, "setup_scene_camera"):
            bpy.ops.object.setup_scene_camera(switch_view=False)
    except Exception:
        pass
    finally:
        _is_updating_cam = False

def update_path_curve_target(self, context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        curve_obj = context.scene.hrg_path_curve_obj
        from .utils.naming import get_control_name
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if pb_root:
            for c in pb_root.constraints:
                if c.type == 'FOLLOW_PATH':
                    c.target = curve_obj

def update_path_facing_axis(self, context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        from .utils.naming import get_control_name
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if pb_root:
            for c in pb_root.constraints:
                if c.type == 'FOLLOW_PATH':
                    c.forward_axis = context.scene.hrg_path_facing
                    
def update_path_reverse(self, context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        from .utils.naming import get_control_name
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if pb_root:
            c = pb_root.constraints.get("Follow_Path")
            if c and c.target:
                start_frame = context.scene.frame_start
                end_frame = context.scene.frame_end
                
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action
                    dp = f'pose.bones["{pb_root.name}"].constraints["Follow_Path"].offset_factor'
                    
                    for fc in get_action_fcurves(action):
                        if fc.data_path == dp:
                            remove_action_fcurve(action, fc)
                                
                    start_val = 1.0 if context.scene.hrg_path_reverse else 0.0
                    end_val = 0.0 if context.scene.hrg_path_reverse else 1.0
                    
                    c.offset_factor = start_val
                    obj.keyframe_insert(data_path=dp, frame=start_frame)
                    
                    c.offset_factor = end_val
                    obj.keyframe_insert(data_path=dp, frame=end_frame)
                    
                    for fc in get_action_fcurves(action):
                        if fc.data_path == dp:
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'LINEAR'
                                
                    c.offset_factor = start_val
                    context.scene.frame_current = start_frame
                    context.view_layer.update()

def update_preset_preview(self, context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        try:
            bpy.ops.object.apply_animation_preset()
        except Exception:
            pass

def update_marker_size(self, context):
    for obj in context.scene.objects:
        if "Mkr_" in obj.name and obj.type == 'EMPTY':
            obj.empty_display_size = self.hrg_marker_size

def update_controller_scale(self, context):
    from .operators.controllers import update_armature_controller_scales
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        update_armature_controller_scales(obj, self.hrg_controller_scale)
    for o in context.selected_objects:
        if o.type == 'ARMATURE' and o != obj:
            update_armature_controller_scales(o, self.hrg_controller_scale)
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def update_marker_names(self, context):
    for obj in context.scene.objects:
        if "Mkr_" in obj.name:
            obj.show_name = self.hrg_show_marker_names

def update_marker_lines(self, context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def update_camera_names(self, context):
    for obj in context.scene.objects:
        if obj.type == 'CAMERA':
            obj.show_name = self.hrg_show_camera_names
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

classes = (
    OBJECT_OT_spawn_markers,
    OBJECT_OT_interactive_marker_place,
    OBJECT_OT_mirror_markers,
    OBJECT_OT_generate_human_rig,
    OBJECT_OT_apply_animation_preset,
    OBJECT_OT_clear_rig_animation,
    OBJECT_OT_push_to_nla,
    OBJECT_OT_bind_rig_to_path,
    OBJECT_OT_unbind_rig_from_path,
    OBJECT_OT_setup_scene_camera,
    OBJECT_OT_add_scene_camera,
    OBJECT_OT_audio_lip_sync,
    OBJECT_OT_reset_pose_mixer,
    OBJECT_OT_auto_skin_mesh,
    OBJECT_OT_fix_clothing_clipping,
    OBJECT_OT_mask_body_under_clothes,
    OBJECT_OT_bind_camera_to_frame,
    OBJECT_OT_delete_timeline_marker,
    OBJECT_OT_setup_dialogue_cameras,
    OBJECT_OT_setup_auto_lighting,
    OBJECT_OT_apply_face_expression,
    OBJECT_OT_apply_body_pose,
    OBJECT_OT_delete_active_action,
    OBJECT_OT_delete_selected_action,
    OBJECT_OT_purge_unused_actions,
    OBJECT_OT_smooth_fcurves,
    OBJECT_OT_scale_animation_timing,
    OBJECT_OT_clone_character_actor,
    OBJECT_OT_reset_rig_to_origin,
    OBJECT_OT_delete_character_actor,
    OBJECT_OT_purge_unused_collections,
    OBJECT_OT_apply_saved_action,
    OBJECT_OT_copy_animation_from_actor,
    OBJECT_OT_save_custom_action,
    OBJECT_OT_import_actions_from_blend,
    OBJECT_OT_pick_anim_source_rig,
    OBJECT_OT_pick_anim_target_rig,
    OBJECT_OT_transfer_actor_animation,
    OBJECT_OT_fix_clone_constraints,
    OBJECT_OT_interactive_spawn_point_place,
    OBJECT_OT_add_spawn_point_at_cursor,
    OBJECT_OT_clone_to_spawn_points,
    OBJECT_OT_keyframe_move_to_point,
    OBJECT_OT_clear_spawn_points,
    OBJECT_OT_attach_prop,
    OBJECT_OT_keyframe_prop_pickup,
    OBJECT_OT_keyframe_prop_drop,
    OBJECT_OT_detach_prop,
    OBJECT_OT_pick_prop_from_selection,
    OBJECT_OT_interactive_asset_spawner,
    OBJECT_OT_scatter_selected_mesh,
    OBJECT_OT_spawn_mesh_at_cursor,
    OBJECT_OT_clear_spawned_assets,
    OBJECT_OT_import_assets_from_blend,
    VIEW3D_PT_human_rig_generator,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
            
    # Register depsgraph update post handler for real-time visual skeleton updates
    if on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)
        
    # Register persistent 3D Viewport skeleton draw callback
    register_skeleton_draw()
        
    # Collapsible UI section state toggles
    bpy.types.Scene.hrg_show_actor = bpy.props.BoolProperty(name="Show Actor Manager", default=True)
    bpy.types.Scene.hrg_clone_count = bpy.props.IntProperty(name="Clone Count", default=2, min=1, max=20)
    bpy.types.Scene.hrg_show_asset_spawner = bpy.props.BoolProperty(name="Show Asset & Mesh Spawner", default=True)
    bpy.types.Scene.hrg_show_markers = bpy.props.BoolProperty(name="Show Marker Alignment", default=False)
    bpy.types.Scene.hrg_show_generator = bpy.props.BoolProperty(name="Show Generator Options", default=True)
    bpy.types.Scene.hrg_show_sequencer = bpy.props.BoolProperty(name="Show Animation Sequencer", default=True)
    bpy.types.Scene.hrg_show_nla = bpy.props.BoolProperty(name="Show NLA Track Mixer", default=False)
    bpy.types.Scene.hrg_show_hand = bpy.props.BoolProperty(name="Show Live Hand Adjustments", default=False)
    bpy.types.Scene.hrg_show_path_sync = bpy.props.BoolProperty(name="Show Path Walker Sync", default=True)
    bpy.types.Scene.hrg_show_camera = bpy.props.BoolProperty(name="Show Camera Controller", default=False)
    bpy.types.Scene.hrg_show_lighting = bpy.props.BoolProperty(name="Show Cinematic Lighting", default=False)
    bpy.types.Scene.hrg_show_pose_mixer = bpy.props.BoolProperty(name="Show Interactive Pose Mixer", default=False)
    bpy.types.Scene.hrg_show_library = bpy.props.BoolProperty(name="Show Acting Poses & Expressions", default=False)
    bpy.types.Scene.hrg_show_cuts = bpy.props.BoolProperty(name="Show Timeline Cuts", default=False)
    bpy.types.Scene.hrg_show_dial = bpy.props.BoolProperty(name="Show Dialogue OTS Setup", default=False)
    bpy.types.Scene.hrg_show_body_presets = bpy.props.BoolProperty(name="Show Body Pose Presets", default=False)
    bpy.types.Scene.hrg_show_switches = bpy.props.BoolProperty(name="Show Rig Switches", default=False)
    bpy.types.Scene.hrg_show_torso = bpy.props.BoolProperty(name="Show Torso & Pelvis Pose", default=False)
    bpy.types.Scene.hrg_show_head_neck = bpy.props.BoolProperty(name="Show Head, Neck & Jaw Pose", default=False)
    bpy.types.Scene.hrg_show_eyelids = bpy.props.BoolProperty(name="Show Eyelid Controllers", default=False)
    bpy.types.Scene.hrg_show_wrist_ctrl = bpy.props.BoolProperty(name="Show Wrist Pose Controllers", default=False)
    bpy.types.Scene.hrg_show_finger_ctrl = bpy.props.BoolProperty(name="Show Finger Pose Controllers", default=False)

    # Register custom scene properties
    bpy.types.Scene.hrg_marker_size = bpy.props.FloatProperty(
        name="Marker Display Size",
        description="Display size of the spawned alignment markers",
        default=0.05,
        min=0.001,
        max=0.5,
        update=update_marker_size
    )
    bpy.types.Scene.hrg_show_marker_names = bpy.props.BoolProperty(
        name="Show Marker Names",
        description="Show/Hide the names of alignment markers in the viewport",
        default=True,
        update=update_marker_names
    )
    bpy.types.Scene.hrg_show_marker_lines = bpy.props.BoolProperty(
        name="Show Marker Lines",
        description="Show wire skeleton guide connecting the markers in real-time",
        default=True,
        update=update_marker_lines
    )
    bpy.types.Scene.hrg_controller_scale = bpy.props.FloatProperty(
        name="Controller Scale",
        description="Display scale of all bone controllers in the viewport",
        default=1.0,
        min=0.1,
        max=5.0,
        update=update_controller_scale
    )
    bpy.types.Scene.hrg_use_bbone_legs = bpy.props.BoolProperty(
        name="Bendy Legs",
        description="Enable Bendy Bones for legs (thighs and shins)",
        default=False
    )
    bpy.types.Scene.hrg_bbone_segments_legs = bpy.props.IntProperty(
        name="Leg Segments",
        description="Number of Bendy Bone segments for leg bones",
        default=5,
        min=2,
        max=16
    )
    bpy.types.Scene.hrg_use_bbone_arms = bpy.props.BoolProperty(
        name="Bendy Arms",
        description="Enable Bendy Bones for arms/wings (upper arms and forearms)",
        default=False
    )
    bpy.types.Scene.hrg_bbone_segments_arms = bpy.props.IntProperty(
        name="Arm Segments",
        description="Number of Bendy Bone segments for arm bones",
        default=5,
        min=2,
        max=16
    )
    bpy.types.Scene.hrg_use_bbone_spine = bpy.props.BoolProperty(
        name="Bendy Spine",
        description="Enable Bendy Bones for spine",
        default=False
    )
    bpy.types.Scene.hrg_bbone_segments_spine = bpy.props.IntProperty(
        name="Spine Segments",
        description="Number of Bendy Bone segments for spine bones",
        default=5,
        min=2,
        max=16
    )
    bpy.types.Scene.hrg_rig_type = bpy.props.EnumProperty(
        name="Rig Type",
        items=[
            ('HUMAN', "Human (Biped)", "Realistic bipedal human rig"),
            ('ANIMAL', "Animal (Quadruped)", "Realistic 4-legged animal rig"),
            ('BIRD', "Bird (Avian)", "Realistic wing and leg bird rig")
        ],
        default='HUMAN'
    )
    bpy.types.Scene.hrg_active_actor = bpy.props.EnumProperty(
        name="Active Actor",
        items=get_actors_items,
        update=update_active_actor
    )
    bpy.types.Scene.hrg_preset = bpy.props.EnumProperty(
        name="Preset",
        items=[
            ('WALK', "Walk Loop", "Seamless walking loop"),
            ('RUN', "Run Loop", "Fast running loop"),
            ('IDLE', "Idle Breathing", "Subtle breathing standing loop"),
            ('WAVE', "Hand Wave", "Hand waving preset"),
            ('JUMP', "Jump Cycle", "Crouch and jump loop"),
            ('TALK', "Talking", "Speech/Jaw movement preset"),
            ('SITTING', "Sitting Down", "Character sitting down on a chair"),
            ('DOOR_OPEN', "Door Opening", "Character opening a door"),
            ('POINT', "Pointing", "Character pointing with hand"),
            ('PUSH', "Pushing Object", "Character pushing an object"),
            ('SIT_SAD', "Sit Sad", "Character sitting down looking sad"),
            ('CRYING', "Crying", "Character crying with hands on face"),
            ('LAUGHING', "Laughing", "Character laughing with body bouncing"),
            ('PUNCH', "Fight: Punch", "Character throwing a forward punch"),
            ('KICK', "Fight: Front Kick", "Character throwing a forward kick"),
            ('BLOCK', "Fight: Guard Block", "Character blocking head and face"),
            ('DODGE', "Fight: Dodge", "Character dodging to the side"),
            ('SPIN_KICK_FALL', "Fight: Spin Kick & Fall", "Jump, spinning head kick, and fall to ground"),
            ('PROP_JUMP_CROSS', "Prop Jump & Cross", "Holding prop crouch, explosive vault jump across obstacle and solid land")
        ],
        default='WALK'
    )
    bpy.types.Scene.hrg_scene_action = bpy.props.EnumProperty(
        name="Saved Action",
        description="Select any saved Action from the blend file to apply to the active character",
        items=get_scene_actions_items
    )
    bpy.types.Scene.hrg_anim_source_rig = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Source Rig",
        description="Pick the source character rig using dropdown or eyedropper pen"
    )
    bpy.types.Scene.hrg_anim_target_rig = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Target Rig",
        description="Pick the target character rig / clone using dropdown or eyedropper pen"
    )
    bpy.types.Scene.hrg_anim_transfer_action = bpy.props.EnumProperty(
        name="Action to Transfer",
        description="Select which action to transfer from source character to target character",
        items=get_transfer_action_items
    )
    bpy.types.Scene.hrg_anim_make_copy = bpy.props.BoolProperty(
        name="Create New Action Copy",
        description="If checked, creates a new unique action copy. If unchecked, directly shares the exact same action data",
        default=False
    )
    bpy.types.Scene.hrg_source_actor_to_copy = bpy.props.EnumProperty(
        name="Source Actor",
        description="Select source character to copy animation from",
        items=get_actors_items
    )
    bpy.types.Scene.hrg_start_frame = bpy.props.IntProperty(
        name="Start Frame",
        default=1,
        min=1
    )
    bpy.types.Scene.hrg_set_timeline_range = bpy.props.BoolProperty(
        name="Auto-Fit Timeline Range",
        description="Automatically adjust Blender's Start and End playback frames to match this preset",
        default=True
    )
    bpy.types.Scene.hrg_walk_direction = bpy.props.EnumProperty(
        name="Walk Direction",
        items=[
            ('FORWARD', "Forward", "Walk forward (along -Y)"),
            ('BACKWARD', "Backward", "Walk backward (along +Y)")
        ],
        default='FORWARD'
    )
    bpy.types.Scene.hrg_walk_style = bpy.props.EnumProperty(
        name="Walk Style",
        items=[
            ('IN_PLACE', "In Place (Treadmill)", "Walk in place"),
            ('TRAVELING', "Traveling (In Scene)", "Translate forward/backward in the scene")
        ],
        default='IN_PLACE'
    )
    bpy.types.Scene.hrg_path_curve_obj = bpy.props.PointerProperty(
        name="Path Curve / Mesh",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type in ['CURVE', 'MESH'],
        update=update_path_curve_target
    )
    bpy.types.Scene.hrg_path_facing = bpy.props.EnumProperty(
        name="Facing Axis",
        items=[
            ('FORWARD_X', "Positive X (X+)", "Face along positive X axis"),
            ('TRACK_NEGATIVE_X', "Negative X (X-)", "Face along negative X axis"),
            ('FORWARD_Y', "Positive Y (Y+)", "Face along positive Y axis"),
            ('TRACK_NEGATIVE_Y', "Negative Y (Y-)", "Face along negative Y axis"),
            ('FORWARD_Z', "Positive Z (Z+)", "Face along positive Z axis"),
            ('TRACK_NEGATIVE_Z', "Negative Z (Z-)", "Face along negative Z axis")
        ],
        default='TRACK_NEGATIVE_Y',
        update=update_path_facing_axis
    )
    bpy.types.Scene.hrg_path_reverse = bpy.props.BoolProperty(
        name="Start at End Point",
        description="Start the walking traversal at the end of the path and walk towards the start",
        default=False,
        update=update_path_reverse
    )
    bpy.types.Scene.hrg_anim_speed = bpy.props.FloatProperty(
        name="Speed Modifier",
        description="Speed multiplier for animation loop playback (e.g., 2.0 is double speed, 0.5 is half speed)",
        default=1.0,
        min=0.1,
        max=5.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_preset_duration = bpy.props.IntProperty(
        name="Preset Duration",
        description="Duration of the generated animation loop segment in frames (useful for multi-segment path walk layouts)",
        default=24,
        min=4
    )
    bpy.types.Scene.hrg_hand_x_offset = bpy.props.FloatProperty(
        name="Hand X Offset (Idle/Talk)",
        default=0.22,
        min=0.0,
        max=1.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_hand_z_offset = bpy.props.FloatProperty(
        name="Hand Z Offset (Idle/Talk)",
        default=-0.85,
        min=-2.0,
        max=0.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_walk_hand_x = bpy.props.FloatProperty(
        name="Walk Hand X (Thigh Distance)",
        default=0.10,
        min=0.0,
        max=1.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_walk_hand_z = bpy.props.FloatProperty(
        name="Walk Hand Z (Height)",
        default=-0.96,
        min=-2.0,
        max=0.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_run_hand_x = bpy.props.FloatProperty(
        name="Run Hand X",
        default=0.18,
        min=0.0,
        max=1.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_run_hand_z = bpy.props.FloatProperty(
        name="Run Hand Z",
        default=-0.45,
        min=-2.0,
        max=0.0,
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_wrist_pitch = bpy.props.FloatProperty(
        name="Wrist Pitch (Rest)",
        default=0.0,
        min=-180.0,
        max=180.0,
        subtype='ANGLE',
        update=update_preset_preview
    )
    bpy.types.Scene.hrg_path_duration = bpy.props.IntProperty(
        name="Duration",
        default=120,
        min=1
    )
    bpy.types.Scene.hrg_cam_shot = bpy.props.EnumProperty(
        name="Shot Type",
        items=[
            ('CLOSEUP', "Close-up (Face)", "Focus on the head"),
            ('MEDIUM', "Medium (Waist)", "Focus on the chest/torso"),
            ('WIDE', "Wide (Full Body)", "Focus on the full body")
        ],
        default='MEDIUM',
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_cam_angle = bpy.props.EnumProperty(
        name="Angle",
        items=[
            ('FRONT', "Front", "Camera directly in front of the character"),
            ('BACK', "Back", "Camera directly behind the character"),
            ('THREE_QUARTER', "Three-Quarter", "45 degree three-quarter angle"),
            ('BACK_THREE_QUARTER', "Back Three-Quarter", "Camera behind at 45 degree angle"),
            ('SIDE', "Side Profile", "90 degree profile shot"),
            ('HIGH', "High Angle", "Looking down from front-high"),
            ('LOW', "Low Angle", "Looking up from front-low")
        ],
        default='THREE_QUARTER',
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_cam_orbit = bpy.props.FloatProperty(
        name="Camera Orbit (Z)",
        description="Orbit camera around character in degrees",
        default=0.0,
        min=-180.0,
        max=180.0,
        subtype='ANGLE',
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_cam_distance_factor = bpy.props.FloatProperty(
        name="Distance Factor",
        description="Multiply default camera distance (zoom in/out)",
        default=1.0,
        min=0.1,
        max=5.0,
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_cam_follow = bpy.props.EnumProperty(
        name="Camera Tracking",
        description="Select how the camera behaves relative to the character",
        items=[
            ('STATIC', "Static (Fixed Camera)", "Camera stays completely stationary and does not track nor move with the character"),
            ('TRACK', "Track Gaze (Static Location)", "Camera stays stationary but rotates to look at/track the character"),
            ('MOVE', "Move with Model (Traveling)", "Camera is parented to the character bone and moves along with it")
        ],
        default='TRACK',
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_cam_target_actor = bpy.props.EnumProperty(
        name="Target Actor",
        description="The character character the camera tracks",
        items=get_actors_items,
        update=update_camera_alignment
    )
    bpy.types.Scene.hrg_active_camera = bpy.props.EnumProperty(
        name="Active Camera",
        description="The active camera used in the scene",
        items=get_cameras_items,
        update=update_active_camera
    )
    bpy.types.Scene.hrg_show_camera_names = bpy.props.BoolProperty(
        name="Show Camera Names",
        description="Show or hide camera names above the camera pyramids in the 3D viewport",
        default=True,
        update=update_camera_names
    )
    
    # Spawn Points & Keyframe Travel
    bpy.types.Scene.hrg_show_spawn = bpy.props.BoolProperty(
        name="Show Spawn Points",
        default=True
    )
    bpy.types.Scene.hrg_travel_duration = bpy.props.IntProperty(
        name="Travel Duration",
        description="Number of frames for the character to travel from current spot to target spot",
        default=10,
        min=1,
        max=500
    )
    bpy.types.Scene.hrg_travel_mode = bpy.props.EnumProperty(
        name="Travel Mode",
        items=[
            ('ANIMATE', "Keyframe Travel (Smooth Move)", "Keyframes character moving from current frame to target frame"),
            ('SNAP', "Instant Teleport", "Instantly teleports character to target location")
        ],
        default='ANIMATE'
    )
    
    # Asset & Mesh Spawner Properties
    bpy.types.Scene.hrg_spawn_source_obj = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Target Mesh / Object",
        description="Select a specific object to spawn (or leave blank to use currently selected viewport object)"
    )
    bpy.types.Scene.hrg_mesh_spawn_count = bpy.props.IntProperty(
        name="Spawn Count",
        description="Number of objects/meshes to spawn (e.g. 1, 2, 3, etc.)",
        default=3,
        min=1,
        max=500
    )
    bpy.types.Scene.hrg_mesh_spawn_radius = bpy.props.FloatProperty(
        name="Scatter Radius",
        description="Radius around click or 3D cursor to scatter multiple objects (in meters)",
        default=5.0,
        min=0.1,
        max=100.0
    )
    bpy.types.Scene.hrg_mesh_random_rot = bpy.props.BoolProperty(
        name="Random Z Rotation",
        description="Randomly rotate objects on the Z-axis (0-360°) so they look natural",
        default=True
    )
    bpy.types.Scene.hrg_mesh_random_scale = bpy.props.BoolProperty(
        name="Random Scale",
        description="Apply random scale variation between Min and Max",
        default=True
    )
    bpy.types.Scene.hrg_mesh_scale_min = bpy.props.FloatProperty(
        name="Scale Min",
        description="Minimum scale factor",
        default=0.8,
        min=0.01,
        max=10.0
    )
    bpy.types.Scene.hrg_mesh_scale_max = bpy.props.FloatProperty(
        name="Scale Max",
        description="Maximum scale factor",
        default=1.2,
        min=0.01,
        max=10.0
    )
    bpy.types.Scene.hrg_mesh_align_normal = bpy.props.BoolProperty(
        name="Align to Surface Normal",
        description="Orient object Z-axis to match ground/terrain slope (great for rocks/props; turn off for upright trees/houses)",
        default=False
    )
    bpy.types.Scene.hrg_mesh_z_offset = bpy.props.FloatProperty(
        name="Ground Z-Offset",
        description="Vertical elevation offset from ground surface",
        default=0.0
    )
    bpy.types.Scene.hrg_mesh_link_dups = bpy.props.BoolProperty(
        name="Linked Duplicate (Alt+D)",
        description="Share mesh data between instances to optimize viewport memory",
        default=False
    )

    # Prop Quick-Attacher Properties
    bpy.types.Scene.hrg_show_props = bpy.props.BoolProperty(
        name="Show Prop Manager",
        default=True
    )
    bpy.types.Scene.hrg_prop_source_obj = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Prop / Rig Object",
        description="Select prop object or armature rig (using dropdown, viewport click, or eyedropper pen)"
    )
    bpy.types.Scene.hrg_prop_object = bpy.props.EnumProperty(
        name="Prop Object / Rig",
        description="Select prop object or armature rig (Weapon, Pet, Tool, Phone) to attach",
        items=get_prop_items
    )
    bpy.types.Scene.hrg_prop_target_actor = bpy.props.EnumProperty(
        name="Target Actor",
        description="Character who will hold the prop or rig",
        items=get_actors_items
    )
    bpy.types.Scene.hrg_prop_slot = bpy.props.EnumProperty(
        name="Attach Slot",
        description="Body part to attach prop or rig to",
        items=[
            ('RIGHT_HAND', "Right Hand", "Attach prop to Right Hand palm"),
            ('LEFT_HAND', "Left Hand", "Attach prop to Left Hand palm"),
            ('HEAD', "Head (Hat / Glasses)", "Attach prop to Head"),
            ('CHEST', "Chest / Back (Backpack / Weapon Sheath)", "Attach prop to Chest/Back"),
            ('PELVIS', "Pelvis / Belt (Holster)", "Attach prop to Belt"),
            ('RIGHT_FOOT', "Right Foot (Shoes / Skates)", "Attach prop to Right Foot"),
            ('LEFT_FOOT', "Left Foot (Shoes / Skates)", "Attach prop to Left Foot")
        ],
        default='RIGHT_HAND'
    )
    
    bpy.types.Scene.hrg_dial_actor_a = bpy.props.EnumProperty(
        name="Actor A",
        description="First character for dialogue cameras",
        items=get_actors_items
    )
    bpy.types.Scene.hrg_dial_actor_b = bpy.props.EnumProperty(
        name="Actor B",
        description="Second character for dialogue cameras",
        items=get_actors_items
    )
    
    bpy.types.Scene.hrg_light_mood = bpy.props.EnumProperty(
        name="Lighting Mood",
        description="Cinematic lighting presets",
        items=[
            ('STUDIO', 'Studio Soft', 'Soft white area lights'),
            ('DRAMATIC', 'Cinematic Dramatic', 'High contrast warm key / cool fill'),
            ('SUNNY', 'Sunny Day', 'Warm sunlight key / sky blue fill'),
            ('HORROR', 'Horror Underlight', 'Green key from below'),
            ('NEON', 'Cyberpunk Neon', 'Contrasting pink key / cyan fill')
        ],
        default='STUDIO'
    )
    
    bpy.types.Scene.hrg_active_pose_selector = bpy.props.EnumProperty(
        name="Body Pose Preset",
        description="Select a quick starting body pose",
        items=[
            ('STAND_NEUTRAL', "Stand Neutral", "Reset to rest stand T-pose"),
            ('CROSS_ARMS', "Cross Arms", "Cross arms over chest"),
            ('SIT_CHAIR', "Sit on Chair", "Sit down with knees bent"),
            ('HOLD_PHONE', "Hold Phone", "Right hand holds a phone up"),
            ('TALK_GESTURE', "Dialogue Gesture", "Dialogue gesture hands")
        ],
        default='STAND_NEUTRAL'
    )
    
    # Register pose mixer properties on Object level
    bpy.types.Object.hrg_pose_walk_blend = bpy.props.FloatProperty(
        name="Walk Blend",
        description="Blend character into a walk pose",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_pose_run_blend = bpy.props.FloatProperty(
        name="Run Blend",
        description="Blend character into a run pose",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_pose_talk_blend = bpy.props.FloatProperty(
        name="Talk Blend",
        description="Blend character into a talk/gesture pose",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_jaw_open = bpy.props.FloatProperty(
        name="Jaw Open",
        description="Open/close character mouth",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_eye_blink_l = bpy.props.FloatProperty(
        name="Left Eye Blink",
        description="Blink/close left eye",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_eye_blink_r = bpy.props.FloatProperty(
        name="Right Eye Blink",
        description="Blink/close right eye",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_brow_raise_l = bpy.props.FloatProperty(
        name="Left Brow Raise",
        description="Raise left eyebrow",
        min=-0.5,
        max=1.5,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_brow_raise_r = bpy.props.FloatProperty(
        name="Right Brow Raise",
        description="Raise right eyebrow",
        min=-0.5,
        max=1.5,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_mouth_smile_l = bpy.props.FloatProperty(
        name="Left Mouth Smile/Frown",
        description="Left side smile (positive) or frown (negative)",
        min=-1.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_mouth_smile_r = bpy.props.FloatProperty(
        name="Right Mouth Smile/Frown",
        description="Right side smile (positive) or frown (negative)",
        min=-1.0,
        max=1.0,
        default=0.0,
        update=update_pose_mixer
    )
    bpy.types.Object.hrg_eye_target = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Eye Look Target",
        description="Select an object for the eyes to track",
        update=update_eye_target
    )
    bpy.types.Object.hrg_eye_influence = bpy.props.FloatProperty(
        name="Eye Tracking Influence",
        description="How strongly the eyes track the target object",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_eye_target
    )
    
    # Register pose-bone level IK/FK switch property
    bpy.types.PoseBone.hrg_ik_fk = bpy.props.FloatProperty(
        name="IK/FK Blend",
        description="IK/FK Blend (0 = FK, 1 = IK)",
        min=0.0,
        max=1.0,
        default=1.0,
        update=update_ik_fk_blend
    )
    
    # Register PoseBone level finger pose controller properties
    bpy.types.PoseBone.hrg_grasp = bpy.props.FloatProperty(
        name="Master Grasp", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )
    bpy.types.PoseBone.hrg_thumb = bpy.props.FloatProperty(
        name="Thumb", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )
    bpy.types.PoseBone.hrg_index = bpy.props.FloatProperty(
        name="Index", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )
    bpy.types.PoseBone.hrg_middle = bpy.props.FloatProperty(
        name="Middle", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )
    bpy.types.PoseBone.hrg_ring = bpy.props.FloatProperty(
        name="Ring", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )
    bpy.types.PoseBone.hrg_pinky = bpy.props.FloatProperty(
        name="Pinky", min=-1.0, max=2.0, default=0.0, update=update_finger_curls
    )

def update_ik_fk_blend(self, context):
    obj = self.id_data
    if not obj or obj.type != 'ARMATURE':
        return
        
    from .utils.naming import get_org_name
    
    side = ".L" if self.name.endswith(".L") else ".R"
    is_arm = "hand" in self.name
    
    if is_arm:
        chain = [f"upper_arm{side}", f"forearm{side}", f"hand{side}"]
    else:
        chain = [f"thigh{side}", f"shin{side}", f"foot{side}", f"toe{side}"]
        
    val = self.hrg_ik_fk
    
    for bone_base in chain:
        org_name = get_org_name(bone_base)
        pb_org = obj.pose.bones.get(org_name)
        if pb_org:
            for c in pb_org.constraints:
                if c.name in ["Copy_FK_Loc", "Copy_FK_Rot"]:
                    c.influence = 1.0 - val
                elif c.name in ["Copy_IK_Loc", "Copy_IK_Rot"]:
                    c.influence = val

def update_finger_curls(self, context):
    obj = self.id_data
    if not obj or obj.type != 'ARMATURE':
        return
        
    from .utils.naming import get_org_name
    
    side = ".L" if self.name.endswith(".L") else ".R"
    
    finger_bones = {
        "thumb": [
            (f"thumb.01{side}", 0.4),
            (f"thumb.02{side}", 0.6),
            (f"thumb.03{side}", 0.8)
        ],
        "index": [
            (f"index.01{side}", 0.8),
            (f"index.02{side}", 0.9),
            (f"index.03{side}", 0.7)
        ],
        "middle": [
            (f"middle.01{side}", 0.8),
            (f"middle.02{side}", 0.9),
            (f"middle.03{side}", 0.7)
        ],
        "ring": [
            (f"ring.01{side}", 0.8),
            (f"ring.02{side}", 0.9),
            (f"ring.03{side}", 0.7)
        ],
        "pinky": [
            (f"pinky.01{side}", 0.8),
            (f"pinky.02{side}", 0.9),
            (f"pinky.03{side}", 0.7)
        ]
    }
    
    grasp = self.hrg_grasp
    
    for finger_name, segments in finger_bones.items():
        curl = getattr(self, f"hrg_{finger_name}", 0.0)
        total_curl = grasp + curl
        
        for bone_base_name, factor in segments:
            org_bone_name = get_org_name(bone_base_name)
            pb_org = obj.pose.bones.get(org_bone_name)
            if pb_org:
                if pb_org.rotation_mode != 'XYZ':
                    pb_org.rotation_mode = 'XYZ'
                pb_org.rotation_euler.x = total_curl * factor

def unregister():
    # Remove depsgraph update post handler
    if on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        try:
            bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)
        except:
            pass
            
    # Unregister skeleton draw callback
    unregister_skeleton_draw()
            
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        
    # Unregister properties
    for prop in [
        "hrg_rig_type", "hrg_active_actor", "hrg_preset", 
        "hrg_start_frame", "hrg_set_timeline_range", "hrg_path_curve_obj", "hrg_path_duration", 
        "hrg_cam_shot", "hrg_cam_angle", "hrg_cam_orbit", "hrg_cam_follow", 
        "hrg_cam_target_actor", "hrg_active_camera", "hrg_light_mood",
        "hrg_dial_actor_a", "hrg_dial_actor_b", "hrg_active_pose_selector",
        "hrg_marker_size", "hrg_show_marker_names", "hrg_show_marker_lines",
        "hrg_show_asset_spawner", "hrg_spawn_source_obj", "hrg_mesh_spawn_count",
        "hrg_mesh_spawn_radius", "hrg_mesh_random_rot", "hrg_mesh_random_scale",
        "hrg_mesh_scale_min", "hrg_mesh_scale_max", "hrg_mesh_align_normal",
        "hrg_mesh_z_offset", "hrg_mesh_link_dups",
        "hrg_show_props", "hrg_prop_source_obj", "hrg_prop_object", "hrg_prop_target_actor", "hrg_prop_slot",
        "hrg_scene_action", "hrg_source_actor_to_copy",
        "hrg_anim_source_rig", "hrg_anim_target_rig", "hrg_anim_transfer_action", "hrg_anim_make_copy",
        "hrg_controller_scale",
        "hrg_use_bbone_legs", "hrg_bbone_segments_legs",
        "hrg_use_bbone_arms", "hrg_bbone_segments_arms",
        "hrg_use_bbone_spine", "hrg_bbone_segments_spine"
    ]:
        try:
            delattr(bpy.types.Scene, prop)
        except:
            pass
            
    for prop in [
        "hrg_pose_walk_blend", "hrg_pose_run_blend", "hrg_pose_talk_blend",
        "hrg_jaw_open", "hrg_eye_target", "hrg_eye_influence",
        "hrg_eye_blink_l", "hrg_eye_blink_r",
        "hrg_brow_raise_l", "hrg_brow_raise_r", "hrg_mouth_smile_l", "hrg_mouth_smile_r"
    ]:
        try:
            delattr(bpy.types.Object, prop)
        except:
            pass
            
    for prop in ["hrg_ik_fk", "hrg_grasp", "hrg_thumb", "hrg_index", "hrg_middle", "hrg_ring", "hrg_pinky"]:
        try:
            delattr(bpy.types.PoseBone, prop)
        except:
            pass
