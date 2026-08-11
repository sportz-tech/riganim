import bpy
import mathutils
import math
import os
from bpy_extras.io_utils import ImportHelper
from ..utils.naming import get_control_name


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

def assign_action_to_rig(arm_obj, action):
    """
    Assigns an action to an armature object, ensuring Blender 5.0+ Action Slots
    are properly connected and active so the rig actually evaluates the animation.
    """
    if not arm_obj:
        return
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
        
    arm_obj.animation_data.action = action
    
    # In Blender 5.0+ (Action Slots), ensure action_slot is assigned to an active slot
    if hasattr(arm_obj.animation_data, "action_slot") and hasattr(action, "slots"):
        if len(action.slots) > 0:
            slot_found = None
            for s in action.slots:
                ident = getattr(s, "identifier", "")
                if arm_obj.name in ident:
                    slot_found = s
                    break
            if not slot_found:
                slot_found = action.slots[0]
            arm_obj.animation_data.action_slot = slot_found
        elif hasattr(action.slots, "new"):
            try:
                new_slot = action.slots.new(name=arm_obj.name)
                arm_obj.animation_data.action_slot = new_slot
            except Exception:
                pass

# Frame length of loops
PRESET_LENGTHS = {
    'WALK': 24,
    'RUN': 16,
    'IDLE': 32,
    'WAVE': 24,
    'JUMP': 24,
    'TALK': 24,
    'SITTING': 32,
    'DOOR_OPEN': 32,
    'POINT': 24,
    'PUSH': 24,
    'SIT_SAD': 32,
    'CRYING': 32,
    'LAUGHING': 24,
    'PUNCH': 24,
    'KICK': 24,
    'BLOCK': 24,
    'DODGE': 24,
    'SPIN_KICK_FALL': 48,
    'PROP_JUMP_CROSS': 48
}

class OBJECT_OT_apply_animation_preset(bpy.types.Operator):
    """Applies a procedural looping animation preset at a specific frame."""
    bl_idname = "object.apply_animation_preset"
    bl_label = "Insert Animation Preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset_name: bpy.props.EnumProperty( # type: ignore
        name="Animation Preset",
        description="Select the animation preset to apply",
        items=[
            ('WALK', "Walk Loop", "Seamless walking loop"),
            ('RUN', "Run Loop", "Fast running loop"),
            ('IDLE', "Idle Breathing", "Subtle standing breathing loop"),
            ('WAVE', "Hand Wave", "Character waving hand"),
            ('JUMP', "Jump Cycle", "Crouch, peak height, and landing cycle"),
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
    
    start_frame: bpy.props.IntProperty( # type: ignore
        name="Start Frame",
        description="The starting timeline frame for the preset action",
        default=1,
        min=1
    )
    
    clear_existing: bpy.props.BoolProperty( # type: ignore
        name="Clear Existing Keys",
        description="Clear all existing keyframes before applying this preset",
        default=False
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        # 1. Handle animation clearing if requested
        if self.clear_existing:
            if obj.animation_data:
                obj.animation_data_clear()
                
        # 2. Ensure animation action exists
        if not obj.animation_data:
            obj.animation_data_create()
        if not obj.animation_data.action:
            obj.animation_data.action = bpy.data.actions.new(f"{obj.name}Action")
            
        action = obj.animation_data.action
        
        # Ensure we are in POSE mode to write keyframes
        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='POSE')
        
        # Read from scene properties
        scene = context.scene
        preset_name = scene.hrg_preset
        start_frame = scene.hrg_start_frame
        walk_dir = getattr(scene, "hrg_walk_direction", 'FORWARD')
        walk_style = getattr(scene, "hrg_walk_style", 'IN_PLACE')
        
        # Check if root bone has an active follow path constraint
        has_follow_path = False
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if pb_root:
            for c in pb_root.constraints:
                if c.type == 'FOLLOW_PATH' and c.target:
                    has_follow_path = True
                    break
                    
        if has_follow_path and walk_style == 'TRAVELING':
            walk_style = 'IN_PLACE'
            scene.hrg_walk_style = 'IN_PLACE'
            self.report({'INFO'}, "Rig is bound to a path. Switched Walk Style to 'In-Place' to prevent double translation.")
        
        # Determine duration
        speed_factor = getattr(scene, "hrg_anim_speed", 1.0)
        original_loop_length = PRESET_LENGTHS[preset_name]
        preset_duration = getattr(scene, "hrg_preset_duration", 24)
        
        # 3. Calculate aligned cycle length and segment duration
        cycle_length = max(4, round(original_loop_length / speed_factor))
        num_cycles = max(1, round(preset_duration / cycle_length))
        segment_duration = cycle_length * num_cycles
        
        # Update scene's hrg_preset_duration to the aligned value
        scene.hrg_preset_duration = segment_duration
        
        if has_follow_path:
            # Get the curve object from the follow path constraint to recalculate length
            curve_obj = None
            for c in pb_root.constraints:
                if c.type == 'FOLLOW_PATH' and c.target:
                    curve_obj = c.target
                    break
                    
            if curve_obj:
                # Calculate exact evaluated length of the path
                curve_length = 0.0
                if curve_obj.data.splines:
                    for spline in curve_obj.data.splines:
                        try:
                            curve_length += spline.calc_length()
                        except AttributeError:
                            points = spline.bezier_points if spline.type == 'BEZIER' else spline.points
                            if len(points) > 1:
                                for i in range(len(points) - 1):
                                    p1 = points[i].co.to_3d() if spline.type == 'BEZIER' else points[i].co.xyz
                                    p2 = points[i+1].co.to_3d() if spline.type == 'BEZIER' else points[i+1].co.xyz
                                    curve_length += (p2 - p1).length
                                    
                c_path = pb_root.constraints.get("Follow_Path")
                if c_path:
                    # Clear default path animations on curve data
                    if curve_obj.data.animation_data:
                        curve_obj.data.animation_data_clear()
                    curve_obj.data.use_path = False
                    c_path.offset = 0
                    
                    # 1. Determine starting offset factor by evaluating F-curve at start_frame
                    start_val = 1.0 if getattr(scene, "hrg_path_reverse", False) else 0.0
                    dp = f'pose.bones["{pb_root.name}"].constraints["Follow_Path"].offset_factor'
                    dp_offset = f'pose.bones["{pb_root.name}"].constraints["Follow_Path"].offset'
                    
                    found_fc = None
                    for fc in get_action_fcurves(action):
                        if fc.data_path == dp:
                            found_fc = fc
                            # Evaluate at start_frame to get continuous connection from previous segment
                            start_val = fc.evaluate(start_frame)
                            break
                                
                    # 2. Calculate delta offset for this segment if walk/run
                    delta_offset = 0.0
                    if preset_name in ['WALK', 'RUN']:
                        factor = 16.0 / 2.6 if preset_name == 'RUN' else 24.0 / 1.4
                        dist_traveled = (segment_duration / factor) * speed_factor
                        if curve_length > 0:
                            delta_offset = dist_traveled / curve_length
                            
                    # 3. Calculate ending offset factor
                    if getattr(scene, "hrg_path_reverse", False):
                        end_val = max(0.0, start_val - delta_offset)
                    else:
                        end_val = min(1.0, start_val + delta_offset)
                        
                    # 4. Clear keyframes on offset_factor in this segment's range only
                    if found_fc:
                        indices = [i for i, kp in enumerate(found_fc.keyframe_points) if start_frame <= kp.co.x <= (start_frame + segment_duration)]
                        for i in reversed(indices):
                            try:
                                found_fc.keyframe_points.remove(found_fc.keyframe_points[i])
                            except Exception:
                                pass
                            
                    # 5. Insert keyframes
                    c_path.offset_factor = start_val
                    obj.keyframe_insert(data_path=dp, frame=start_frame)
                    
                    c_path.offset_factor = end_val
                    obj.keyframe_insert(data_path=dp, frame=start_frame + segment_duration)
                    
                    # 6. Set keyframe interpolation to linear to prevent ease-in/ease-out bumps
                    for fc in get_action_fcurves(action):
                        if fc.data_path == dp:
                            for kp in fc.keyframe_points:
                                if kp.co.x in [start_frame, start_frame + segment_duration]:
                                    kp.interpolation = 'LINEAR'
                                        
                    # Reset constraint viewport value and timeline frame to start
                    c_path.offset_factor = start_val
                    context.scene.frame_current = start_frame
                    
                    # Force update timeline range end to fit the new segment
                    scene.frame_end = start_frame + segment_duration
                    
                self.report({'INFO'}, f"Applied path segment: {segment_duration} frames total.")
                
        loop_length = cycle_length
        end_frame = start_frame + segment_duration - 1
        
        # Auto-fit playback timeline range if requested
        if getattr(context.scene, "hrg_set_timeline_range", True):
            context.scene.frame_start = start_frame
            context.scene.frame_end = end_frame
        else:
            if context.scene.frame_end < (start_frame + segment_duration):
                context.scene.frame_end = start_frame + segment_duration
            
        lf_locs, rf_locs, lh_locs, rh_locs, pel_locs, pel_rots = {}, {}, {}, {}, {}, {}
        lh_rots, rh_rots = {}, {}
        jaw_rots = {}
        
        # Determine scale factor based on actual rig proportions
        anim_scale = 1.0
        try:
            pelvis_bone = obj.data.bones.get(get_control_name("pelvis"))
            foot_l_bone = obj.data.bones.get(get_control_name("foot_IK.L"))
            if pelvis_bone and foot_l_bone:
                leg_length = (foot_l_bone.head - pelvis_bone.head).length
                anim_scale = max(0.1, min(3.0, leg_length / 0.90))
        except Exception:
            pass
            
        # Read hand controller settings from scene properties
        import math
        hand_x = scene.hrg_hand_x_offset
        hand_z = scene.hrg_hand_z_offset
        walk_x = scene.hrg_walk_hand_x
        walk_z = scene.hrg_walk_hand_z
        run_x = scene.hrg_run_hand_x
        run_z = scene.hrg_run_hand_z
        wrist_pitch = math.radians(scene.hrg_wrist_pitch)

        # Standard hand base offsets for idle, talking, wave, etc.
        lh_base = (hand_x * anim_scale, 0.0, hand_z * anim_scale)
        rh_base = (-hand_x * anim_scale, 0.0, hand_z * anim_scale)
        
        # Walk hand base offsets (closer to thighs and lower)
        lh_walk_base = (walk_x * anim_scale, 0.0, walk_z * anim_scale)
        rh_walk_base = (-walk_x * anim_scale, 0.0, walk_z * anim_scale)
        
        # Base hand offsets for running
        lh_run_base = (run_x * anim_scale, -0.05 * anim_scale, run_z * anim_scale)
        rh_run_base = (-run_x * anim_scale, -0.05 * anim_scale, run_z * anim_scale)
        
        # Rotations to turn palms inward (facing thighs) and keep wrist straight down
        lh_down_rot = (wrist_pitch, 0.0, 0.0)
        rh_down_rot = (wrist_pitch, 0.0, 0.0)
        
        # Rotations for running/reaching (palms face inward, hand points forward along the bent forearm)
        lh_run_rot = (0.0, 0.0, 0.0)
        rh_run_rot = (0.0, 0.0, 0.0)
        
        travel_speed = 0.0
        if walk_style == 'TRAVELING':
            if walk_dir == 'FORWARD':
                travel_speed = -0.8 * anim_scale / 24.0 if preset_name == 'WALK' else -1.2 * anim_scale / 16.0
            else:
                travel_speed = 0.8 * anim_scale / 24.0 if preset_name == 'WALK' else 1.2 * anim_scale / 16.0
            travel_speed *= speed_factor
        
        if preset_name == 'WALK':
            if walk_dir == 'FORWARD':
                # Feet Gait
                lf_locs = {
                    1: (0.0, -0.15 * anim_scale, 0.0), 
                    7: (0.0, 0.0, 0.0), 
                    13: (0.0, 0.15 * anim_scale, 0.0), 
                    19: (0.0, 0.0, 0.08 * anim_scale), 
                    25: (0.0, -0.15 * anim_scale, 0.0)
                }
                rf_locs = {
                    1: (0.0, 0.15 * anim_scale, 0.0), 
                    7: (0.0, 0.0, 0.08 * anim_scale), 
                    13: (0.0, -0.15 * anim_scale, 0.0), 
                    19: (0.0, 0.0, 0.0), 
                    25: (0.0, 0.15 * anim_scale, 0.0)
                }
                
                # Left Leg Forward -> Left Arm Backward
                lh_locs = {
                    1: (lh_walk_base[0], lh_walk_base[1] + 0.10 * anim_scale, lh_walk_base[2]),
                    7: (lh_walk_base[0], lh_walk_base[1], lh_walk_base[2] - 0.01 * anim_scale),
                    13: (lh_walk_base[0], lh_walk_base[1] - 0.10 * anim_scale, lh_walk_base[2] + 0.03 * anim_scale),
                    19: (lh_walk_base[0], lh_walk_base[1], lh_walk_base[2] - 0.01 * anim_scale),
                    25: (lh_walk_base[0], lh_walk_base[1] + 0.10 * anim_scale, lh_walk_base[2])
                }
                # Right Leg Backward -> Right Arm Forward
                rh_locs = {
                    1: (rh_walk_base[0], rh_walk_base[1] - 0.10 * anim_scale, rh_walk_base[2] + 0.03 * anim_scale),
                    7: (rh_walk_base[0], rh_walk_base[1], rh_walk_base[2] - 0.01 * anim_scale),
                    13: (rh_walk_base[0], rh_walk_base[1] + 0.10 * anim_scale, rh_walk_base[2]),
                    19: (rh_walk_base[0], rh_walk_base[1], rh_walk_base[2] - 0.01 * anim_scale),
                    25: (rh_walk_base[0], rh_walk_base[1] - 0.10 * anim_scale, rh_walk_base[2] + 0.03 * anim_scale)
                }
                
                # Hand Rotations
                lh_rots = {
                    1: lh_down_rot,
                    7: lh_down_rot,
                    13: lh_down_rot,
                    19: lh_down_rot,
                    25: lh_down_rot
                }
                rh_rots = {
                    1: rh_down_rot,
                    7: rh_down_rot,
                    13: rh_down_rot,
                    19: rh_down_rot,
                    25: rh_down_rot
                }
                pel_rots = {1: (0.0, 0.0, -0.05), 7: (0.0, 0.0, 0.0), 13: (0.0, 0.0, 0.05), 19: (0.0, 0.0, 0.0), 25: (0.0, 0.0, -0.05)}
            else: # BACKWARD
                lf_locs = {1: (0.0, 0.15 * anim_scale, 0.0), 7: (0.0, 0.0, 0.08 * anim_scale), 13: (0.0, -0.15 * anim_scale, 0.0), 19: (0.0, 0.0, 0.0), 25: (0.0, 0.15 * anim_scale, 0.0)}
                rf_locs = {1: (0.0, -0.15 * anim_scale, 0.0), 7: (0.0, 0.0, 0.0), 13: (0.0, 0.15 * anim_scale, 0.0), 19: (0.0, 0.0, 0.08 * anim_scale), 25: (0.0, -0.15 * anim_scale, 0.0)}
                lh_locs = {
                    1: (lh_walk_base[0], lh_walk_base[1] - 0.10 * anim_scale, lh_walk_base[2] + 0.03 * anim_scale),
                    7: (lh_walk_base[0], lh_walk_base[1], lh_walk_base[2] - 0.01 * anim_scale),
                    13: (lh_walk_base[0], lh_walk_base[1] + 0.10 * anim_scale, lh_walk_base[2]),
                    19: (lh_walk_base[0], lh_walk_base[1], lh_walk_base[2] - 0.01 * anim_scale),
                    25: (lh_walk_base[0], lh_walk_base[1] - 0.10 * anim_scale, lh_walk_base[2] + 0.03 * anim_scale)
                }
                rh_locs = {
                    1: (rh_walk_base[0], rh_walk_base[1] + 0.10 * anim_scale, rh_walk_base[2]),
                    7: (rh_walk_base[0], rh_walk_base[1], rh_walk_base[2] - 0.01 * anim_scale),
                    13: (rh_walk_base[0], rh_walk_base[1] - 0.10 * anim_scale, rh_walk_base[2] + 0.03 * anim_scale),
                    19: (rh_walk_base[0], rh_walk_base[1], rh_walk_base[2] - 0.01 * anim_scale),
                    25: (rh_walk_base[0], rh_walk_base[1] + 0.10 * anim_scale, rh_walk_base[2])
                }
                lh_rots = {
                    1: lh_down_rot,
                    7: lh_down_rot,
                    13: lh_down_rot,
                    19: lh_down_rot,
                    25: lh_down_rot
                }
                rh_rots = {
                    1: rh_down_rot,
                    7: rh_down_rot,
                    13: rh_down_rot,
                    19: rh_down_rot,
                    25: rh_down_rot
                }
                pel_rots = {1: (0.0, 0.0, 0.05), 7: (0.0, 0.0, 0.0), 13: (0.0, 0.0, -0.05), 19: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.05)}
            pel_locs = {1: (0.0, 0.0, -0.02 * anim_scale), 7: (0.0, 0.0, 0.01 * anim_scale), 13: (0.0, 0.0, -0.02 * anim_scale), 19: (0.0, 0.0, 0.01 * anim_scale), 25: (0.0, 0.0, -0.02 * anim_scale)}
            
        elif preset_name == 'RUN':
            if walk_dir == 'FORWARD':
                lf_locs = {1: (0.0, -0.22 * anim_scale, 0.0), 5: (0.0, 0.0, 0.0), 9: (0.0, 0.22 * anim_scale, 0.0), 13: (0.0, 0.0, 0.14 * anim_scale), 17: (0.0, -0.22 * anim_scale, 0.0)}
                rf_locs = {1: (0.0, 0.22 * anim_scale, 0.0), 5: (0.0, 0.0, 0.14 * anim_scale), 9: (0.0, -0.22 * anim_scale, 0.0), 13: (0.0, 0.0, 0.0), 17: (0.0, 0.22 * anim_scale, 0.0)}
                
                lh_locs = {
                    1: (lh_run_base[0] - 0.02 * anim_scale, lh_run_base[1] + 0.15 * anim_scale, lh_run_base[2] + 0.04 * anim_scale),
                    5: (lh_run_base[0], lh_run_base[1], lh_run_base[2]),
                    9: (lh_run_base[0] + 0.02 * anim_scale, lh_run_base[1] - 0.15 * anim_scale, lh_run_base[2] + 0.08 * anim_scale),
                    13: (lh_run_base[0], lh_run_base[1], lh_run_base[2]),
                    17: (lh_run_base[0] - 0.02 * anim_scale, lh_run_base[1] + 0.15 * anim_scale, lh_run_base[2] + 0.04 * anim_scale)
                }
                rh_locs = {
                    1: (rh_run_base[0] + 0.02 * anim_scale, rh_run_base[1] - 0.15 * anim_scale, rh_run_base[2] + 0.08 * anim_scale),
                    5: (rh_run_base[0], rh_run_base[1], rh_run_base[2]),
                    9: (rh_run_base[0] - 0.02 * anim_scale, rh_run_base[1] + 0.15 * anim_scale, rh_run_base[2] + 0.04 * anim_scale),
                    13: (rh_run_base[0], rh_run_base[1], rh_run_base[2]),
                    17: (rh_run_base[0] + 0.02 * anim_scale, rh_run_base[1] - 0.15 * anim_scale, rh_run_base[2] + 0.08 * anim_scale)
                }
                lh_rots = {
                    1: lh_run_rot,
                    5: lh_run_rot,
                    9: lh_run_rot,
                    13: lh_run_rot,
                    17: lh_run_rot
                }
                rh_rots = {
                    1: rh_run_rot,
                    5: rh_run_rot,
                    9: rh_run_rot,
                    13: rh_run_rot,
                    17: rh_run_rot
                }
                pel_rots = {1: (0.0, 0.0, -0.08), 5: (0.0, 0.0, 0.0), 9: (0.0, 0.0, 0.08), 13: (0.0, 0.0, 0.0), 17: (0.0, 0.0, -0.08)}
            else:
                lf_locs = {1: (0.0, 0.22 * anim_scale, 0.0), 5: (0.0, 0.0, 0.14 * anim_scale), 9: (0.0, -0.22 * anim_scale, 0.0), 13: (0.0, 0.0, 0.0), 17: (0.0, 0.22 * anim_scale, 0.0)}
                rf_locs = {1: (0.0, -0.22 * anim_scale, 0.0), 5: (0.0, 0.0, 0.0), 9: (0.0, 0.22 * anim_scale, 0.0), 13: (0.0, 0.0, 0.14 * anim_scale), 17: (0.0, -0.22 * anim_scale, 0.0)}
                lh_locs = {
                    1: (lh_run_base[0] + 0.02 * anim_scale, lh_run_base[1] - 0.15 * anim_scale, lh_run_base[2] + 0.08 * anim_scale),
                    5: (lh_run_base[0], lh_run_base[1], lh_run_base[2]),
                    9: (lh_run_base[0] - 0.02 * anim_scale, lh_run_base[1] + 0.15 * anim_scale, lh_run_base[2] + 0.04 * anim_scale),
                    13: (lh_run_base[0], lh_run_base[1], lh_run_base[2]),
                    17: (lh_run_base[0] + 0.02 * anim_scale, lh_run_base[1] - 0.15 * anim_scale, lh_run_base[2] + 0.08 * anim_scale)
                }
                rh_locs = {
                    1: (rh_run_base[0] - 0.02 * anim_scale, rh_run_base[1] + 0.15 * anim_scale, rh_run_base[2] + 0.04 * anim_scale),
                    5: (rh_run_base[0], rh_run_base[1], rh_run_base[2]),
                    9: (rh_run_base[0] + 0.02 * anim_scale, rh_run_base[1] - 0.15 * anim_scale, rh_run_base[2] + 0.08 * anim_scale),
                    13: (rh_run_base[0], rh_run_base[1], rh_run_base[2]),
                    17: (rh_run_base[0] - 0.02 * anim_scale, rh_run_base[1] + 0.15 * anim_scale, rh_run_base[2] + 0.04 * anim_scale)
                }
                lh_rots = {
                    1: lh_run_rot,
                    5: lh_run_rot,
                    9: lh_run_rot,
                    13: lh_run_rot,
                    17: lh_run_rot
                }
                rh_rots = {
                    1: rh_run_rot,
                    5: rh_run_rot,
                    9: rh_run_rot,
                    13: rh_run_rot,
                    17: rh_run_rot
                }
                pel_rots = {1: (0.0, 0.0, 0.08), 5: (0.0, 0.0, 0.0), 9: (0.0, 0.0, -0.08), 13: (0.0, 0.0, 0.0), 17: (0.0, 0.0, 0.08)}
            pel_locs = {1: (0.0, 0.0, -0.04 * anim_scale), 5: (0.0, 0.0, 0.02 * anim_scale), 9: (0.0, 0.0, -0.04 * anim_scale), 13: (0.0, 0.0, 0.02 * anim_scale), 17: (0.0, 0.0, -0.04 * anim_scale)}
            
        elif preset_name == 'IDLE':
            lf_locs = {1: (0.0, 0.0, 0.0), 33: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 33: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 33: lh_base}
            rh_locs = {1: rh_base, 33: rh_base}
            lh_rots = {1: lh_down_rot, 33: lh_down_rot}
            rh_rots = {1: rh_down_rot, 33: rh_down_rot}
            pel_locs = {1: (0.0, 0.0, 0.0), 17: (0.0, 0.0, -0.01 * anim_scale), 33: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'WAVE':
            lf_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 25: lh_base}
            lh_rots = {1: lh_down_rot, 25: lh_down_rot}
            rh_locs = {
                1: rh_base, 
                5: (-0.15 * anim_scale, 0.0, 0.25 * anim_scale), 
                9: (-0.10 * anim_scale, -0.08 * anim_scale, 0.25 * anim_scale), 
                13: (-0.10 * anim_scale, 0.08 * anim_scale, 0.25 * anim_scale), 
                17: (-0.10 * anim_scale, -0.08 * anim_scale, 0.25 * anim_scale), 
                21: (-0.30 * anim_scale, 0.0, -0.35 * anim_scale),
                25: rh_base
            }
            rh_rots = {
                1: rh_down_rot,
                5: (0.0, 0.0, 0.0), 
                9: (0.0, 0.2, 0.0), 
                13: (0.0, -0.2, 0.0), 
                17: (0.0, 0.2, 0.0), 
                21: (0.0, 0.0, 0.8),
                25: rh_down_rot
            }
            pel_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'JUMP':
            lf_locs = {1: (0.0, 0.0, 0.0), 5: (0.0, 0.0, 0.0), 11: (0.0, 0.0, 0.20 * anim_scale), 17: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 5: (0.0, 0.0, 0.0), 11: (0.0, 0.0, 0.20 * anim_scale), 17: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: lh_base, 
                5: (lh_base[0], lh_base[1] + 0.08 * anim_scale, lh_base[2] + 0.08 * anim_scale), 
                11: (0.15 * anim_scale, -0.15 * anim_scale, 0.10 * anim_scale), 
                17: (lh_base[0], lh_base[1] - 0.05 * anim_scale, lh_base[2] + 0.05 * anim_scale), 
                25: lh_base
            }
            rh_locs = {
                1: rh_base, 
                5: (rh_base[0], rh_base[1] + 0.08 * anim_scale, rh_base[2] + 0.08 * anim_scale), 
                11: (-0.15 * anim_scale, -0.15 * anim_scale, 0.10 * anim_scale), 
                17: (rh_base[0], rh_base[1] - 0.05 * anim_scale, rh_base[2] + 0.05 * anim_scale), 
                25: rh_base
            }
            lh_rots = {
                1: lh_down_rot,
                5: lh_down_rot, 
                11: lh_down_rot, 
                17: lh_down_rot, 
                25: lh_down_rot
            }
            rh_rots = {
                1: rh_down_rot,
                5: rh_down_rot, 
                11: rh_down_rot, 
                17: rh_down_rot, 
                25: rh_down_rot
            }
            pel_locs = {1: (0.0, 0.0, 0.0), 5: (0.0, 0.0, -0.12 * anim_scale), 11: (0.0, 0.0, 0.35 * anim_scale), 17: (0.0, 0.0, -0.08 * anim_scale), 25: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'TALK':
            lf_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 25: lh_base}
            rh_locs = {1: rh_base, 25: rh_base}
            lh_rots = {1: lh_down_rot, 25: lh_down_rot}
            rh_rots = {1: rh_down_rot, 25: rh_down_rot}
            pel_locs = {1: (0.0, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            jaw_rots = {1: (0.0, 0.0, 0.0), 4: (0.15, 0.0, 0.0), 8: (0.0, 0.0, 0.0), 12: (0.22, 0.0, 0.0), 16: (0.05, 0.0, 0.0), 20: (0.18, 0.0, 0.0), 25: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'SITTING':
            lf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 12: (0.12 * anim_scale, -0.15 * anim_scale, -0.35 * anim_scale), 32: (0.12 * anim_scale, -0.15 * anim_scale, -0.35 * anim_scale)}
            rh_locs = {1: rh_base, 12: (-0.12 * anim_scale, -0.15 * anim_scale, -0.35 * anim_scale), 32: (-0.12 * anim_scale, -0.15 * anim_scale, -0.35 * anim_scale)}
            lh_rots = {1: lh_down_rot, 12: (0.3, 0.0, -1.57), 32: (0.3, 0.0, -1.57)}
            rh_rots = {1: rh_down_rot, 12: (0.3, 0.0, 1.57), 32: (0.3, 0.0, 1.57)}
            pel_locs = {1: (0.0, 0.0, 0.0), 12: (0.0, -0.2 * anim_scale, -0.45 * anim_scale), 32: (0.0, -0.22 * anim_scale, -0.45 * anim_scale)}
            pel_rots = {1: (0.0, 0.0, 0.0), 12: (0.1, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'DOOR_OPEN':
            lf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 32: lh_base}
            rh_locs = {
                1: rh_base,
                10: (-0.10 * anim_scale, -0.45 * anim_scale, -0.05 * anim_scale),
                14: (-0.10 * anim_scale, -0.45 * anim_scale, -0.10 * anim_scale),
                22: (-0.15 * anim_scale, -0.20 * anim_scale, -0.05 * anim_scale),
                32: rh_base
            }
            rh_rots = {
                1: rh_down_rot,
                10: (0.0, 0.0, 1.5708),
                14: (0.3, 0.0, 1.5708),
                22: (0.0, 0.0, 1.5708),
                32: rh_down_rot
            }
            pel_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'POINT':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            lh_locs = {1: lh_base, 24: lh_base}
            rh_locs = {
                1: rh_base,
                8: (-0.12 * anim_scale, -0.55 * anim_scale, -0.05 * anim_scale),
                16: (-0.12 * anim_scale, -0.55 * anim_scale, -0.05 * anim_scale),
                24: rh_base
            }
            rh_rots = {
                1: rh_down_rot,
                8: (0.0, 0.0, 1.5708),
                16: (0.0, 0.0, 1.5708),
                24: rh_down_rot
            }
            pel_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            
        elif preset_name == 'PUSH':
            lf_locs = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, 0.15 * anim_scale, 0.0),
                16: (0.0, 0.12 * anim_scale, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            rf_locs = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, -0.05 * anim_scale, 0.0),
                16: (0.0, -0.08 * anim_scale, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            lh_locs = {
                1: lh_base,
                8: (0.18 * anim_scale, -0.30 * anim_scale, -0.30 * anim_scale),
                16: (0.18 * anim_scale, -0.45 * anim_scale, -0.28 * anim_scale),
                24: lh_base
            }
            rh_locs = {
                1: rh_base,
                8: (-0.18 * anim_scale, -0.30 * anim_scale, -0.30 * anim_scale),
                16: (-0.18 * anim_scale, -0.45 * anim_scale, -0.28 * anim_scale),
                24: rh_base
            }
            lh_rots = {1: lh_down_rot, 8: (-1.5708, 0.0, -1.5708), 16: (-1.5708, 0.0, -1.5708), 24: lh_down_rot}
            rh_rots = {1: rh_down_rot, 8: (1.5708, 0.0, 1.5708), 16: (1.5708, 0.0, 1.5708), 24: rh_down_rot}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, -0.08 * anim_scale, -0.02 * anim_scale),
                16: (0.0, -0.15 * anim_scale, -0.04 * anim_scale),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                8: (0.08, 0.0, 0.0),
                16: (0.15, 0.0, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            
        elif preset_name == 'SIT_SAD':
            lf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: (0.08 * anim_scale, -0.15 * anim_scale, -0.32 * anim_scale),
                16: (0.08 * anim_scale, -0.15 * anim_scale, -0.34 * anim_scale),
                32: (0.08 * anim_scale, -0.15 * anim_scale, -0.32 * anim_scale)
            }
            rh_locs = {
                1: (-0.08 * anim_scale, -0.15 * anim_scale, -0.32 * anim_scale),
                16: (-0.08 * anim_scale, -0.15 * anim_scale, -0.34 * anim_scale),
                32: (-0.08 * anim_scale, -0.15 * anim_scale, -0.32 * anim_scale)
            }
            lh_rots = {1: (lh_run_rot[0] + 0.3, lh_run_rot[1], lh_run_rot[2]), 32: (lh_run_rot[0] + 0.3, lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0] + 0.3, rh_run_rot[1], rh_run_rot[2]), 32: (rh_run_rot[0] + 0.3, rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, -0.22 * anim_scale, -0.45 * anim_scale),
                16: (0.0, -0.21 * anim_scale, -0.47 * anim_scale),
                32: (0.0, -0.22 * anim_scale, -0.45 * anim_scale)
            }
            pel_rots = {1: (0.2, 0.0, 0.0), 32: (0.2, 0.0, 0.0)}
            
        elif preset_name == 'CRYING':
            lf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 32: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: (0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale),
                8: (0.08 * anim_scale, -0.12 * anim_scale, -0.13 * anim_scale),
                16: (0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale),
                24: (0.08 * anim_scale, -0.12 * anim_scale, -0.13 * anim_scale),
                32: (0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale)
            }
            rh_locs = {
                1: (-0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale),
                8: (-0.08 * anim_scale, -0.12 * anim_scale, -0.13 * anim_scale),
                16: (-0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale),
                24: (-0.08 * anim_scale, -0.12 * anim_scale, -0.13 * anim_scale),
                32: (-0.08 * anim_scale, -0.12 * anim_scale, -0.15 * anim_scale)
            }
            lh_rots = {1: (0.0, 1.57, -1.57), 32: (0.0, 1.57, -1.57)}
            rh_rots = {1: (0.0, 1.57, 1.57), 32: (0.0, 1.57, 1.57)}
            pel_locs = {
                1: (0.0, -0.05 * anim_scale, -0.05 * anim_scale),
                8: (0.0, -0.04 * anim_scale, -0.03 * anim_scale),
                16: (0.0, -0.05 * anim_scale, -0.05 * anim_scale),
                24: (0.0, -0.04 * anim_scale, -0.03 * anim_scale),
                32: (0.0, -0.05 * anim_scale, -0.05 * anim_scale)
            }
            pel_rots = {1: (0.15, 0.0, 0.0), 32: (0.15, 0.0, 0.0)}
            
        elif preset_name == 'LAUGHING':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: (0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale),
                6: (0.12 * anim_scale, -0.16 * anim_scale, -0.62 * anim_scale),
                12: (0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale),
                18: (0.12 * anim_scale, -0.16 * anim_scale, -0.62 * anim_scale),
                24: (0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale)
            }
            rh_locs = {
                1: (-0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale),
                6: (-0.12 * anim_scale, -0.16 * anim_scale, -0.62 * anim_scale),
                12: (-0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale),
                18: (-0.12 * anim_scale, -0.16 * anim_scale, -0.62 * anim_scale),
                24: (-0.12 * anim_scale, -0.18 * anim_scale, -0.65 * anim_scale)
            }
            lh_rots = {1: (lh_run_rot[0] + 0.2, lh_run_rot[1], lh_run_rot[2]), 24: (lh_run_rot[0] + 0.2, lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0] + 0.2, rh_run_rot[1], rh_run_rot[2]), 24: (rh_run_rot[0] + 0.2, rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                6: (0.0, 0.02 * anim_scale, 0.03 * anim_scale),
                12: (0.0, 0.0, 0.0),
                18: (0.0, 0.02 * anim_scale, 0.03 * anim_scale),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                6: (-0.08, 0.0, 0.0),
                12: (0.0, 0.0, 0.0),
                18: (-0.08, 0.0, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            jaw_rots = {
                1: (0.0, 0.0, 0.0),
                6: (0.25, 0.0, 0.0),
                12: (0.05, 0.0, 0.0),
                18: (0.25, 0.0, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            
        elif preset_name == 'PUNCH':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                8: (0.15 * anim_scale, -0.12 * anim_scale, -0.12 * anim_scale),
                24: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)
            }
            rh_locs = {
                1: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                8: (-0.12 * anim_scale, 0.12 * anim_scale, -0.10 * anim_scale), # Wind-up back
                12: (-0.02 * anim_scale, -0.55 * anim_scale, 0.05 * anim_scale), # Punch FORWARD (-Y)
                16: (-0.02 * anim_scale, -0.52 * anim_scale, 0.05 * anim_scale),
                24: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)
            }
            lh_rots = {1: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2]), 24: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2]), 12: (rh_run_rot[0] + 0.3, rh_run_rot[1], rh_run_rot[2] - 0.5), 24: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, 0.02 * anim_scale, 0.0),
                12: (0.02 * anim_scale, -0.05 * anim_scale, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, 0.0, -0.08),
                12: (0.0, 0.0, 0.2),
                24: (0.0, 0.0, 0.0)
            }
            
        elif preset_name == 'KICK':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {
                1: (0.0, 0.0, 0.0),
                6: (0.0, -0.15 * anim_scale, 0.35 * anim_scale), # Chamber knee lift up & forward
                12: (0.0, -0.62 * anim_scale, 0.42 * anim_scale), # Snap kick FORWARD (-Y)
                18: (0.0, -0.15 * anim_scale, 0.35 * anim_scale), # Chamber back
                24: (0.0, 0.0, 0.0) # Ground plant
            }
            lh_locs = {1: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale), 24: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)}
            rh_locs = {1: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale), 24: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)}
            lh_rots = {1: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2]), 24: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2]), 24: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                6: (0.0, 0.04 * anim_scale, -0.02 * anim_scale),
                12: (0.0, 0.12 * anim_scale, -0.06 * anim_scale), # Lean back for high forward kick
                18: (0.0, 0.04 * anim_scale, -0.02 * anim_scale),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                6: (-0.08, 0.0, -0.08),
                12: (-0.15, 0.0, -0.15),
                18: (-0.08, 0.0, -0.08),
                24: (0.0, 0.0, 0.0)
            }

        elif preset_name == 'BLOCK':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            lh_locs = {
                1: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                12: (0.06 * anim_scale, 0.08 * anim_scale, 0.08 * anim_scale),
                24: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)
            }
            rh_locs = {
                1: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                12: (-0.06 * anim_scale, 0.08 * anim_scale, 0.08 * anim_scale),
                24: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)
            }
            lh_rots = {1: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2]), 12: (lh_run_rot[0] + 0.5, lh_run_rot[1], lh_run_rot[2] - 0.5), 24: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2]), 12: (rh_run_rot[0] + 0.5, rh_run_rot[1], rh_run_rot[2] + 0.5), 24: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                12: (0.0, -0.04 * anim_scale, -0.05 * anim_scale),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                12: (0.12, 0.0, 0.0),
                24: (0.0, 0.0, 0.0)
            }
            
        elif preset_name == 'DODGE':
            lf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            rf_locs = {1: (0.0, 0.0, 0.0), 24: (0.0, 0.0, 0.0)}
            lh_locs = {1: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale), 24: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)}
            rh_locs = {1: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale), 24: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale)}
            lh_rots = {1: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2]), 24: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2])}
            rh_rots = {1: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2]), 24: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2])}
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                12: (0.18 * anim_scale, -0.05 * anim_scale, -0.05 * anim_scale),
                24: (0.0, 0.0, 0.0)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                12: (0.0, -0.15, -0.12),
                24: (0.0, 0.0, 0.0)
            }
            
        elif preset_name == 'SPIN_KICK_FALL':
            lf_locs = {
                1: (0.13 * anim_scale, 0.0, 0.0),
                8: (0.13 * anim_scale, 0.0, 0.2 * anim_scale),
                16: (0.13 * anim_scale, -0.2 * anim_scale, 0.5 * anim_scale),
                24: (0.13 * anim_scale, 0.0, 0.4 * anim_scale),
                36: (0.2 * anim_scale, -0.4 * anim_scale, 0.05 * anim_scale),
                48: (0.2 * anim_scale, -0.5 * anim_scale, 0.05 * anim_scale)
            }
            rf_locs = {
                1: (-0.13 * anim_scale, 0.0, 0.0),
                8: (-0.13 * anim_scale, 0.0, 0.2 * anim_scale),
                16: (-0.1 * anim_scale, 0.62 * anim_scale, 0.9 * anim_scale),
                24: (-0.15 * anim_scale, 0.2 * anim_scale, 0.5 * anim_scale),
                36: (-0.2 * anim_scale, -0.4 * anim_scale, 0.05 * anim_scale),
                48: (-0.2 * anim_scale, -0.5 * anim_scale, 0.05 * anim_scale)
            }
            lh_locs = {
                1: (0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                16: (0.4 * anim_scale, -0.2 * anim_scale, -0.1 * anim_scale),
                36: (0.3 * anim_scale, -0.2 * anim_scale, -0.8 * anim_scale),
                48: (0.3 * anim_scale, -0.3 * anim_scale, -0.8 * anim_scale)
            }
            rh_locs = {
                1: (-0.15 * anim_scale, -0.15 * anim_scale, -0.15 * anim_scale),
                16: (-0.4 * anim_scale, -0.2 * anim_scale, -0.1 * anim_scale),
                36: (-0.3 * anim_scale, -0.2 * anim_scale, -0.8 * anim_scale),
                48: (-0.3 * anim_scale, -0.3 * anim_scale, -0.8 * anim_scale)
            }
            lh_rots = {
                1: (lh_run_rot[0], lh_run_rot[1], lh_run_rot[2]), 
                16: (lh_run_rot[0] + 0.5, lh_run_rot[1], lh_run_rot[2] - 0.5),
                36: (lh_run_rot[0] + 1.2, lh_run_rot[1], lh_run_rot[2]),
                48: (lh_run_rot[0] + 1.2, lh_run_rot[1], lh_run_rot[2])
            }
            rh_rots = {
                1: (rh_run_rot[0], rh_run_rot[1], rh_run_rot[2]), 
                16: (rh_run_rot[0] + 0.5, rh_run_rot[1], rh_run_rot[2] + 0.5),
                36: (rh_run_rot[0] + 1.2, rh_run_rot[1], rh_run_rot[2]),
                48: (rh_run_rot[0] + 1.2, rh_run_rot[1], rh_run_rot[2])
            }
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                6: (0.0, 0.0, -0.15 * anim_scale),
                16: (0.0, 0.1 * anim_scale, 0.6 * anim_scale),
                28: (0.0, -0.1 * anim_scale, 0.2 * anim_scale),
                36: (0.0, -0.5 * anim_scale, -0.7 * anim_scale),
                48: (0.0, -0.5 * anim_scale, -0.7 * anim_scale)
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                6: (0.1, 0.0, 0.0),
                16: (0.0, 0.0, 3.14),
                24: (0.0, 0.0, 6.28),
                36: (1.4, 0.0, 0.0),
                48: (1.4, 0.0, 0.0)
            }
            
        elif preset_name in ['PROP_JUMP_CROSS', 'PARKOUR_VAULT']:
            # Cinematic 48-frame one-hand handrail vault jump:
            # 1. Left hand locks firmly onto the rod at a single fixed pivot point (frames 8-28)
            # 2. Right hand stays held high in the air for balance and prop grip
            # 3. Hips and both legs sweep in a wide, high 3D semicircular arc (+Z, +X, -Y) sailing over the rod
            # 4. Releases rod, absorbs landing impact, and settles into a clean normal standing pose
            rod_pivot = (0.22 * anim_scale, -0.45 * anim_scale, -0.25 * anim_scale)
            
            lf_locs = {
                1: (0.12 * anim_scale, 0.0, 0.0),
                8: (0.14 * anim_scale, 0.05 * anim_scale, 0.0), # Jump plant before rod
                14: (0.35 * anim_scale, -0.15 * anim_scale, 0.40 * anim_scale), # Arc takeoff & lateral swing
                20: (0.58 * anim_scale, -0.50 * anim_scale, 0.62 * anim_scale), # Apex high arc over rod (exact drawing pose)
                26: (0.40 * anim_scale, -0.90 * anim_scale, 0.35 * anim_scale), # Arc descent past the rod
                32: (0.20 * anim_scale, -1.20 * anim_scale, 0.05 * anim_scale), # Reaching for landing ground
                38: (0.12 * anim_scale, -1.35 * anim_scale, 0.0), # Touchdown impact
                48: (0.12 * anim_scale, -1.40 * anim_scale, 0.0)  # Clean normal standing pose
            }
            rf_locs = {
                1: (-0.12 * anim_scale, 0.0, 0.0),
                8: (-0.14 * anim_scale, -0.05 * anim_scale, 0.0),
                14: (0.25 * anim_scale, -0.05 * anim_scale, 0.30 * anim_scale),
                20: (0.48 * anim_scale, -0.40 * anim_scale, 0.55 * anim_scale), # Trailing foot high arc over rod
                26: (0.30 * anim_scale, -0.75 * anim_scale, 0.28 * anim_scale),
                32: (0.10 * anim_scale, -1.05 * anim_scale, 0.05 * anim_scale),
                38: (-0.12 * anim_scale, -1.25 * anim_scale, 0.0),
                48: (-0.12 * anim_scale, -1.40 * anim_scale, 0.0)
            }
            lh_locs = {
                # Left hand locks firmly on the rod at rod_pivot throughout the whole vault (frames 8-28)
                1: (lh_base[0], 0.0, lh_base[2]),
                8: rod_pivot,  # Plant on rod
                14: rod_pivot, # Holding rod as body vaults
                20: rod_pivot, # Holding rod at apex
                26: rod_pivot, # Push off rod
                32: (0.20 * anim_scale, -0.85 * anim_scale, -0.15 * anim_scale), # Release rod
                38: (0.18 * anim_scale, -1.20 * anim_scale, -0.45 * anim_scale), # Shock absorption
                48: (lh_base[0], -1.40 * anim_scale, lh_base[2]) # Normal standing rest pose
            }
            rh_locs = {
                # Right arm held high in the air holding prop throughout the entire vault flight
                1: (rh_base[0], 0.0, rh_base[2]),
                8: (-0.20 * anim_scale, 0.15 * anim_scale, -0.10 * anim_scale), # Wind-up
                14: (-0.30 * anim_scale, 0.05 * anim_scale, 0.45 * anim_scale), # Swing high
                20: (-0.35 * anim_scale, 0.08 * anim_scale, 0.65 * anim_scale), # High aloft in air (drawing pose)
                26: (-0.30 * anim_scale, -0.20 * anim_scale, 0.45 * anim_scale), # Guiding balance
                32: (-0.25 * anim_scale, -0.65 * anim_scale, 0.15 * anim_scale), # Lowering on descent
                38: (-0.18 * anim_scale, -1.20 * anim_scale, -0.45 * anim_scale), # Shock absorption
                48: (rh_base[0], -1.40 * anim_scale, rh_base[2]) # Normal standing rest pose
            }
            lh_rots = {
                1: lh_down_rot,
                8: (1.3, 0.0, -1.4), # Firm grip on rod
                14: (1.4, 0.1, -1.4),
                20: (1.4, 0.3, -1.4), # Hand pivot on rod at apex
                26: (1.2, 0.1, -1.2),
                32: (0.4, 0.0, -0.4), # Release
                38: (0.2, 0.0, 0.0),
                48: lh_down_rot # Reset to normal rest rotation
            }
            rh_rots = {
                1: rh_down_rot,
                8: (rh_run_rot[0] + 0.3, rh_run_rot[1] - 0.3, rh_run_rot[2] + 0.2),
                14: (-0.6, 0.4, 1.2),
                20: (-0.8, 0.5, 1.4), # Upward fist/prop rotation at apex
                26: (-0.4, 0.3, 0.8),
                32: (0.2, 0.1, 0.3),
                38: (0.2, 0.0, 0.0),
                48: rh_down_rot # Reset to normal rest rotation
            }
            pel_locs = {
                1: (0.0, 0.0, 0.0),
                8: (0.0, 0.05 * anim_scale, -0.20 * anim_scale), # Crouch load
                14: (0.10 * anim_scale, -0.25 * anim_scale, 0.35 * anim_scale), # Takeoff
                20: (0.22 * anim_scale, -0.55 * anim_scale, 0.58 * anim_scale), # High apex clearance over rod
                26: (0.15 * anim_scale, -0.85 * anim_scale, 0.40 * anim_scale), # Arc descent
                32: (0.05 * anim_scale, -1.15 * anim_scale, 0.15 * anim_scale), # Descent flight
                38: (0.0, -1.35 * anim_scale, -0.22 * anim_scale), # Deep landing absorption crouch
                48: (0.0, -1.40 * anim_scale, 0.0) # Normal standing pose height
            }
            pel_rots = {
                1: (0.0, 0.0, 0.0),
                8: (0.15, 0.0, 0.0),
                14: (0.15, 0.40, 0.20),
                20: (0.25, 0.70, 0.35), # 40° sideways roll sailing over rod
                26: (0.20, 0.35, 0.15),
                32: (0.15, 0.10, 0.0),
                38: (0.25, 0.0, 0.0), # Landing absorption tilt
                48: (0.0, 0.0, 0.0) # Reset to normal upright rotation
            }
            
        if loop_length != original_loop_length:
            scale_time = (loop_length - 1) / (original_loop_length - 1)
            
            def scale_dict(d):
                if not d: return {}
                new_d = {}
                for k, v in d.items():
                    new_k = 1 + int(round((k - 1) * scale_time))
                    new_d[new_k] = v
                # Ensure the last frame matches exactly loop_length
                last_key = max(d.keys())
                new_last_key = 1 + int(round((last_key - 1) * scale_time))
                if new_last_key in new_d:
                    val = new_d.pop(new_last_key)
                    new_d[loop_length] = val
                return new_d

            lf_locs = scale_dict(lf_locs)
            rf_locs = scale_dict(rf_locs)
            lh_locs = scale_dict(lh_locs)
            rh_locs = scale_dict(rh_locs)
            pel_locs = scale_dict(pel_locs)
            pel_rots = scale_dict(pel_rots)
            lh_rots = scale_dict(lh_rots)
            rh_rots = scale_dict(rh_rots)
            jaw_rots = scale_dict(jaw_rots)

        if travel_speed != 0.0:
            # We apply travel offset dynamically during keyframe insertion below
            pass
            
        # Target FK upper arms and forearms as well as IK hands to reset T-pose arms properly
        mappings = [
            (get_control_name("foot_IK.L"), lf_locs, None),
            (get_control_name("foot_IK.R"), rf_locs, None),
            (get_control_name("hand_IK.L"), lh_locs, lh_rots),
            (get_control_name("hand_IK.R"), rh_locs, rh_rots),
            (get_control_name("pelvis"), pel_locs, pel_rots),
            (get_control_name("jaw"), None, jaw_rots),
            # Keyframe FK arms to pull them down out of T-Pose
            (get_control_name("arm_fk.L"), None, {1: (0.0, 0.0, -1.35), loop_length: (0.0, 0.0, -1.35)}),
            (get_control_name("arm_fk.R"), None, {1: (0.0, 0.0, 1.35), loop_length: (0.0, 0.0, 1.35)}),
        ]
        
        # Force IK/FK switch properties to 1.0 (IK mode) at start frame to ensure presets play correctly
        for side in [".L", ".R"]:
            for part in ["hand_IK", "foot_IK"]:
                pb_ik = obj.pose.bones.get(get_control_name(f"{part}{side}"))
                if pb_ik:
                    pb_ik.hrg_ik_fk = 1.0
                    pb_ik.keyframe_insert(data_path="hrg_ik_fk", frame=start_frame)
                    
        translation_bones = [
            get_control_name("foot_IK.L"),
            get_control_name("foot_IK.R"),
            get_control_name("hand_IK.L"),
            get_control_name("hand_IK.R"),
            get_control_name("pelvis")
        ]
        
        for bone_name, loc_data, rot_data in mappings:
            pb = obj.pose.bones.get(bone_name)
            if not pb:
                continue
                
            if pb.rotation_mode != 'XYZ':
                pb.rotation_mode = 'XYZ'
                
            loc_keys = list(loc_data.keys()) if loc_data else []
            rot_keys = list(rot_data.keys()) if rot_data else []
            all_keys = sorted(set(loc_keys + rot_keys))
            
            for c in range(num_cycles):
                cycle_start_frame = start_frame + c * loop_length
                for f_local in all_keys:
                    f_target = cycle_start_frame + f_local - 1
                    
                    if loc_data and f_local in loc_data:
                        val = loc_data[f_local]
                        # Apply travel offset dynamically per frame across cycles
                        if travel_speed != 0.0 and bone_name in translation_bones:
                            elapsed = c * loop_length + f_local - 1
                            val = (val[0], val[1] + travel_speed * elapsed, val[2])
                            
                        world_offset = mathutils.Vector(val)
                        local_offset = pb.bone.matrix_local.to_3x3().inverted() @ world_offset
                        pb.location = local_offset
                        pb.keyframe_insert(data_path="location", frame=f_target)
                    if rot_data and f_local in rot_data:
                        pb.rotation_euler = rot_data[f_local]
                        pb.keyframe_insert(data_path="rotation_euler", frame=f_target)
                        
        if action:
            for fcurve in get_action_fcurves(action):
                has_cycles = False
                for mod in fcurve.modifiers:
                    if mod.type == 'CYCLES':
                        has_cycles = True
                        break
                if not has_cycles:
                    fcurve.modifiers.new(type='CYCLES')
            
        bpy.ops.object.mode_set(mode=original_mode)
        
        self.report({'INFO'}, f"Inserted preset '{preset_name}' starting at frame {start_frame}!")
        return {'FINISHED'}

class OBJECT_OT_push_to_nla(bpy.types.Operator):
    """Pushes the active action down to a new NLA track for layered blending."""
    bl_idname = "object.push_to_nla"
    bl_label = "Push Action to NLA"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No active animation action found to push down!")
            return {'CANCELLED'}
            
        action = obj.animation_data.action
        
        # Create track and strip via python API
        track = obj.animation_data.nla_tracks.new()
        track.name = f"Track_{action.name}"
        
        start_frame = int(action.frame_range[0])
        strip = track.strips.new(action.name, start_frame, action)
        strip.blend_type = 'REPLACE'
        
        # Clear active action to prevent duplicate movements
        obj.animation_data.action = None
        
        self.report({'INFO'}, f"Successfully pushed action '{action.name}' to track '{track.name}'!")
        return {'FINISHED'}

class OBJECT_OT_bind_rig_to_path(bpy.types.Operator):
    """Binds the rig's root bone to follow a curve and animates traversal."""
    bl_idname = "object.bind_rig_to_path"
    bl_label = "Bind Rig to Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    curve_name: bpy.props.StringProperty( # type: ignore
        name="Curve Name",
        description="Select the scene curve object to follow"
    )
    
    duration: bpy.props.IntProperty( # type: ignore
        name="Duration (Frames)",
        description="Duration of the path traversal in frames",
        default=120,
        min=1
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        # Automatically switch walk style to 'IN_PLACE' if set to 'TRAVELING'
        # so that character plays loop in-place and translation is driven by the path constraint.
        if context.scene.hrg_walk_style == 'TRAVELING':
            context.scene.hrg_walk_style = 'IN_PLACE'
            try:
                bpy.ops.object.apply_animation_preset()
                self.report({'INFO'}, "Switched Walk Style to 'In-Place' to align with the path.")
            except Exception as e:
                self.report({'WARNING'}, f"Could not auto-apply In-Place preset: {e}")
            
        # Retrieve curve from scene property first
        curve_obj = context.scene.hrg_path_curve_obj
        if not curve_obj and self.curve_name:
            curve_obj = bpy.data.objects.get(self.curve_name)
            
        if not curve_obj or curve_obj.type not in ['CURVE', 'MESH']:
            self.report({'WARNING'}, "Please select a valid Curve path or Mesh line in the viewport or panel!")
            return {'CANCELLED'}
            
        # If the path is a Mesh (e.g. converted Bezier curve or edge line), auto-convert it to a Curve object
        if curve_obj.type == 'MESH':
            mesh_data = curve_obj.data
            curve_name = f"{curve_obj.name}_CurvePath"
            new_curve_obj = bpy.data.objects.get(curve_name)
            if not new_curve_obj:
                new_curve_data = bpy.data.curves.new(f"{curve_name}_Data", type='CURVE')
                new_curve_data.dimensions = '3D'
                new_curve_obj = bpy.data.objects.new(curve_name, new_curve_data)
                context.scene.collection.objects.link(new_curve_obj)
                
            new_curve_data = new_curve_obj.data
            new_curve_data.splines.clear()
            if len(mesh_data.vertices) > 1:
                spline = new_curve_data.splines.new(type='POLY')
                spline.points.add(len(mesh_data.vertices) - 1)
                for i, v in enumerate(mesh_data.vertices):
                    spline.points[i].co = (v.co.x, v.co.y, v.co.z, 1.0)
                    
            new_curve_obj.matrix_world = curve_obj.matrix_world.copy()
            curve_obj = new_curve_obj
            context.scene.hrg_path_curve_obj = new_curve_obj
            self.report({'INFO'}, f"Auto-converted Mesh into Curve Path '{curve_name}'!")
            
        # Auto-detect whether the rig is closer to the start or end of the curve in world coordinates
        start_world = None
        end_world = None
        if curve_obj.data.splines:
            s_first = curve_obj.data.splines[0]
            if s_first.type == 'BEZIER' and len(s_first.bezier_points) > 0:
                start_local = s_first.bezier_points[0].co.to_3d()
            elif len(s_first.points) > 0:
                start_local = s_first.points[0].co.xyz
            else:
                start_local = None
                
            s_last = curve_obj.data.splines[-1]
            if s_last.type == 'BEZIER' and len(s_last.bezier_points) > 0:
                end_local = s_last.bezier_points[-1].co.to_3d()
            elif len(s_last.points) > 0:
                end_local = s_last.points[-1].co.xyz
            else:
                end_local = None
                
            if start_local is not None and end_local is not None:
                start_world = curve_obj.matrix_world @ start_local
                end_world = curve_obj.matrix_world @ end_local

        if start_world is not None and end_world is not None:
            # Get original armature position before applying transforms
            rig_pos = obj.matrix_world.translation
            dist_to_start = (rig_pos - start_world).length
            dist_to_end = (rig_pos - end_world).length
            
            # Auto-set reverse property depending on proximity
            is_reverse = dist_to_end < dist_to_start
            context.scene.hrg_path_reverse = is_reverse
            self.report({'INFO'}, f"Auto-detected walk starting point: {'End of Path' if is_reverse else 'Start of Path'}")
            
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if not pb_root:
            self.report({'WARNING'}, "CTRL-root control bone not found!")
            return {'CANCELLED'}
            
        # Calculate curve length to auto-sync walk duration
        curve_length = 0.0
        if curve_obj.data.splines:
            for spline in curve_obj.data.splines:
                try:
                    # Use Blender's built-in evaluated spline length for precision Bezier path syncing
                    curve_length += spline.calc_length()
                except AttributeError:
                    # Fallback to straight line distance between anchors
                    points = spline.bezier_points if spline.type == 'BEZIER' else spline.points
                    if len(points) > 1:
                        for i in range(len(points) - 1):
                            p1 = points[i].co.to_3d() if spline.type == 'BEZIER' else points[i].co.xyz
                            p2 = points[i+1].co.to_3d() if spline.type == 'BEZIER' else points[i+1].co.xyz
                            curve_length += (p2 - p1).length
                        
        # Auto-calculate ideal travel duration
        preset = context.scene.hrg_preset
        factor = 16.0 / 2.6 if preset == 'RUN' else 24.0 / 1.4
        
        calculated_duration = max(24, int(curve_length * factor))
        
        final_duration = self.duration
        if self.duration == 120:
            final_duration = calculated_duration
            context.scene.hrg_path_duration = calculated_duration
            self.report({'INFO'}, f"Synced walk duration: {calculated_duration} frames for curve length {curve_length:.2f}m")
            
        # Reset armature object transform to world origin so the bone follow-path constraint snaps directly onto the curve
        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        
        # Clear any manual offset/transform on the root bone to ensure it centers on the path
        pb_root.location = (0.0, 0.0, 0.0)
        if pb_root.rotation_mode == 'QUATERNION':
            pb_root.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        elif pb_root.rotation_mode == 'AXIS_ANGLE':
            pb_root.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
        else:
            pb_root.rotation_euler = (0.0, 0.0, 0.0)
        pb_root.scale = (1.0, 1.0, 1.0)

        # Clean existing constraints
        for c in list(pb_root.constraints):
            if c.type == 'FOLLOW_PATH':
                pb_root.constraints.remove(c)
                
        # Create constraint
        c = pb_root.constraints.new(type='FOLLOW_PATH')
        c.name = "Follow_Path"
        c.target = curve_obj
        c.use_curve_follow = True
        c.use_fixed_location = True
        c.forward_axis = getattr(context.scene, "hrg_path_facing", 'TRACK_NEGATIVE_Y')
        c.up_axis = 'UP_Z'
        
        # Clear any auto-generated path animation on the curve data itself to prevent start/end jumps
        if curve_obj.data.animation_data:
            curve_obj.data.animation_data_clear()
        curve_obj.data.use_path = False
        
        # Explicitly reset constraint offset to 0 to prevent double-offset drift
        c.offset = 0
        
        # Keyframe offset_factor
        if not obj.animation_data:
            obj.animation_data_create()
        if not obj.animation_data.action:
            obj.animation_data.action = bpy.data.actions.new(f"{obj.name}Action")
            
        action = obj.animation_data.action
        
        # Clear existing keyframes for both offset_factor and offset on the constraint
        dp = f'pose.bones["{pb_root.name}"].constraints["{c.name}"].offset_factor'
        dp_offset = f'pose.bones["{pb_root.name}"].constraints["{c.name}"].offset'
        for fc in get_action_fcurves(action):
            if fc.data_path in [dp, dp_offset]:
                remove_action_fcurve(action, fc)
                
        start_frame = context.scene.frame_start
        end_frame = start_frame + final_duration
        
        # Keyframe Start (0.0 or 1.0 depending on reverse path)
        start_val = 1.0 if context.scene.hrg_path_reverse else 0.0
        end_val = 0.0 if context.scene.hrg_path_reverse else 1.0
        
        c.offset_factor = start_val
        obj.keyframe_insert(
            data_path=dp,
            frame=start_frame
        )
        
        # Keyframe End (1.0 or 0.0 depending on reverse path)
        c.offset_factor = end_val
        obj.keyframe_insert(
            data_path=dp,
            frame=end_frame
        )
        
        # Set keyframe interpolation to linear to prevent ease-in/ease-out bumps
        for fc in get_action_fcurves(action):
            if fc.data_path == dp:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                        
        # Ensure tracking empty is generated and attached to head/chest
        ensure_cam_target(obj, context.scene)
        
        # Reset constraint viewport value and timeline frame to start
        c.offset_factor = start_val
        context.scene.frame_current = start_frame
        context.view_layer.update()
        
        # Set scene end frame
        context.scene.frame_end = end_frame
        
        self.report({'INFO'}, f"Bound rig to follow curve path '{curve_obj.name}' successfully!")
        return {'FINISHED'}

class OBJECT_OT_unbind_rig_from_path(bpy.types.Operator):
    """Unbinds the rig's root bone from the curve path constraint."""
    bl_idname = "object.unbind_rig_from_path"
    bl_label = "Reset Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        pb_root = obj.pose.bones.get(get_control_name("root"))
        if pb_root:
            # Remove FOLLOW_PATH constraints
            removed = False
            for c in list(pb_root.constraints):
                if c.type == 'FOLLOW_PATH':
                    pb_root.constraints.remove(c)
                    removed = True
                    
            # Clear constraint offset keyframes
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                dp = f'pose.bones["{pb_root.name}"].constraints["Follow_Path"].offset_factor'
                for fc in get_action_fcurves(action):
                    if fc.data_path == dp:
                        remove_action_fcurve(action, fc)
                            
            # Reset root bone transforms
            pb_root.location = (0.0, 0.0, 0.0)
            if pb_root.rotation_mode == 'QUATERNION':
                pb_root.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            else:
                pb_root.rotation_euler = (0.0, 0.0, 0.0)
            pb_root.scale = (1.0, 1.0, 1.0)
            
            # Reset curve property in scene
            context.scene.hrg_path_curve_obj = None
            
            if removed:
                self.report({'INFO'}, "Successfully reset path and removed Follow Path constraint.")
            else:
                self.report({'INFO'}, "No curve path constraints were bound to the rig.")
        else:
            self.report({'WARNING'}, "CTRL-root control bone not found!")
            
        return {'FINISHED'}

class OBJECT_OT_clear_rig_animation(bpy.types.Operator):
    """Safely clears all animations from the active rig and resets pose transforms."""
    bl_idname = "object.clear_rig_animation"
    bl_label = "Clear Animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        # Reset animation action
        if obj.animation_data:
            obj.animation_data_clear()
            
        # Reset pose bone locations & rotations
        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='POSE')
        
        for pb in obj.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
            
        bpy.ops.object.mode_set(mode=original_mode)
        
        self.report({'INFO'}, "Cleared all keyframes and reset pose transforms.")
        return {'FINISHED'}

def ensure_cam_target(obj, scene, shot_type='MEDIUM'):
    """Ensures a dedicated tracking empty exists and is parented to the appropriate character bone."""
    from ..utils.naming import get_control_name
    target_name = f"Cam_Target_{obj.name}"
    target = bpy.data.objects.get(target_name)
    if not target:
        target = bpy.data.objects.new(target_name, None)
        target.empty_display_type = 'SINGLE_ARROW'
        target.empty_display_size = 0.15
        scene.collection.objects.link(target)
        
    # Choose tracking bone based on shot type
    if shot_type == 'CLOSEUP':
        bone_name = get_control_name("head")
    elif shot_type == 'MEDIUM':
        bone_name = get_control_name("spine.003") or get_control_name("spine") or get_control_name("head")
    else: # WIDE
        bone_name = get_control_name("pelvis") or get_control_name("root")
        
    if bone_name not in obj.pose.bones:
        bone_name = get_control_name("head")
        if bone_name not in obj.pose.bones:
            bone_name = get_control_name("root")
            if bone_name not in obj.pose.bones and len(obj.pose.bones) > 0:
                bone_name = obj.pose.bones[0].name
                
    if target.parent != obj or target.parent_bone != bone_name:
        target.parent = obj
        target.parent_type = 'BONE'
        target.parent_bone = bone_name
        target.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        target.location = (0.0, 0.0, 0.0)
    return target

class OBJECT_OT_setup_scene_camera(bpy.types.Operator):
    """Sets up and aligns the active scene camera targeting the character dynamically."""
    bl_idname = "object.setup_scene_camera"
    bl_label = "Setup Scene Camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    switch_view: bpy.props.BoolProperty(default=True) # type: ignore
    
    def execute(self, context):
        scene = context.scene
        
        # 1. Determine target actor armature object
        obj = None
        target_actor_name = scene.hrg_cam_target_actor
        if target_actor_name != 'NONE':
            obj = bpy.data.objects.get(target_actor_name)
            
        if not obj:
            # Fallback to active armature object
            obj = context.active_object
            if not obj or obj.type != 'ARMATURE':
                # Or any armature in the scene
                for o in scene.objects:
                    if o.type == 'ARMATURE':
                        obj = o
                        break
                        
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No character rig (armature) found to target!")
            return {'CANCELLED'}
            
        # 2. Get active camera name and object (reuse existing camera)
        cam_name = scene.hrg_active_camera
        cam_obj = None
        if cam_name != 'NONE' and cam_name:
            cam_obj = bpy.data.objects.get(cam_name)
            
        if not cam_obj:
            # Check if scene already has an active camera
            if scene.camera and scene.camera.type == 'CAMERA':
                cam_obj = scene.camera
            else:
                # Check if any camera already exists in the scene
                for o in scene.objects:
                    if o.type == 'CAMERA':
                        cam_obj = o
                        break
                        
        if not cam_obj:
            # Only create a new camera if absolutely NO camera exists in the scene
            cam_name = "Rig_Camera"
            cam_data = bpy.data.cameras.new(f"{cam_name}_Data")
            cam_obj = bpy.data.objects.new(cam_name, cam_data)
            cam_obj.show_name = getattr(scene, "hrg_show_camera_names", True)
            scene.collection.objects.link(cam_obj)
            
        # Ensure it is set as active scene camera
        scene.camera = cam_obj
        if scene.hrg_active_camera != cam_obj.name:
            scene.hrg_active_camera = cam_obj.name
        
        # 3. Create or get tracking target Empty on head/chest
        shot_type = scene.hrg_cam_shot
        target = ensure_cam_target(obj, scene, shot_type)
        
        from ..utils.naming import get_control_name
        root_bone_name = get_control_name("root")
        if root_bone_name not in obj.data.bones and len(obj.data.bones) > 0:
            root_bone_name = obj.data.bones[0].name
        
        # 4. Add Track To constraint to camera targeting Cam_Target if tracking mode supports it
        track = cam_obj.constraints.get("Track_To")
        if scene.hrg_cam_follow in ['TRACK', 'MOVE']:
            if not track:
                track = cam_obj.constraints.new(type='TRACK_TO')
                track.name = "Track_To"
            track.target = target
            track.track_axis = 'TRACK_NEGATIVE_Z'
            track.up_axis = 'UP_Y'
        else:
            if track:
                cam_obj.constraints.remove(track)
        
        # 5. Handle Parenting (Camera Follow)
        if scene.hrg_cam_follow != 'MOVE' and cam_obj.parent:
            cam_obj.parent = None
            cam_obj.matrix_parent_inverse.identity()
        
        # 6. Calculate camera location relative to the character
        anchor_pos = target.matrix_world.to_translation()
        
        if shot_type == 'CLOSEUP':
            distance = 0.85
            height_offset = 0.0
        elif shot_type == 'MEDIUM':
            distance = 2.4
            height_offset = 0.2
        else: # WIDE
            distance = 5.2
            height_offset = 0.5
            
        angle = scene.hrg_cam_angle
        # Character faces -Y by default in this rig system, so front is -Y
        if angle == 'FRONT':
            dir_vec = mathutils.Vector((0.0, -1.0, 0.0))
        elif angle == 'BACK':
            dir_vec = mathutils.Vector((0.0, 1.0, 0.0))
        elif angle == 'THREE_QUARTER':
            dir_vec = mathutils.Vector((0.707, -0.707, 0.0))
        elif angle == 'BACK_THREE_QUARTER':
            dir_vec = mathutils.Vector((0.707, 0.707, 0.0))
        elif angle == 'SIDE':
            dir_vec = mathutils.Vector((1.0, 0.0, 0.0))
        elif angle == 'HIGH':
            dir_vec = mathutils.Vector((0.0, -1.0, 0.5))
        else: # LOW
            dir_vec = mathutils.Vector((0.0, -1.0, -0.25))
            
        # Apply Orbit Rotation around Z-axis dynamically
        orbit_rad = math.radians(scene.hrg_cam_orbit)
        rot_z = mathutils.Matrix.Rotation(orbit_rad, 3, 'Z')
        dir_vec = rot_z @ dir_vec
        dir_vec = dir_vec.normalized()
        
        # Define local offset vector relative to character
        offset_local = dir_vec * (distance * scene.hrg_cam_distance_factor)
        offset_local.z += height_offset
        
        # Transform local offset to world space using the character's real facing direction
        bone_root = obj.pose.bones.get(root_bone_name)
        if bone_root:
            root_world_mat = obj.matrix_world @ bone_root.matrix
            rot_scale_matrix = root_world_mat.to_3x3()
        else:
            rot_scale_matrix = obj.matrix_world.to_3x3()
            
        offset_world = rot_scale_matrix @ offset_local
        cam_pos = anchor_pos + offset_world
        
        # 7. Apply parent and position based on hrg_cam_follow selection
        if scene.hrg_cam_follow == 'MOVE':
            if cam_obj.parent != obj or cam_obj.parent_bone != root_bone_name:
                cam_obj.parent = obj
                cam_obj.parent_type = 'BONE'
                cam_obj.parent_bone = root_bone_name
                cam_obj.matrix_parent_inverse.identity()
            if bone_root:
                bone_world_mat = obj.matrix_world @ bone_root.matrix
                cam_obj.location = bone_world_mat.inverted() @ cam_pos
            else:
                cam_obj.location = obj.matrix_world.inverted() @ cam_pos
        else:
            # STATIC or TRACK (no parenting)
            if cam_obj.parent:
                cam_obj.parent = None
                cam_obj.matrix_parent_inverse.identity()
            cam_obj.location = cam_pos
            
            # For STATIC mode, calculate and apply static rotation to look at the character
            if scene.hrg_cam_follow == 'STATIC':
                direction = anchor_pos - cam_pos
                if direction.length > 0.0001:
                    rot_quat = direction.to_track_quat('-Z', 'Y')
                    cam_obj.rotation_euler = rot_quat.to_euler()
        
        # Only switch viewport perspective when explicitly clicking Align & View
        if self.switch_view:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.region_3d.view_perspective = 'CAMERA'
                            space.camera = cam_obj
                            break
                            
        return {'FINISHED'}

class OBJECT_OT_add_scene_camera(bpy.types.Operator):
    """Adds a new camera setup to the scene for film setup switching."""
    bl_idname = "object.add_scene_camera"
    bl_label = "Add New Camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        # Find next camera number
        num = 1
        while f"Rig_Camera_{num:02d}" in bpy.data.objects:
            num += 1
        cam_name = f"Rig_Camera_{num:02d}"
        
        # Create Camera
        cam_data = bpy.data.cameras.new(f"{cam_name}_Data")
        cam_obj = bpy.data.objects.new(cam_name, cam_data)
        cam_obj.show_name = getattr(scene, "hrg_show_camera_names", True)
        scene.collection.objects.link(cam_obj)
        
        self.report({'INFO'}, f"Created camera '{cam_name}'")
        
        # Force update list and set active
        scene.hrg_active_camera = cam_name
        
        return {'FINISHED'}

class OBJECT_OT_audio_lip_sync(bpy.types.Operator, ImportHelper):
    """Imports an audio file and bakes it onto the jaw control F-curve for lip sync."""
    bl_idname = "object.audio_lip_sync"
    bl_label = "Audio Lip Sync"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty( # type: ignore
        name="Audio File",
        description="Select the speech audio file (.wav, .mp3, .ogg)",
        subtype='FILE_PATH'
    )
    
    filter_glob: bpy.props.StringProperty( # type: ignore
        default="*.wav;*.mp3;*.ogg",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        pb_jaw = obj.pose.bones.get(get_control_name("jaw"))
        if not pb_jaw:
            self.report({'WARNING'}, "CTRL-jaw control bone not found on the rig!")
            return {'CANCELLED'}
            
        if pb_jaw.rotation_mode != 'XYZ':
            pb_jaw.rotation_mode = 'XYZ'
            
        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='POSE')
        
        pb_jaw.rotation_euler.x = 0.0
        pb_jaw.keyframe_insert(data_path="rotation_euler", index=0, frame=1)
        
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "F-Curve could not be initialized.")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}
            
        action = obj.animation_data.action
        for fc in get_action_fcurves(action):
            fc.select = False
            
        dp = f'pose.bones["{pb_jaw.name}"].rotation_euler'
        target_fcurve = None
        for fc in get_action_fcurves(action):
            if fc.data_path == dp and fc.array_index == 0:
                fc.select = True
                target_fcurve = fc
                break
                
        if not target_fcurve:
            self.report({'WARNING'}, "Target jaw F-Curve not found.")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}
            
        area_to_switch = None
        if context.area:
            area_to_switch = context.area
        elif context.screen and context.screen.areas:
            area_to_switch = context.screen.areas[0]
            
        original_area_type = None
        if area_to_switch:
            original_area_type = area_to_switch.type
            area_to_switch.type = 'GRAPH_EDITOR'
            
        try:
            bpy.ops.graph.sound_bake(filepath=self.filepath, low=30, high=3000)
        except Exception as e:
            self.report({'ERROR'}, f"Sound bake failed: {str(e)}")
            return {'CANCELLED'}
        finally:
            if area_to_switch and original_area_type:
                area_to_switch.type = original_area_type
            bpy.ops.object.mode_set(mode=original_mode)
            
        self.report({'INFO'}, f"Successfully baked audio '{self.filepath}' to lip sync!")
        return {'FINISHED'}

def update_pose_mixer(self, context):
    if self.type != 'ARMATURE':
        return
        
    import mathutils
    from ..utils.naming import get_control_name, get_org_name
    
    pose_bones = self.pose.bones
    
    lf = pose_bones.get(get_control_name("foot_IK.L"))
    rf = pose_bones.get(get_control_name("foot_IK.R"))
    lh = pose_bones.get(get_control_name("hand_IK.L"))
    rh = pose_bones.get(get_control_name("hand_IK.R"))
    pelvis = pose_bones.get(get_control_name("pelvis"))
    jaw = pose_bones.get(get_control_name("jaw"))
    
    # Retrieve slider values
    walk_blend = getattr(self, "hrg_pose_walk_blend", 0.0)
    run_blend = getattr(self, "hrg_pose_run_blend", 0.0)
    talk_blend = getattr(self, "hrg_pose_talk_blend", 0.0)
    jaw_open = getattr(self, "hrg_jaw_open", 0.0)
    
    # Determine size scale factor dynamically
    anim_scale = 1.0
    try:
        pelvis_bone = self.data.bones.get(get_control_name("pelvis"))
        foot_l_bone = self.data.bones.get(get_control_name("foot_IK.L"))
        if pelvis_bone and foot_l_bone:
            leg_length = (foot_l_bone.head - pelvis_bone.head).length
            anim_scale = max(0.1, min(3.0, leg_length / 0.90))
    except Exception:
        pass
        
    # Define Walk Pose target offsets relative to neutral pose
    lf_walk_loc = mathutils.Vector((0.0, 0.25 * anim_scale, 0.0))
    rf_walk_loc = mathutils.Vector((0.0, -0.25 * anim_scale, 0.0))
    lh_walk_loc = mathutils.Vector((0.0, -0.25 * anim_scale, -0.1 * anim_scale))
    rh_walk_loc = mathutils.Vector((0.0, 0.25 * anim_scale, -0.1 * anim_scale))
    pelvis_walk_loc = mathutils.Vector((0.0, 0.0, -0.05 * anim_scale))
    
    # Define Run Pose target offsets (torso leaning, legs high, arms bent)
    lf_run_loc = mathutils.Vector((0.0, 0.45 * anim_scale, 0.0))
    rf_run_loc = mathutils.Vector((0.0, -0.45 * anim_scale, 0.3 * anim_scale))
    lh_run_loc = mathutils.Vector((0.0, 0.35 * anim_scale, 0.2 * anim_scale))
    rh_run_loc = mathutils.Vector((0.0, -0.35 * anim_scale, 0.1 * anim_scale))
    pelvis_run_loc = mathutils.Vector((0.0, 0.15 * anim_scale, -0.15 * anim_scale))
    pelvis_run_rot = mathutils.Euler((0.25, 0.0, 0.0))
    
    # Define Talk Pose target offsets (hands gesturing in front)
    lf_talk_loc = mathutils.Vector((0.0, 0.0, 0.0))
    rf_talk_loc = mathutils.Vector((0.0, 0.0, 0.0))
    lh_talk_loc = mathutils.Vector((0.15 * anim_scale, 0.22 * anim_scale, 0.15 * anim_scale))
    rh_talk_loc = mathutils.Vector((-0.15 * anim_scale, 0.26 * anim_scale, 0.22 * anim_scale))
    pelvis_talk_loc = mathutils.Vector((0.0, 0.0, 0.0))
    
    # Blend offsets
    lf_loc = lf_walk_loc * walk_blend + lf_run_loc * run_blend + lf_talk_loc * talk_blend
    rf_loc = rf_walk_loc * walk_blend + rf_run_loc * run_blend + rf_talk_loc * talk_blend
    lh_loc = lh_walk_loc * walk_blend + lh_run_loc * run_blend + lh_talk_loc * talk_blend
    rh_loc = rh_walk_loc * walk_blend + rh_run_loc * run_blend + rh_talk_loc * talk_blend
    pelvis_loc = pelvis_walk_loc * walk_blend + pelvis_run_loc * run_blend + pelvis_talk_loc * talk_blend
    
    # Apply combined offsets to pose bones
    if lf: lf.location = lf_loc
    if rf: rf.location = rf_loc
    if lh: lh.location = lh_loc
    if rh: rh.location = rh_loc
    if pelvis:
        pelvis.location = pelvis_loc
        pelvis.rotation_mode = 'XYZ'
        pelvis.rotation_euler = mathutils.Euler((pelvis_run_rot.x * run_blend, pelvis_run_rot.y * run_blend, pelvis_run_rot.z * run_blend))
        
    if jaw:
        jaw.rotation_mode = 'XYZ'
        jaw.rotation_euler.x = 0.18 * jaw_open + 0.06 * talk_blend
        
    # 1. Smooth Rigify Eyelid Blinking (Spherical Arc Follow)
    ctrl_eyes = pose_bones.get(get_control_name("eyes_look"))
    blink_l = getattr(self, "hrg_eye_blink_l", 0.0)
    blink_r = getattr(self, "hrg_eye_blink_r", 0.0)
    if ctrl_eyes:
        ctrl_eyes["eye_close.L"] = blink_l
        ctrl_eyes["eye_close.R"] = blink_r
        
    for side, blink in [(".L", blink_l), (".R", blink_r)]:
        # Upper eyelid 3-bone smooth parabolic curve: meets lower lid precisely at central eye slit
        u1 = pose_bones.get(f"ORG-eyelid.upper.01{side}")
        u2 = pose_bones.get(f"ORG-eyelid.upper.02{side}") or pose_bones.get(f"ORG-eyelid.upper{side}")
        u3 = pose_bones.get(f"ORG-eyelid.upper.03{side}")
        
        if u1:
            u1.rotation_mode = 'XYZ'
            u1.rotation_euler.x = min(0.0, -0.26 * blink) # -14.9 deg
        if u2:
            u2.rotation_mode = 'XYZ'
            u2.rotation_euler.x = min(0.0, -0.38 * blink) # -21.8 deg
        if u3:
            u3.rotation_mode = 'XYZ'
            u3.rotation_euler.x = min(0.0, -0.30 * blink) # -17.2 deg
            
        # Lower eyelid 3-bone subtle meeting curve
        l1 = pose_bones.get(f"ORG-eyelid.lower.01{side}")
        l2 = pose_bones.get(f"ORG-eyelid.lower.02{side}") or pose_bones.get(f"ORG-eyelid.lower{side}")
        l3 = pose_bones.get(f"ORG-eyelid.lower.03{side}")
        
        if l1:
            l1.rotation_mode = 'XYZ'
            l1.rotation_euler.x = max(0.0, 0.07 * blink)
        if l2:
            l2.rotation_mode = 'XYZ'
            l2.rotation_euler.x = max(0.0, 0.12 * blink)
        if l3:
            l3.rotation_mode = 'XYZ'
            l3.rotation_euler.x = max(0.0, 0.08 * blink)
            
    # 2. Smooth Rigify Eyebrows (Unified Natural Arch Follow)
    brow_l = getattr(self, "hrg_brow_raise_l", 0.0)
    brow_r = getattr(self, "hrg_brow_raise_r", 0.0)
    
    pb_brow_ctrl_l = pose_bones.get("CTRL-eyebrow.L")
    if pb_brow_ctrl_l:
        pb_brow_ctrl_l.location.z = 0.016 * anim_scale * brow_l
        pb_brow_ctrl_l.rotation_mode = 'XYZ'
        pb_brow_ctrl_l.rotation_euler.y = 0.05 * brow_l
    pb_brow_ctrl_r = pose_bones.get("CTRL-eyebrow.R")
    if pb_brow_ctrl_r:
        pb_brow_ctrl_r.location.z = 0.016 * anim_scale * brow_r
        pb_brow_ctrl_r.rotation_mode = 'XYZ'
        pb_brow_ctrl_r.rotation_euler.y = -0.05 * brow_r
        
    # Keep child detail bones strictly aligned with the eyebrow control without stretching
    for side in [".L", ".R"]:
        for b_idx in ["01", "02", "03"]:
            b = pose_bones.get(f"ORG-eyebrow.{b_idx}{side}")
            if b:
                b.location = (0.0, 0.0, 0.0)

    # 3. Smooth Rigify Mouth, Lips & Cheeks
    smile_l = getattr(self, "hrg_mouth_smile_l", 0.0)
    smile_r = getattr(self, "hrg_mouth_smile_r", 0.0)
    smile_avg = (smile_l + smile_r) * 0.5
    
    pb_lip_up = pose_bones.get("CTRL-lip.upper")
    if pb_lip_up:
        pb_lip_up.location.z = 0.012 * anim_scale * smile_avg + 0.004 * anim_scale * jaw_open
        
    pb_lip_low = pose_bones.get("CTRL-lip.lower")
    if pb_lip_low:
        pb_lip_low.location.z = 0.008 * anim_scale * smile_avg - 0.012 * anim_scale * jaw_open
        
    corner_l = pose_bones.get("ORG-lip.corner.L")
    if corner_l:
        if smile_l > 0.0:
            corner_l.location.x = 0.012 * anim_scale * smile_l
            corner_l.location.z = 0.010 * anim_scale * smile_l
        else:
            corner_l.location.x = 0.0
            corner_l.location.z = 0.0
            
    corner_r = pose_bones.get("ORG-lip.corner.R")
    if corner_r:
        if smile_r > 0.0:
            corner_r.location.x = -0.012 * anim_scale * smile_r
            corner_r.location.z = 0.010 * anim_scale * smile_r
        else:
            corner_r.location.x = 0.0
            corner_r.location.z = 0.0
            
    cheek_l = pose_bones.get("ORG-cheek.L")
    if cheek_l:
        cheek_l.location.z = 0.012 * anim_scale * max(0.0, smile_l)
        cheek_l.location.y = -0.004 * anim_scale * max(0.0, smile_l)
    cheek_r = pose_bones.get("ORG-cheek.R")
    if cheek_r:
        cheek_r.location.z = 0.012 * anim_scale * max(0.0, smile_r)
        cheek_r.location.y = -0.004 * anim_scale * max(0.0, smile_r)

def update_eye_target(self, context):
    if self.type != 'ARMATURE':
        return
        
    from ..utils.naming import get_control_name
    
    ctrl_eyes = self.pose.bones.get(get_control_name("eyes_look"))
    if not ctrl_eyes:
        return
        
    target_obj = getattr(self, "hrg_eye_target", None)
    influence = getattr(self, "hrg_eye_influence", 0.0)
    
    c_name = "Track_Scene_Target"
    constraint = None
    for c in list(ctrl_eyes.constraints):
        if c.name == c_name:
            constraint = c
            break
            
    if target_obj:
        if not constraint:
            constraint = ctrl_eyes.constraints.new(type='TRACK_TO')
            constraint.name = c_name
        constraint.target = target_obj
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'
        constraint.influence = influence
    else:
        if constraint:
            ctrl_eyes.constraints.remove(constraint)

class OBJECT_OT_reset_pose_mixer(bpy.types.Operator):
    """Resets all Pose Mixer sliders and clears pose transforms of the active armature."""
    bl_idname = "object.reset_pose_mixer"
    bl_label = "Reset Pose Mixer"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the Human Rig armature first!")
            return {'CANCELLED'}
            
        # Reset slider properties to default (0.0)
        obj.hrg_pose_walk_blend = 0.0
        obj.hrg_pose_run_blend = 0.0
        obj.hrg_pose_talk_blend = 0.0
        obj.hrg_jaw_open = 0.0
        obj.hrg_eye_blink_l = 0.0
        obj.hrg_eye_blink_r = 0.0
        obj.hrg_brow_raise_l = 0.0
        obj.hrg_brow_raise_r = 0.0
        obj.hrg_mouth_smile_l = 0.0
        obj.hrg_mouth_smile_r = 0.0
        obj.hrg_eye_influence = 0.0
        obj.hrg_eye_target = None
        
        # Clear all pose transforms
        for pb in obj.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif pb.rotation_mode == 'AXIS_ANGLE':
                pb.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
            
        self.report({'INFO'}, "Pose Mixer and pose bones reset to defaults!")
        return {'FINISHED'}

class OBJECT_OT_bind_camera_to_frame(bpy.types.Operator):
    """Binds a camera to a specific timeline frame (Timeline camera cut)."""
    bl_idname = "object.bind_camera_to_frame"
    bl_label = "Bind Camera to Frame"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        cam_name = scene.hrg_active_camera
        
        if cam_name == 'NONE' or not cam_name:
            self.report({'WARNING'}, "No active camera selected!")
            return {'CANCELLED'}
            
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj or cam_obj.type != 'CAMERA':
            self.report({'WARNING'}, f"Camera '{cam_name}' not found!")
            return {'CANCELLED'}
            
        # Remove any existing marker at this frame to avoid duplicates
        for m in list(scene.timeline_markers):
            if m.frame == frame:
                scene.timeline_markers.remove(m)
                
        # Create a new timeline marker
        marker_name = f"Cut_{cam_name}_{frame}"
        marker = scene.timeline_markers.new(marker_name, frame=frame)
        marker.camera = cam_obj
        
        self.report({'INFO'}, f"Bound camera '{cam_name}' to frame {frame}")
        return {'FINISHED'}

class OBJECT_OT_delete_timeline_marker(bpy.types.Operator):
    """Deletes a timeline camera cut marker by name."""
    bl_idname = "object.delete_timeline_marker"
    bl_label = "Delete Marker"
    bl_options = {'REGISTER', 'UNDO'}
    
    marker_name: bpy.props.StringProperty() # type: ignore
    
    def execute(self, context):
        marker = context.scene.timeline_markers.get(self.marker_name)
        if marker:
            context.scene.timeline_markers.remove(marker)
            self.report({'INFO'}, f"Removed camera cut marker '{self.marker_name}'")
        return {'FINISHED'}

class OBJECT_OT_setup_dialogue_cameras(bpy.types.Operator):
    """Sets up classic Over-the-Shoulder (OTS) dialogue cameras for two characters or clones."""
    bl_idname = "object.setup_dialogue_cameras"
    bl_label = "Setup Dialogue Cameras"
    bl_options = {'REGISTER', 'UNDO'}
    
    actor_a: bpy.props.StringProperty() # type: ignore
    actor_b: bpy.props.StringProperty() # type: ignore
    
    def execute(self, context):
        scene = context.scene
        
        # Auto-detect actors if not explicitly set
        all_armatures = [o for o in scene.objects if o.type == 'ARMATURE']
        if len(all_armatures) < 2:
            self.report({'WARNING'}, "At least two character rigs or clones are required for OTS dialogue cameras!")
            return {'CANCELLED'}
            
        name_a = self.actor_a if self.actor_a and self.actor_a != 'NONE' else all_armatures[0].name
        name_b = self.actor_b if self.actor_b and self.actor_b != 'NONE' else all_armatures[1].name
        
        if name_a == name_b and len(all_armatures) >= 2:
            name_b = [o.name for o in all_armatures if o.name != name_a][0]
            
        obj_a = bpy.data.objects.get(name_a)
        obj_b = bpy.data.objects.get(name_b)
        
        if not obj_a or not obj_b or obj_a.type != 'ARMATURE' or obj_b.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select two valid character/clone armatures!")
            return {'CANCELLED'}
            
        from ..utils.naming import get_control_name
        
        context.view_layer.update()
        
        head_bone_a = obj_a.pose.bones.get(get_control_name("head"))
        head_bone_b = obj_b.pose.bones.get(get_control_name("head"))
        
        head_pos_a = (obj_a.matrix_world @ head_bone_a.head) if head_bone_a else (obj_a.matrix_world.translation + mathutils.Vector((0, 0, 1.6)))
        head_pos_b = (obj_b.matrix_world @ head_bone_b.head) if head_bone_b else (obj_b.matrix_world.translation + mathutils.Vector((0, 0, 1.6)))
        
        vec_ab = head_pos_b - head_pos_a
        if vec_ab.length < 0.001:
            vec_ab = mathutils.Vector((0, 1, 0))
        dir_ab = vec_ab.normalized()
        
        perp_ab = mathutils.Vector((-dir_ab.y, dir_ab.x, 0.0)).normalized()
        
        head_bone_name = get_control_name("head")
        
        # Setup OTS Camera A (behind A, looking at B)
        self.create_ots_camera(context, "Rig_Camera_OTS_A", obj_a, obj_b, head_pos_a, head_pos_b, dir_ab, perp_ab, head_bone_name)
        
        # Setup OTS Camera B (behind B, looking at A)
        self.create_ots_camera(context, "Rig_Camera_OTS_B", obj_b, obj_a, head_pos_b, head_pos_a, -dir_ab, -perp_ab, head_bone_name)
        
        # Force active camera
        scene.hrg_active_camera = "Rig_Camera_OTS_A"
        scene.camera = bpy.data.objects.get("Rig_Camera_OTS_A")
        
        self.report({'INFO'}, f"Created OTS Dialogue Cameras between '{obj_a.name}' and '{obj_b.name}'!")
        return {'FINISHED'}
        
    def create_ots_camera(self, context, cam_name, host_obj, target_obj, host_head, target_head, dir_vec, perp_vec, head_bone_name):
        scene = context.scene
        
        # Target empty on target_obj
        target_name = f"Cam_Target_{cam_name}"
        t_obj = bpy.data.objects.get(target_name)
        if not t_obj:
            t_obj = bpy.data.objects.new(target_name, None)
            t_obj.empty_display_type = 'SINGLE_ARROW'
            t_obj.empty_display_size = 0.1
            scene.collection.objects.link(t_obj)
            
        t_obj.parent = target_obj
        if head_bone_name in target_obj.pose.bones:
            t_obj.parent_type = 'BONE'
            t_obj.parent_bone = head_bone_name
        else:
            t_obj.parent_type = 'OBJECT'
        t_obj.matrix_parent_inverse.identity()
        t_obj.location = (0.0, 0.0, 0.0)
        
        # Create Camera
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            cam_data = bpy.data.cameras.new(f"{cam_name}_Data")
            cam_obj = bpy.data.objects.new(cam_name, cam_data)
            scene.collection.objects.link(cam_obj)
            
        cam_obj.parent = None
        cam_obj.matrix_parent_inverse.identity()
        
        # Track constraint targeting t_obj
        for c in list(cam_obj.constraints):
            if c.type == 'TRACK_TO':
                cam_obj.constraints.remove(c)
        track = cam_obj.constraints.new(type='TRACK_TO')
        track.target = t_obj
        track.track_axis = 'TRACK_NEGATIVE_Z'
        track.up_axis = 'UP_Y'
        
        # Calculate OTS camera position:
        cam_pos = host_head - dir_vec * 0.75 + perp_vec * 0.3 + mathutils.Vector((0, 0, 0.08))
        cam_obj.location = cam_pos
        cam_obj.parent = host_obj
        if head_bone_name in host_obj.pose.bones:
            cam_obj.parent_type = 'BONE'
            cam_obj.parent_bone = head_bone_name
            head_bone_host = host_obj.pose.bones.get(head_bone_name)
            head_world_mat = host_obj.matrix_world @ head_bone_host.matrix
            cam_obj.location = head_world_mat.inverted() @ cam_pos
        else:
            cam_obj.parent_type = 'OBJECT'
            cam_obj.location = host_obj.matrix_world.inverted() @ cam_pos
        cam_obj.matrix_parent_inverse.identity()

class OBJECT_OT_setup_auto_lighting(bpy.types.Operator):
    """Spawns a studio film 3-point lighting setup dynamically tracking the selected character or clone."""
    bl_idname = "object.setup_auto_lighting"
    bl_label = "Auto-Lighting Setup"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        
        if not obj or obj.type != 'ARMATURE':
            # Check scene active actor property
            actor_name = getattr(scene, "hrg_active_actor", None)
            if actor_name and actor_name != 'NONE' and actor_name in bpy.data.objects:
                obj = bpy.data.objects[actor_name]
            else:
                # Find first armature in scene
                for o in scene.objects:
                    if o.type == 'ARMATURE':
                        obj = o
                        break
                        
        if not obj:
            self.report({'WARNING'}, "No character armature or clone found for light targeting!")
            return {'CANCELLED'}
            
        context.view_layer.update()
        
        # Get head / chest world position
        from ..utils.naming import get_control_name
        head_bone = obj.pose.bones.get(get_control_name("head"))
        chest_bone = obj.pose.bones.get(get_control_name("chest"))
        
        if head_bone:
            target_pos = obj.matrix_world @ head_bone.head
        elif chest_bone:
            target_pos = obj.matrix_world @ chest_bone.head
        else:
            target_pos = obj.matrix_world.translation + mathutils.Vector((0, 0, 1.6))
            
        # Target empty for lights to track smoothly
        target_name = f"Light_Target_{obj.name}"
        t_obj = bpy.data.objects.get(target_name)
        if not t_obj:
            t_obj = bpy.data.objects.new(target_name, None)
            t_obj.empty_display_type = 'SPHERE'
            t_obj.empty_display_size = 0.08
            scene.collection.objects.link(t_obj)
            
        t_obj.location = target_pos
        t_obj.parent = obj
        if head_bone:
            t_obj.parent_type = 'BONE'
            t_obj.parent_bone = get_control_name("head")
            head_world_mat = obj.matrix_world @ head_bone.matrix
            t_obj.location = head_world_mat.inverted() @ target_pos
        else:
            t_obj.parent_type = 'OBJECT'
            t_obj.location = obj.matrix_world.inverted() @ target_pos
        t_obj.matrix_parent_inverse.identity()
        
        # Collection for lighting
        coll_name = f"Studio_Lights_{obj.name}"
        light_coll = bpy.data.collections.get(coll_name)
        if not light_coll:
            light_coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(light_coll)
            
        # Clear previous lights in this collection
        for l in list(light_coll.objects):
            if l.type == 'LIGHT':
                bpy.data.objects.remove(l, do_unlink=True)
                
        mood = scene.hrg_light_mood
        
        # Mood color & intensity palettes
        if mood == 'STUDIO':
            key_color = (1.0, 0.98, 0.95)
            fill_color = (0.85, 0.90, 1.0)
            rim_color = (1.0, 1.0, 1.0)
            key_power, fill_power, rim_power = 200.0, 75.0, 150.0
        elif mood == 'DRAMATIC':
            key_color = (1.0, 0.82, 0.65)
            fill_color = (0.55, 0.75, 1.0)
            rim_color = (1.0, 1.0, 1.0)
            key_power, fill_power, rim_power = 300.0, 40.0, 350.0
        elif mood == 'SUNNY':
            key_color = (1.0, 0.95, 0.80)
            fill_color = (0.60, 0.80, 1.0)
            rim_color = (1.0, 0.98, 0.90)
            key_power, fill_power, rim_power = 450.0, 120.0, 200.0
        elif mood == 'HORROR':
            key_color = (0.35, 0.75, 0.50)
            fill_color = (0.10, 0.15, 0.25)
            rim_color = (0.60, 0.60, 0.70)
            key_power, fill_power, rim_power = 150.0, 15.0, 160.0
        else: # NEON
            key_color = (1.0, 0.05, 0.65)
            fill_color = (0.05, 0.85, 1.0)
            rim_color = (1.0, 1.0, 1.0)
            key_power, fill_power, rim_power = 350.0, 180.0, 450.0
            
        rig_prefix = f"Rig_Light_{obj.name}_"
        
        # Spawn Key Light (Front-Right-High)
        self.create_studio_light(light_coll, f"{rig_prefix}Key", 'AREA', target_pos + mathutils.Vector((1.5, -1.8, 1.2)), t_obj, key_color, key_power, size=1.8)
        
        # Spawn Fill Light (Front-Left-Low)
        self.create_studio_light(light_coll, f"{rig_prefix}Fill", 'AREA', target_pos + mathutils.Vector((-2.0, -1.5, 0.4)), t_obj, fill_color, fill_power, size=2.5)
        
        # Spawn Rim / Hair Light (Behind-High)
        self.create_studio_light(light_coll, f"{rig_prefix}Rim", 'SPOT', target_pos + mathutils.Vector((-0.3, 2.0, 1.8)), t_obj, rim_color, rim_power, spot_size=0.6)
        
        self.report({'INFO'}, f"Generated Studio 3-Point Lighting ({mood}) for '{obj.name}' with live tracking!")
        return {'FINISHED'}
        
    def create_studio_light(self, coll, name, l_type, pos, target_empty, color, power, size=1.5, spot_size=0.6):
        l_data = bpy.data.lights.new(name=f"{name}_Data", type=l_type)
        l_data.color = color
        
        if l_type == 'AREA':
            l_data.energy = power
            l_data.size = size
        elif l_type == 'SPOT':
            l_data.energy = power * 2.0
            l_data.spot_size = spot_size
            l_data.show_cone = True
        else:
            l_data.energy = power
            
        l_obj = bpy.data.objects.new(name=name, object_data=l_data)
        coll.objects.link(l_obj)
        l_obj.location = pos
        
        # Dynamic Track To target empty
        track = l_obj.constraints.new(type='TRACK_TO')
        track.target = target_empty
        track.track_axis = 'TRACK_NEGATIVE_Z'
        track.up_axis = 'UP_Y'

class OBJECT_OT_apply_face_expression(bpy.types.Operator):
    """Applies a facial expression preset dynamically to the character's facial joints."""
    bl_idname = "object.apply_face_expression"
    bl_label = "Apply Face Expression"
    bl_options = {'REGISTER', 'UNDO'}
    
    expression: bpy.props.EnumProperty( # type: ignore
        items=[
            ('NEUTRAL', "Neutral", "Reset face to rest pose"),
            ('HAPPY', "Happy", "Smile and raised brows"),
            ('ANGRY', "Angry", "Frowning brows and open snarling jaw"),
            ('SAD', "Sad", "Inward tilted brows and downcast mouth corner"),
            ('SURPRISED', "Surprised", "Raised brows and open wide mouth"),
            ('SMIRK', "Smirk", "One-sided smirk smile")
        ]
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the active character armature rig!")
            return {'CANCELLED'}
            
        from ..utils.naming import get_org_name, get_control_name
        
        pose_bones = obj.pose.bones
        
        # Reset all facial ORG bones first
        face_prefixes = ["eyebrow.01", "eyebrow.02", "eyebrow.03", "cheek", "lip.corner"]
        for prefix in face_prefixes:
            for side in [".L", ".R"]:
                org_name = get_org_name(f"{prefix}{side}")
                pb = pose_bones.get(org_name)
                if pb:
                    pb.location = (0.0, 0.0, 0.0)
                    pb.rotation_euler = (0.0, 0.0, 0.0)
                    
        # Reset jaw and eyelids
        obj.hrg_jaw_open = 0.0
        pb_eyes = pose_bones.get(get_control_name("eyes_look"))
        if pb_eyes:
            pb_eyes["eye_close.L"] = 0.0
            pb_eyes["eye_close.R"] = 0.0
            
        exp = self.expression
        scale = 1.0
        
        # Apply specific presets
        if exp == 'HAPPY':
            # Lips raised up and out
            for side, mult in [(".L", 1.0), (".R", -1.0)]:
                pb_lip_corner = pose_bones.get(get_org_name(f"lip.corner{side}"))
                pb_cheek = pose_bones.get(get_org_name(f"cheek{side}"))
                if pb_lip_corner:
                    pb_lip_corner.location.z = 0.007 * scale
                    pb_lip_corner.location.x = 0.004 * scale * mult
                if pb_cheek:
                    pb_cheek.location.z = 0.005 * scale
                    
            # Brows raised slightly
            for side in [".L", ".R"]:
                pb_brow1 = pose_bones.get(get_org_name(f"eyebrow.01{side}"))
                if pb_brow1:
                    pb_brow1.location.z = 0.004 * scale
                    
        elif exp == 'ANGRY':
            # Brows lowered and pulled inward
            for side, mult in [(".L", 1.0), (".R", -1.0)]:
                pb_brow1 = pose_bones.get(get_org_name(f"eyebrow.01{side}"))
                pb_brow2 = pose_bones.get(get_org_name(f"eyebrow.02{side}"))
                if pb_brow1:
                    pb_brow1.location.z = -0.008 * scale
                    pb_brow1.location.x = 0.004 * scale * mult
                if pb_brow2:
                    pb_brow2.location.z = -0.005 * scale
                    
            # Eyelids slightly squinting
            if pb_eyes:
                pb_eyes["eye_close.L"] = 0.25
                pb_eyes["eye_close.R"] = 0.25
                
            # Lips open snarling
            for side in [".L", ".R"]:
                pb_lip_corner = pose_bones.get(get_org_name(f"lip.corner{side}"))
                if pb_lip_corner:
                    pb_lip_corner.location.z = 0.003 * scale
            obj.hrg_jaw_open = 0.15
            
        elif exp == 'SAD':
            # Brows inner corner tilted up and together
            for side, mult in [(".L", 1.0), (".R", -1.0)]:
                pb_brow1 = pose_bones.get(get_org_name(f"eyebrow.01{side}"))
                if pb_brow1:
                    pb_brow1.location.z = 0.008 * scale
                    pb_brow1.location.x = 0.003 * scale * mult
                    pb_brow1.rotation_euler.y = 0.15 * mult
                    
            # Lip corner lowered
            for side in [".L", ".R"]:
                pb_lip_corner = pose_bones.get(get_org_name(f"lip.corner{side}"))
                if pb_lip_corner:
                    pb_lip_corner.location.z = -0.006 * scale
            if pb_eyes:
                pb_eyes["eye_close.L"] = 0.18
                pb_eyes["eye_close.R"] = 0.18
                
        elif exp == 'SURPRISED':
            # Brows high
            for side in [".L", ".R"]:
                for i in range(1, 4):
                    pb_brow = pose_bones.get(get_org_name(f"eyebrow.0{i}{side}"))
                    if pb_brow:
                        pb_brow.location.z = 0.015 * scale
            obj.hrg_jaw_open = 0.5
            
        elif exp == 'SMIRK':
            # Left corner pulled high and wide, right corner flat
            pb_lip_corner_l = pose_bones.get(get_org_name("lip.corner.L"))
            pb_cheek_l = pose_bones.get(get_org_name("cheek.L"))
            if pb_lip_corner_l:
                pb_lip_corner_l.location.z = 0.014 * scale
                pb_lip_corner_l.location.x = 0.008 * scale
            if pb_cheek_l:
                pb_cheek_l.location.z = 0.007 * scale
                
            pb_lip_corner_r = pose_bones.get(get_org_name("lip.corner.R"))
            if pb_lip_corner_r:
                pb_lip_corner_r.location.z = -0.002 * scale
                
            pb_brow_l = pose_bones.get(get_org_name("eyebrow.01.L"))
            if pb_brow_l:
                pb_brow_l.location.z = 0.005 * scale
                
        # Force redraw updates by setting pose mixer (which triggers viewport redraws)
        obj.hrg_jaw_open = obj.hrg_jaw_open
        
        self.report({'INFO'}, f"Facial expression set to: {exp}")
        return {'FINISHED'}

class OBJECT_OT_apply_body_pose(bpy.types.Operator):
    """Applies a starting body pose preset dynamically to the rig controllers."""
    bl_idname = "object.apply_body_pose"
    bl_label = "Apply Body Pose"
    bl_options = {'REGISTER', 'UNDO'}
    
    pose: bpy.props.EnumProperty( # type: ignore
        items=[
            ('STAND_NEUTRAL', "Stand Neutral", "Reset armature to standard stand T-pose"),
            ('CROSS_ARMS', "Cross Arms", "IK arms crossed over chest"),
            ('SIT_CHAIR', "Sit on Chair", "Sits character flat on hips, knees bent"),
            ('HOLD_PHONE', "Hold Phone", "Right hand holds a phone up, left hand dangles"),
            ('TALK_GESTURE', "Dialogue Gesture", "Hands open in front conversing")
        ],
        default='STAND_NEUTRAL'
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the active character armature rig!")
            return {'CANCELLED'}
            
        from ..utils.naming import get_control_name
        
        pose_bones = obj.pose.bones
        
        # Reset all IK / FK / spine controllers first
        for pb in pose_bones:
            if pb.name.startswith("CTRL-"):
                pb.location = (0.0, 0.0, 0.0)
                if pb.rotation_mode == 'QUATERNION':
                    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                else:
                    pb.rotation_euler = (0.0, 0.0, 0.0)
                pb.scale = (1.0, 1.0, 1.0)
                
        # Retrieve switches and defaults
        for side in [".L", ".R"]:
            pb_hand_ik = pose_bones.get(get_control_name(f"hand_IK{side}"))
            pb_foot_ik = pose_bones.get(get_control_name(f"foot_IK{side}"))
            if pb_hand_ik:
                pb_hand_ik.hrg_ik_fk = 1.0
            if pb_foot_ik:
                pb_foot_ik.hrg_ik_fk = 1.0
                
        pose_name = self.pose
        scale = 1.0
        
        # Calculate dynamic size scale based on pelvis/leg height
        try:
            pelvis_bone = obj.data.bones.get(get_control_name("pelvis"))
            foot_l_bone = obj.data.bones.get(get_control_name("foot_IK.L"))
            if pelvis_bone and foot_l_bone:
                leg_length = (foot_l_bone.head - pelvis_bone.head).length
                scale = max(0.1, min(3.0, leg_length / 0.90))
        except Exception:
            pass
            
        # Apply specific body pose values
        if pose_name == 'CROSS_ARMS':
            pb_lh = pose_bones.get(get_control_name("hand_IK.L"))
            if pb_lh:
                pb_lh.location = (0.15 * scale, 0.18 * scale, -0.22 * scale)
                pb_lh.rotation_mode = 'XYZ'
                pb_lh.rotation_euler = (0.5, 0.2, -1.0)
                
            pb_rh = pose_bones.get(get_control_name("hand_IK.R"))
            if pb_rh:
                pb_rh.location = (-0.15 * scale, 0.20 * scale, -0.25 * scale)
                pb_rh.rotation_mode = 'XYZ'
                pb_rh.rotation_euler = (0.5, -0.2, 1.0)
                
        elif pose_name == 'SIT_CHAIR':
            pb_pelvis = pose_bones.get(get_control_name("pelvis"))
            if pb_pelvis:
                pb_pelvis.location = (0.0, -0.22 * scale, -0.45 * scale)
                
            pb_lf = pose_bones.get(get_control_name("foot_IK.L"))
            pb_rf = pose_bones.get(get_control_name("foot_IK.R"))
            if pb_lf:
                pb_lf.location = (0.0, 0.25 * scale, 0.43 * scale)
            if pb_rf:
                pb_rf.location = (0.0, 0.25 * scale, 0.43 * scale)
                
            pb_lh = pose_bones.get(get_control_name("hand_IK.L"))
            pb_rh = pose_bones.get(get_control_name("hand_IK.R"))
            if pb_lh:
                pb_lh.location = (0.08 * scale, 0.22 * scale, -0.28 * scale)
                pb_lh.rotation_mode = 'XYZ'
                pb_lh.rotation_euler = (0.3, 0.0, -1.5)
            if pb_rh:
                pb_rh.location = (-0.08 * scale, 0.22 * scale, -0.28 * scale)
                pb_rh.rotation_mode = 'XYZ'
                pb_rh.rotation_euler = (0.3, 0.0, 1.5)
                
        elif pose_name == 'HOLD_PHONE':
            pb_rh = pose_bones.get(get_control_name("hand_IK.R"))
            if pb_rh:
                pb_rh.location = (-0.12 * scale, 0.28 * scale, 0.08 * scale)
                pb_rh.rotation_mode = 'XYZ'
                pb_rh.rotation_euler = (-0.4, -0.3, 1.2)
                
            pb_rfingers = pose_bones.get(get_control_name("fingers.R"))
            if pb_rfingers:
                pb_rfingers.hrg_grasp = 0.95
                pb_rfingers.hrg_thumb = 0.5
                
        elif pose_name == 'TALK_GESTURE':
            pb_lh = pose_bones.get(get_control_name("hand_IK.L"))
            if pb_lh:
                pb_lh.location = (0.12 * scale, 0.24 * scale, -0.10 * scale)
                pb_lh.rotation_mode = 'XYZ'
                pb_lh.rotation_euler = (0.5, 0.0, -1.2)
                
            pb_rh = pose_bones.get(get_control_name("hand_IK.R"))
            if pb_rh:
                pb_rh.location = (-0.14 * scale, 0.26 * scale, -0.05 * scale)
                pb_rh.rotation_mode = 'XYZ'
                pb_rh.rotation_euler = (0.6, 0.2, 1.0)
                
        # Force initial updates of constraint influences
        for side in [".L", ".R"]:
            for part in ["hand_IK", "foot_IK"]:
                pb_ik = pose_bones.get(get_control_name(f"{part}{side}"))
                if pb_ik:
                    pb_ik.hrg_ik_fk = pb_ik.hrg_ik_fk
                    
        self.report({'INFO'}, f"Body pose preset applied: {pose_name}")
        return {'FINISHED'}

class OBJECT_OT_delete_active_action(bpy.types.Operator):
    """Permanently deletes the active animation Action from the blend file and Action Editor."""
    bl_idname = "object.delete_active_action"
    bl_label = "Delete Active Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        action = None
        
        if context.active_object and context.active_object.animation_data and context.active_object.animation_data.action:
            action = context.active_object.animation_data.action
        elif getattr(scene, "hrg_scene_action", 'NONE') != 'NONE':
            action = bpy.data.actions.get(scene.hrg_scene_action)
        elif getattr(scene, "hrg_anim_transfer_action", 'ACTIVE') not in ['ACTIVE', 'NONE']:
            action = bpy.data.actions.get(scene.hrg_anim_transfer_action)
        elif len(bpy.data.actions) > 0:
            action = bpy.data.actions[0]
            
        if not action:
            self.report({'WARNING'}, "No actions found in the blend file to delete!")
            return {'CANCELLED'}
            
        action_name = action.name
        
        # 1. Unlink action from all objects safely
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action == action:
                try:
                    obj.animation_data.action = None
                except Exception:
                    pass
                    
        # 2. Clear fake user so it can be unlinked
        action.use_fake_user = False
        
        # 3. Completely remove action from Blender's database
        try:
            bpy.data.actions.remove(action, do_unlink=True)
            self.report({'INFO'}, f"Permanently deleted Action '{action_name}' from blend file!")
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete action: {e}")
            return {'CANCELLED'}
            
        # 4. Auto-advance dropdown to next available action
        remaining = [a.name for a in bpy.data.actions]
        next_act = remaining[0] if remaining else 'NONE'
        if getattr(scene, "hrg_scene_action", None) == action_name:
            scene.hrg_scene_action = next_act
        if getattr(scene, "hrg_anim_transfer_action", None) == action_name:
            scene.hrg_anim_transfer_action = next_act if remaining else 'ACTIVE'
            
        return {'FINISHED'}

class OBJECT_OT_delete_selected_action(bpy.types.Operator):
    """Permanently deletes the selected Action from the blend file and unlinks it from all characters."""
    bl_idname = "object.delete_selected_action"
    bl_label = "Delete Selected Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_name: bpy.props.StringProperty(name="Action Name", default="") # type: ignore
    action_type: bpy.props.EnumProperty( # type: ignore
        name="Target Source",
        items=[
            ('AUTO', "Auto", "Detect from dropdown or active character"),
            ('SAVED', "Saved Action", "Delete action selected in Saved Action dropdown"),
            ('TRANSFER', "Transfer Action", "Delete action selected in Transfer Action dropdown"),
            ('ACTIVE', "Active Action", "Delete active object's current action"),
        ],
        default='AUTO'
    )
    
    def execute(self, context):
        scene = context.scene
        target_action = None
        target_name = self.action_name
        
        if not target_name:
            if self.action_type == 'TRANSFER':
                transfer_act = getattr(scene, "hrg_anim_transfer_action", 'ACTIVE')
                if transfer_act != 'ACTIVE' and transfer_act != 'NONE':
                    target_name = transfer_act
                else:
                    src_obj = getattr(scene, "hrg_anim_source_rig", None) or context.active_object
                    if src_obj and src_obj.animation_data and src_obj.animation_data.action:
                        target_action = src_obj.animation_data.action
            elif self.action_type == 'SAVED':
                saved_act = getattr(scene, "hrg_scene_action", 'NONE')
                if saved_act and saved_act != 'NONE':
                    target_name = saved_act
                elif context.active_object and context.active_object.animation_data and context.active_object.animation_data.action:
                    target_action = context.active_object.animation_data.action
            else: # AUTO
                saved_act = getattr(scene, "hrg_scene_action", 'NONE')
                transfer_act = getattr(scene, "hrg_anim_transfer_action", 'ACTIVE')
                if saved_act and saved_act != 'NONE':
                    target_name = saved_act
                elif transfer_act and transfer_act != 'ACTIVE' and transfer_act != 'NONE':
                    target_name = transfer_act
                elif context.active_object and context.active_object.animation_data and context.active_object.animation_data.action:
                    target_action = context.active_object.animation_data.action
                    
        if not target_action and target_name:
            target_action = bpy.data.actions.get(target_name)
            
        # Ultimate fallback: if nothing was explicitly chosen in dropdown, pick active rig action or any remaining action!
        if not target_action:
            if context.active_object and context.active_object.animation_data and context.active_object.animation_data.action:
                target_action = context.active_object.animation_data.action
            elif len(bpy.data.actions) > 0:
                target_action = bpy.data.actions[0]
            
        if not target_action:
            self.report({'WARNING'}, "No Action found in the blend file to delete!")
            return {'CANCELLED'}
            
        deleted_name = target_action.name
        
        # 1. Safely unlink this action from all objects in the scene
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action == target_action:
                try:
                    obj.animation_data.action = None
                except Exception:
                    pass
                    
        # 2. Clear fake user protection
        target_action.use_fake_user = False
        
        # 3. Remove action permanently from blend file database
        try:
            bpy.data.actions.remove(target_action, do_unlink=True)
            self.report({'INFO'}, f"Deleted Action '{deleted_name}' permanently from the blend file!")
        except Exception as e:
            self.report({'WARNING'}, f"Could not remove action '{deleted_name}': {e}")
            return {'CANCELLED'}
            
        # 4. Auto-advance dropdowns to the next available action so the user can keep deleting without re-selecting
        remaining = [a.name for a in bpy.data.actions]
        next_act = remaining[0] if remaining else 'NONE'
        
        if getattr(scene, "hrg_scene_action", None) == deleted_name or getattr(scene, "hrg_scene_action", 'NONE') == 'NONE':
            scene.hrg_scene_action = next_act
            
        if getattr(scene, "hrg_anim_transfer_action", None) == deleted_name or getattr(scene, "hrg_anim_transfer_action", 'ACTIVE') == 'NONE':
            scene.hrg_anim_transfer_action = next_act if remaining else 'ACTIVE'
            
        return {'FINISHED'}

class OBJECT_OT_purge_unused_actions(bpy.types.Operator):
    """Purges all unused test Actions and orphan animations from the blend file and Action Editor."""
    bl_idname = "object.purge_unused_actions"
    bl_label = "Purge Unused Actions"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        removed_count = 0
        for act in list(bpy.data.actions):
            # Check if this action is not actively assigned to any object
            is_used_by_obj = any(o.animation_data and o.animation_data.action == act for o in bpy.data.objects)
            if not is_used_by_obj:
                try:
                    act.use_fake_user = False
                    bpy.data.actions.remove(act, do_unlink=True)
                    removed_count += 1
                except Exception:
                    pass
        
        self.report({'INFO'}, f"Purged {removed_count} unused test Actions from Action Editor!")
        return {'FINISHED'}

class OBJECT_OT_smooth_fcurves(bpy.types.Operator):
    """Smooths and auto-clamps all animation curves on the character to eliminate sudden speed spikes and jerky motion."""
    bl_idname = "object.smooth_fcurves"
    bl_label = "Smooth All Keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No active animation action found on the selected object!")
            return {'CANCELLED'}
            
        action = obj.animation_data.action
        fcurves = get_action_fcurves(action)
        
        smoothed_count = 0
        for fc in fcurves:
            # Set handle types to AUTO_CLAMPED to prevent overshooting
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'
                smoothed_count += 1
                
        self.report({'INFO'}, f"Smoothed {len(fcurves)} animation curves ({smoothed_count} keyframes) for seamless motion!")
        return {'FINISHED'}

class OBJECT_OT_scale_animation_timing(bpy.types.Operator):
    """Scales the timing of all keyframes uniformly to make the animation faster or slower."""
    bl_idname = "object.scale_animation_timing"
    bl_label = "Scale Timing"
    bl_options = {'REGISTER', 'UNDO'}
    
    factor: bpy.props.FloatProperty( # type: ignore
        name="Speed Multiplier",
        description="Factor to scale timing (e.g., 2.0 = 2x faster / half duration, 0.5 = 2x slower / double duration)",
        default=1.0,
        min=0.1,
        max=10.0
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No active animation action found!")
            return {'CANCELLED'}
            
        action = obj.animation_data.action
        fcurves = get_action_fcurves(action)
        
        # Factor < 1.0 means slower (more frames), factor > 1.0 means faster (fewer frames)
        time_scale = 1.0 / self.factor
        pivot_frame = context.scene.frame_start
        
        for fc in fcurves:
            for kp in fc.keyframe_points:
                old_x = kp.co.x
                new_x = pivot_frame + (old_x - pivot_frame) * time_scale
                kp.co.x = new_x
                kp.handle_left.x = pivot_frame + (kp.handle_left.x - pivot_frame) * time_scale
                kp.handle_right.x = pivot_frame + (kp.handle_right.x - pivot_frame) * time_scale
                
        # Update timeline end frame
        old_duration = context.scene.frame_end - context.scene.frame_start
        context.scene.frame_end = int(context.scene.frame_start + old_duration * time_scale)
        context.view_layer.update()
        
        self.report({'INFO'}, f"Scaled animation timing by {self.factor}x!")
        return {'FINISHED'}

def retarget_rig_internal_constraints(arm_obj, orig_arm_obj=None):
    """
    Retargets all bone constraints (IK, Copy Transforms, Copy Location/Rotation, TrackTo, etc.)
    and child mesh Armature modifiers so the rig's internal constraints point to itself
    rather than pointing to another/original armature.
    """
    if not arm_obj or arm_obj.type != 'ARMATURE':
        return 0
        
    retargeted_count = 0
    
    # 1. Pose Bones Constraints
    for pb in arm_obj.pose.bones:
        for c in pb.constraints:
            # Target
            if hasattr(c, "target") and c.target:
                if c.target != arm_obj and c.target.type == 'ARMATURE':
                    c.target = arm_obj
                    retargeted_count += 1
                        
            # Pole target for IK
            if hasattr(c, "pole_target") and c.pole_target:
                if c.pole_target != arm_obj and c.pole_target.type == 'ARMATURE':
                    c.pole_target = arm_obj
                    retargeted_count += 1
                    
    # 2. Child Meshes and all scene meshes rigged to this armature or parented to it
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if obj.parent == arm_obj or obj.name.startswith(arm_obj.name):
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE' and mod.object != arm_obj:
                        mod.object = arm_obj
                        retargeted_count += 1
            elif orig_arm_obj and obj.parent != orig_arm_obj:
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == orig_arm_obj:
                        mod.object = arm_obj
                        obj.parent = arm_obj
                        retargeted_count += 1
                            
    # 3. Trigger pose constraint evaluation & IK/FK blend influences
    from ..utils.naming import get_org_name
    for pb in arm_obj.pose.bones:
        if hasattr(pb, "hrg_ik_fk"):
            val = pb.hrg_ik_fk
            side = ".L" if pb.name.endswith(".L") else ".R"
            is_arm = "hand" in pb.name
            chain = [f"upper_arm{side}", f"forearm{side}", f"hand{side}"] if is_arm else [f"thigh{side}", f"shin{side}", f"foot{side}", f"toe{side}"]
            for bone_base in chain:
                org_name = get_org_name(bone_base)
                pb_org = arm_obj.pose.bones.get(org_name)
                if pb_org:
                    for c in pb_org.constraints:
                        if c.name in ["Copy_FK_Loc", "Copy_FK_Rot"]:
                            c.influence = 1.0 - val
                        elif c.name in ["Copy_IK_Loc", "Copy_IK_Rot"]:
                            c.influence = val

    return retargeted_count

class OBJECT_OT_fix_clone_constraints(bpy.types.Operator):
    """Retargets and fixes all internal bone constraints on the selected character rig so it moves independently."""
    bl_idname = "object.fix_clone_constraints"
    bl_label = "Fix Rig Constraints"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a character Armature rig to fix!")
            return {'CANCELLED'}
            
        count = retarget_rig_internal_constraints(obj)
        context.view_layer.update()
        self.report({'INFO'}, f"Relinked {count} internal bone constraints & modifiers on '{obj.name}'!")
        return {'FINISHED'}

def get_scene_actions_items(self, context):
    """Dynamic enum of all animation actions available in the blend file."""
    items = [('NONE', "Select Saved Action", "No action selected")]
    for act in bpy.data.actions:
        fcurves = get_action_fcurves(act)
        valid_ranges = [fc.range() for fc in fcurves if len(fc.keyframe_points) > 0]
        if valid_ranges:
            min_f = int(min(r[0] for r in valid_ranges))
            max_f = int(max(r[1] for r in valid_ranges))
            duration = max_f - min_f + 1
            items.append((act.name, f"{act.name} ({duration}f)", f"Apply action '{act.name}' (Frames {min_f}-{max_f})"))
        else:
            items.append((act.name, act.name, f"Apply action '{act.name}'"))
    return items

class OBJECT_OT_apply_saved_action(bpy.types.Operator):
    """Applies a saved Action from the scene to the active character rig or clone, preserving world position."""
    bl_idname = "object.apply_saved_action"
    bl_label = "Apply Saved Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    make_copy: bpy.props.BoolProperty( # type: ignore
        name="Make Independent Copy",
        description="Creates an independent copy of the action for this character so edits don't overwrite the original",
        default=False
    )
    
    preserve_location: bpy.props.BoolProperty( # type: ignore
        name="Preserve Character Position",
        description="Preserves the character's current location in the scene so it doesn't snap back to origin",
        default=True
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a character Armature rig first!")
            return {'CANCELLED'}
            
        scene = context.scene
        action_name = getattr(scene, "hrg_scene_action", 'NONE')
        if action_name == 'NONE' or not action_name:
            self.report({'WARNING'}, "Please select an Action from the 'Saved Action' dropdown first!")
            return {'CANCELLED'}
            
        source_action = bpy.data.actions.get(action_name)
        if not source_action:
            self.report({'WARNING'}, f"Action '{action_name}' not found in blend file!")
            return {'CANCELLED'}
            
        # Relink any stray constraints so rig evaluates its own bones
        retarget_rig_internal_constraints(obj)
        
        current_loc = obj.location.copy()
        
        if not obj.animation_data:
            obj.animation_data_create()
            
        if self.make_copy:
            target_action = source_action.copy()
            target_action.name = f"{obj.name}_{source_action.name}"
            target_action.use_fake_user = True
        else:
            target_action = source_action
            target_action.use_fake_user = True
            
        # Unmute any muted tracks
        if obj.animation_data.nla_tracks:
            for track in obj.animation_data.nla_tracks:
                track.mute = True
                
        assign_action_to_rig(obj, target_action)
        
        # If preserving position, offset any object location curves so clone stays at its location
        if self.preserve_location and self.make_copy:
            fcurves = get_action_fcurves(target_action)
            obj_loc_fcs = [fc for fc in fcurves if fc.data_path == "location"]
            if obj_loc_fcs:
                first_key_loc = mathutils.Vector((0.0, 0.0, 0.0))
                for fc in obj_loc_fcs:
                    if len(fc.keyframe_points) > 0:
                        first_key_loc[fc.array_index] = fc.keyframe_points[0].co[1]
                delta = current_loc - first_key_loc
                for fc in obj_loc_fcs:
                    offset = delta[fc.array_index]
                    for kp in fc.keyframe_points:
                        kp.co[1] += offset
                        kp.handle_left[1] += offset
                        kp.handle_right[1] += offset
            else:
                obj.location = current_loc
        else:
            obj.location = current_loc
                
        # Update timeline range if enabled
        if getattr(scene, "hrg_set_timeline_range", True):
            fcurves = get_action_fcurves(target_action)
            valid_ranges = [fc.range() for fc in fcurves if len(fc.keyframe_points) > 0]
            if valid_ranges:
                scene.frame_start = int(min(r[0] for r in valid_ranges))
                scene.frame_end = int(max(r[1] for r in valid_ranges))
                
        # Force evaluation & update
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='POSE')
            context.view_layer.update()
            
        context.view_layer.update()
        self.report({'INFO'}, f"Applied Action '{target_action.name}' to '{obj.name}' successfully!")
        return {'FINISHED'}

class OBJECT_OT_copy_animation_from_actor(bpy.types.Operator):
    """Copies the full animation action from another actor/character to the active character rig."""
    bl_idname = "object.copy_animation_from_actor"
    bl_label = "Copy Animation From Actor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        target_obj = context.active_object
        if not target_obj or target_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the target character Armature first!")
            return {'CANCELLED'}
            
        scene = context.scene
        src_actor_name = getattr(scene, "hrg_source_actor_to_copy", 'NONE')
        if src_actor_name == 'NONE' or not src_actor_name:
            self.report({'WARNING'}, "Please select a Source Actor to copy animation from!")
            return {'CANCELLED'}
            
        src_obj = bpy.data.objects.get(src_actor_name)
        if not src_obj or src_obj.type != 'ARMATURE':
            self.report({'WARNING'}, f"Source Actor '{src_actor_name}' is not a valid armature!")
            return {'CANCELLED'}
            
        if src_obj == target_obj:
            self.report({'WARNING'}, "Source Actor and Target Actor are the same object!")
            return {'CANCELLED'}
            
        if not src_obj.animation_data or not src_obj.animation_data.action:
            self.report({'WARNING'}, f"Source Actor '{src_obj.name}' has no active animation action to copy!")
            return {'CANCELLED'}
            
        # Relink target constraints
        retarget_rig_internal_constraints(target_obj, src_obj)
        
        current_loc = target_obj.location.copy()
        src_action = src_obj.animation_data.action
        
        use_copy = getattr(scene, "hrg_anim_make_copy", False)
        if use_copy:
            cloned_action = src_action.copy()
            cloned_action.name = f"{target_obj.name}_{src_action.name}"
            cloned_action.use_fake_user = True
        else:
            cloned_action = src_action
            cloned_action.use_fake_user = True
        
        if not target_obj.animation_data:
            target_obj.animation_data_create()
            
        if target_obj.animation_data.nla_tracks:
            for track in target_obj.animation_data.nla_tracks:
                track.mute = True
                
        assign_action_to_rig(target_obj, cloned_action)
        
        # Offset object location curves so target stays at its position
        fcurves = get_action_fcurves(cloned_action)
        if use_copy:
            obj_loc_fcs = [fc for fc in fcurves if fc.data_path == "location"]
            if obj_loc_fcs:
                first_key_loc = src_obj.location.copy()
                delta = current_loc - first_key_loc
                for fc in obj_loc_fcs:
                    offset = delta[fc.array_index]
                    for kp in fc.keyframe_points:
                        kp.co[1] += offset
                        kp.handle_left[1] += offset
                        kp.handle_right[1] += offset
            else:
                target_obj.location = current_loc
        else:
            target_obj.location = current_loc
            
        if getattr(scene, "hrg_set_timeline_range", True):
            valid_ranges = [fc.range() for fc in fcurves if len(fc.keyframe_points) > 0]
            if valid_ranges:
                scene.frame_start = int(min(r[0] for r in valid_ranges))
                scene.frame_end = int(max(r[1] for r in valid_ranges))
                
        # Force evaluation & update
        for o in context.selected_objects:
            o.select_set(False)
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='POSE')
            context.view_layer.update()
            
        context.view_layer.update()
        self.report({'INFO'}, f"Copied animation from '{src_obj.name}' to '{target_obj.name}' successfully!")
        return {'FINISHED'}

class OBJECT_OT_save_custom_action(bpy.types.Operator):
    """Saves and stashes the current character's animation as a named Action in the blend file with Fake User."""
    bl_idname = "object.save_custom_action"
    bl_label = "Save Current Animation as Action"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_name: bpy.props.StringProperty( # type: ignore
        name="Action Name",
        description="Name to give the saved action",
        default="Custom_Pose_Action"
    )
    
    def invoke(self, context, event):
        obj = context.active_object
        if obj and obj.animation_data and obj.animation_data.action:
            self.action_name = obj.animation_data.action.name
        elif obj:
            self.action_name = f"{obj.name}_CustomAction"
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No active animation action found on the selected character!")
            return {'CANCELLED'}
            
        action = obj.animation_data.action
        if self.action_name:
            action.name = self.action_name
        action.use_fake_user = True
        
        context.scene.hrg_scene_action = action.name
        self.report({'INFO'}, f"Saved Action '{action.name}' with Fake User protection!")
        return {'FINISHED'}

class OBJECT_OT_import_actions_from_blend(bpy.types.Operator, ImportHelper):
    """Imports and appends saved animation Actions from another Blender project (.blend file) into your Action Library."""
    bl_idname = "object.import_actions_from_blend"
    bl_label = "Import Actions from Project"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty( # type: ignore
        name="Blender File",
        description="Select the Blender file (.blend) containing saved animations",
        subtype='FILE_PATH'
    )
    
    filter_glob: bpy.props.StringProperty( # type: ignore
        default="*.blend",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    apply_to_active: bpy.props.BoolProperty( # type: ignore
        name="Apply First Action to Active Character",
        description="Immediately assigns the first imported action to the currently selected character",
        default=True
    )
    
    def execute(self, context):
        if not self.filepath or not self.filepath.lower().endswith(".blend"):
            self.report({'WARNING'}, "Please select a valid Blender project file (.blend)!")
            return {'CANCELLED'}
            
        try:
            with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
                if not data_from.actions:
                    self.report({'WARNING'}, f"No saved actions found in '{os.path.basename(self.filepath)}'!")
                    return {'CANCELLED'}
                data_to.actions = data_from.actions
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load actions from '{os.path.basename(self.filepath)}': {e}")
            return {'CANCELLED'}
            
        imported_actions = [a for a in data_to.actions if a is not None]
        if not imported_actions:
            self.report({'WARNING'}, "No actions were imported!")
            return {'CANCELLED'}
            
        for act in imported_actions:
            act.use_fake_user = True
            
        # Set dropdown to first imported action
        first_act = imported_actions[0]
        context.scene.hrg_scene_action = first_act.name
        context.scene.hrg_anim_transfer_action = first_act.name
        
        # Apply to active character if selected
        obj = context.active_object
        if self.apply_to_active and obj and obj.type == 'ARMATURE' and first_act:
            assign_action_to_rig(obj, first_act)
            retarget_rig_internal_constraints(obj)
            self.report({'INFO'}, f"Successfully imported {len(imported_actions)} actions and applied '{first_act.name}' to '{obj.name}'!")
        else:
            self.report({'INFO'}, f"Successfully imported {len(imported_actions)} actions into Action Library!")
            
        return {'FINISHED'}

def get_transfer_action_items(self, context):
    """Dynamic enum of actions available for transfer, prioritizing the source rig's action."""
    items = [('ACTIVE', "★ Active Action on Source Rig", "Transfer whatever animation is currently active on the source character")]
    for act in bpy.data.actions:
        fcurves = get_action_fcurves(act)
        valid_ranges = [fc.range() for fc in fcurves if len(fc.keyframe_points) > 0]
        if valid_ranges:
            min_f = int(min(r[0] for r in valid_ranges))
            max_f = int(max(r[1] for r in valid_ranges))
            duration = max_f - min_f + 1
            items.append((act.name, f"{act.name} ({duration}f: {min_f}-{max_f})", f"Transfer action '{act.name}'"))
        else:
            items.append((act.name, act.name, f"Transfer action '{act.name}'"))
    return items

class OBJECT_OT_pick_anim_source_rig(bpy.types.Operator):
    """Picks the currently selected 3D Viewport armature or character as the Source for animation transfer."""
    bl_idname = "object.pick_anim_source_rig"
    bl_label = "Pick Source Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        picked_obj = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            picked_obj = context.active_object
        elif context.active_object and context.active_object.parent and context.active_object.parent.type == 'ARMATURE':
            picked_obj = context.active_object.parent
            
        if not picked_obj:
            for o in context.selected_objects:
                if o.type == 'ARMATURE':
                    picked_obj = o
                    break
                elif o.parent and o.parent.type == 'ARMATURE':
                    picked_obj = o.parent
                    break
                    
        if not picked_obj:
            self.report({'WARNING'}, "Please select a character Armature rig in the 3D Viewport first!")
            return {'CANCELLED'}
            
        context.scene.hrg_anim_source_rig = picked_obj
        self.report({'INFO'}, f"Selected Source Character: '{picked_obj.name}'")
        return {'FINISHED'}

class OBJECT_OT_pick_anim_target_rig(bpy.types.Operator):
    """Picks the currently selected 3D Viewport armature or character as the Target for animation transfer."""
    bl_idname = "object.pick_anim_target_rig"
    bl_label = "Pick Target Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        picked_obj = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            picked_obj = context.active_object
        elif context.active_object and context.active_object.parent and context.active_object.parent.type == 'ARMATURE':
            picked_obj = context.active_object.parent
            
        if not picked_obj:
            for o in context.selected_objects:
                if o.type == 'ARMATURE':
                    picked_obj = o
                    break
                elif o.parent and o.parent.type == 'ARMATURE':
                    picked_obj = o.parent
                    break
                    
        if not picked_obj:
            self.report({'WARNING'}, "Please select a target character Armature rig in the 3D Viewport first!")
            return {'CANCELLED'}
            
        context.scene.hrg_anim_target_rig = picked_obj
        self.report({'INFO'}, f"Selected Target Character: '{picked_obj.name}'")
        return {'FINISHED'}

class OBJECT_OT_transfer_actor_animation(bpy.types.Operator):
    """Transfers selected action/pose animation from Source Character to Target Character/Clone."""
    bl_idname = "object.transfer_actor_animation"
    bl_label = "Transfer Animation Data"
    bl_options = {'REGISTER', 'UNDO'}
    
    make_copy: bpy.props.BoolProperty( # type: ignore
        name="Make Independent Action Copy",
        description="If checked, creates a new unique action copy for the clone. If unchecked, shares the exact same action directly",
        default=False
    )
    
    preserve_location: bpy.props.BoolProperty( # type: ignore
        name="Preserve Target Position",
        description="Preserves the target character's world position so it doesn't snap to source location",
        default=True
    )
    
    def execute(self, context):
        scene = context.scene
        
        # 1. Resolve Source Rig
        src_obj = getattr(scene, "hrg_anim_source_rig", None)
        if not src_obj:
            src_name = getattr(scene, "hrg_source_actor_to_copy", 'NONE')
            if src_name != 'NONE' and src_name:
                src_obj = bpy.data.objects.get(src_name)
                
        # 2. Resolve Target Rig
        target_obj = getattr(scene, "hrg_anim_target_rig", None)
        if not target_obj:
            if context.active_object and context.active_object.type == 'ARMATURE' and context.active_object != src_obj:
                target_obj = context.active_object
            elif getattr(scene, "hrg_active_actor", 'NONE') != 'NONE':
                target_obj = bpy.data.objects.get(scene.hrg_active_actor)
                
        if not src_obj or src_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid Source Character Rig (use the Pen icon or dropdown)!")
            return {'CANCELLED'}
            
        if not target_obj or target_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid Target Character Rig (use the Pen icon or dropdown)!")
            return {'CANCELLED'}
            
        if src_obj == target_obj:
            self.report({'WARNING'}, "Source Character and Target Character cannot be the same rig!")
            return {'CANCELLED'}
            
        # 3. Retarget target constraints to itself so it evaluates its own controls
        retarget_rig_internal_constraints(target_obj, src_obj)
        
        # 4. Determine Action to transfer
        action_choice = getattr(scene, "hrg_anim_transfer_action", 'ACTIVE')
        source_action = None
        
        if action_choice == 'ACTIVE' or not action_choice:
            if src_obj.animation_data and src_obj.animation_data.action:
                source_action = src_obj.animation_data.action
            else:
                self.report({'WARNING'}, f"Source Character '{src_obj.name}' does not have an active animation action!")
                return {'CANCELLED'}
        else:
            source_action = bpy.data.actions.get(action_choice)
            if not source_action and src_obj.animation_data and src_obj.animation_data.action:
                source_action = src_obj.animation_data.action
                    
        if not source_action:
            self.report({'WARNING'}, "No valid Action found to transfer!")
            return {'CANCELLED'}
            
        # 5. Record target's current world location
        target_loc = target_obj.location.copy()
        src_loc = src_obj.location.copy()
        
        # 6. Assign Action to Target (Shared or Copy based on user preference)
        use_copy = getattr(scene, "hrg_anim_make_copy", self.make_copy)
        if use_copy:
            final_action = source_action.copy()
            final_action.name = f"{target_obj.name}_{source_action.name}"
            final_action.use_fake_user = True
        else:
            final_action = source_action
            final_action.use_fake_user = True
            
        if not target_obj.animation_data:
            target_obj.animation_data_create()
            
        # Make sure NLA tracks don't override the active action on target
        if target_obj.animation_data.nla_tracks:
            for track in target_obj.animation_data.nla_tracks:
                track.mute = True
                
        assign_action_to_rig(target_obj, final_action)
        
        # 7. If preserving location, offset object location fcurves
        fcurves = get_action_fcurves(final_action)
        if self.preserve_location and use_copy:
            obj_loc_fcs = [fc for fc in fcurves if fc.data_path == "location"]
            if obj_loc_fcs:
                delta = target_loc - src_loc
                for fc in obj_loc_fcs:
                    offset = delta[fc.array_index]
                    for kp in fc.keyframe_points:
                        kp.co[1] += offset
                        kp.handle_left[1] += offset
                        kp.handle_right[1] += offset
            else:
                target_obj.location = target_loc
        else:
            target_obj.location = target_loc
                
        # 8. Update timeline range if auto-fit enabled
        if getattr(scene, "hrg_set_timeline_range", True):
            valid_ranges = [fc.range() for fc in fcurves if len(fc.keyframe_points) > 0]
            if valid_ranges:
                scene.frame_start = int(min(r[0] for r in valid_ranges))
                scene.frame_end = int(max(r[1] for r in valid_ranges))
                
        # 9. Ensure Target is selected and active so viewport and timeline focus on it
        for o in context.selected_objects:
            o.select_set(False)
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='POSE')
            context.view_layer.update()
            
        context.view_layer.update()
        self.report({'INFO'}, f"Transferred Action '{final_action.name}' to '{target_obj.name}' successfully!")
        return {'FINISHED'}

class OBJECT_OT_clone_character_actor(bpy.types.Operator):
    """Clones the selected character rig and all attached skinned meshes into independent, conflict-free actors."""
    bl_idname = "object.clone_character_actor"
    bl_label = "Clone Actor"
    bl_options = {'REGISTER', 'UNDO'}
    
    clone_count: bpy.props.IntProperty( # type: ignore
        name="Number of Clones",
        description="How many independent copies of this character to generate",
        default=2,
        min=1,
        max=20
    )
    
    offset_spacing: bpy.props.FloatProperty( # type: ignore
        name="Spacing (X Offset)",
        description="Distance to place each cloned character apart along the X axis",
        default=1.5,
        min=0.0,
        max=20.0
    )
    
    def execute(self, context):
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a character Armature rig to clone!")
            return {'CANCELLED'}
            
        orig_armature = active_obj
        
        # Read from scene property if available
        count = getattr(context.scene, "hrg_clone_count", self.clone_count)
        
        # 1. Find all skinned mesh children attached to this armature
        skinned_meshes = []
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                if obj.parent == orig_armature:
                    skinned_meshes.append(obj)
                else:
                    for mod in obj.modifiers:
                        if mod.type == 'ARMATURE' and mod.object == orig_armature:
                            skinned_meshes.append(obj)
                            break
                            
        # Ensure we are in Object Mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            
        created_clones = []
        
        for clone_idx in range(1, count + 1):
            clone_suffix = f"_{clone_idx:02d}"
            base_name = orig_armature.name.split(".")[0]
            new_arm_name = f"{base_name}_Actor{clone_suffix}"
            
            # Select original armature and all skinned meshes together
            for o in context.selected_objects:
                o.select_set(False)
            orig_armature.select_set(True)
            for m in skinned_meshes:
                m.select_set(True)
            context.view_layer.objects.active = orig_armature
            
            # Perform native Blender duplication to preserve all IK constraints, bone shapes, and skinning
            bpy.ops.object.duplicate(linked=False)
            
            new_arm_obj = context.active_object
            new_meshes = [o for o in context.selected_objects if o != new_arm_obj and o.type == 'MESH']
            
            # Rename armature & data
            new_arm_obj.name = new_arm_name
            if new_arm_obj.data:
                new_arm_obj.data.name = f"{new_arm_name}_Data"
                
            # Retarget all internal bone constraints and modifiers from orig_armature to new_arm_obj!
            retarget_rig_internal_constraints(new_arm_obj, orig_armature)
                
            dx = self.offset_spacing * clone_idx
            # Create unique independent action copy if original had animation, or new action
            if not new_arm_obj.animation_data:
                new_arm_obj.animation_data_create()
                
            if orig_armature.animation_data and orig_armature.animation_data.action:
                cloned_act = orig_armature.animation_data.action.copy()
                cloned_act.name = f"{orig_armature.animation_data.action.name}{clone_suffix}"
                cloned_act.use_fake_user = True
                assign_action_to_rig(new_arm_obj, cloned_act)
                
                # Offset any object location keyframes by clone dx
                fcurves = get_action_fcurves(cloned_act)
                for fc in fcurves:
                    if fc.data_path == "location" and fc.array_index == 0:
                        for kp in fc.keyframe_points:
                            kp.co[1] += dx
                            kp.handle_left[1] += dx
                            kp.handle_right[1] += dx
            else:
                new_action = bpy.data.actions.new(f"{new_arm_name}_Action")
                assign_action_to_rig(new_arm_obj, new_action)
            
            # Offset position along X
            new_arm_obj.location.x = orig_armature.location.x + dx
            
            # Relink meshes, make mesh data and materials single-user
            for mesh_obj in new_meshes:
                raw_mesh_name = mesh_obj.name.split(".")[0]
                mesh_obj.name = f"{raw_mesh_name}{clone_suffix}"
                mesh_obj.data = mesh_obj.data.copy()
                mesh_obj.data.name = f"{mesh_obj.name}_Data"
                
                # Make sure parent is new_arm_obj
                mesh_obj.parent = new_arm_obj
                
                # Relink Armature modifier to new clone armature
                for mod in mesh_obj.modifiers:
                    if mod.type == 'ARMATURE':
                        mod.object = new_arm_obj
                        
                # Make all clothing and mesh materials single-user copies for independent coloring
                for slot_idx, slot in enumerate(mesh_obj.material_slots):
                    if slot.material:
                        cloned_mat = slot.material.copy()
                        cloned_mat.name = f"{slot.material.name}{clone_suffix}"
                        mesh_obj.material_slots[slot_idx].material = cloned_mat
                        
            # Create a separate, dedicated collection for this clone in the Outliner
            actor_coll_name = new_arm_name
            actor_coll = bpy.data.collections.get(actor_coll_name)
            if not actor_coll:
                actor_coll = bpy.data.collections.new(actor_coll_name)
                context.scene.collection.children.link(actor_coll)
                
            # Move the clone armature into its dedicated collection
            for coll in list(new_arm_obj.users_collection):
                coll.objects.unlink(new_arm_obj)
            actor_coll.objects.link(new_arm_obj)
            
            # Move all clone meshes into this dedicated collection
            for mesh_obj in new_meshes:
                for coll in list(mesh_obj.users_collection):
                    coll.objects.unlink(mesh_obj)
                actor_coll.objects.link(mesh_obj)
                
            created_clones.append(new_arm_obj)
            
        # Select the created clones
        if created_clones:
            context.view_layer.objects.active = created_clones[-1]
            bpy.ops.object.select_all(action='DESELECT')
            for c in created_clones:
                c.select_set(True)
                
            context.scene.hrg_active_actor = created_clones[-1].name
            
        context.view_layer.update()
        self.report({'INFO'}, f"Successfully created {len(created_clones)} independent character clones with full rig controllers and meshes!")
        return {'FINISHED'}

class OBJECT_OT_reset_rig_to_origin(bpy.types.Operator):
    """Resets the armature object, pose bones, root controller, and mesh back to the center of the world origin (0, 0, 0)."""
    bl_idname = "object.reset_rig_to_origin"
    bl_label = "Snap Rig to Origin (0,0,0)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "Please select a character armature or mesh!")
            return {'CANCELLED'}
            
        arm_obj = obj if obj.type == 'ARMATURE' else (obj.parent if obj.parent and obj.parent.type == 'ARMATURE' else None)
        if not arm_obj:
            self.report({'WARNING'}, "No Armature found on selected object!")
            return {'CANCELLED'}
            
        # 1. Reset Armature Object transforms in Object Mode
        arm_obj.location = (0.0, 0.0, 0.0)
        arm_obj.rotation_euler = (0.0, 0.0, 0.0)
        
        # 2. Reset all Pose Bone transforms in Pose Mode
        for pb in arm_obj.pose.bones:
            pb.location = (0.0, 0.0, 0.0)
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif pb.rotation_mode == 'AXIS_ANGLE':
                pb.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
            
        context.view_layer.update()
        self.report({'INFO'}, f"Successfully snapped '{arm_obj.name}' and all bones back to World Origin (0,0,0)!")
        return {'FINISHED'}

class OBJECT_OT_delete_character_actor(bpy.types.Operator):
    """Completely deletes the active character rig, all attached meshes, widget objects, and removes its collection from the Outliner."""
    bl_idname = "object.delete_character_actor"
    bl_label = "Delete Actor & Clean Collections"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active_obj = context.active_object
        actor_name = context.scene.hrg_active_actor
        
        # Prioritize the character currently selected by the user in the 3D Viewport
        arm_obj = None
        if active_obj:
            arm_obj = active_obj if active_obj.type == 'ARMATURE' else (active_obj.parent if active_obj.parent and active_obj.parent.type == 'ARMATURE' else None)
            
        if not arm_obj and actor_name != 'NONE' and actor_name:
            arm_obj = bpy.data.objects.get(actor_name)
            
        if not arm_obj:
            self.report({'WARNING'}, "Please select the character clone you want to delete!")
            return {'CANCELLED'}
            
        deleted_name = arm_obj.name
        
        # 1. If this actor has a dedicated collection (cloned actor), delete all objects inside it
        actor_coll = bpy.data.collections.get(deleted_name)
        if actor_coll:
            for o in list(actor_coll.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(actor_coll, do_unlink=True)
        else:
            # For non-collection armatures, ONLY delete meshes that are direct children of this exact armature
            for o in list(bpy.data.objects):
                if o.type == 'MESH' and o.parent == arm_obj:
                    bpy.data.objects.remove(o, do_unlink=True)
                    
        # 2. Find tracking target empty
        target_name = f"Cam_Target_{deleted_name}"
        target_obj = bpy.data.objects.get(target_name)
        if target_obj:
            bpy.data.objects.remove(target_obj, do_unlink=True)
            
        # 3. Find widget objects and widget collection specific to this character
        wgt_coll_name = f"WGTS_{deleted_name}"
        wgt_coll = bpy.data.collections.get(wgt_coll_name)
        if wgt_coll:
            for wgt_obj in list(wgt_coll.objects):
                bpy.data.objects.remove(wgt_obj, do_unlink=True)
            bpy.data.collections.remove(wgt_coll, do_unlink=True)
            
        # 4. Remove Armature object if not already removed with collection
        if deleted_name in bpy.data.objects:
            arm_to_remove = bpy.data.objects.get(deleted_name)
            if arm_to_remove:
                bpy.data.objects.remove(arm_to_remove, do_unlink=True)
                
        # 5. Clean any empty leftover collections specific to this character
        for coll in list(bpy.data.collections):
            if coll.name == deleted_name or coll.name == wgt_coll_name:
                try:
                    bpy.data.collections.remove(coll, do_unlink=True)
                except Exception:
                    pass
                        
        # Reset active actor safely
        remaining_arms = [o.name for o in context.scene.objects if o.type == 'ARMATURE']
        if remaining_arms:
            context.scene.hrg_active_actor = remaining_arms[0]
        else:
            context.scene.hrg_active_actor = 'NONE'
            
        context.view_layer.update()
        
        self.report({'INFO'}, f"Completely deleted Actor '{deleted_name}' and cleaned all collections!")
        return {'FINISHED'}

class OBJECT_OT_purge_unused_collections(bpy.types.Operator):
    """Purges all empty, orphaned, and leftover rig collections from the Outliner."""
    bl_idname = "object.purge_unused_collections"
    bl_label = "Clean Empty Collections"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        purged = 0
        for coll in list(bpy.data.collections):
            if len(coll.objects) == 0 and len(coll.children) == 0:
                if coll.name not in ["Collection", "Scene Collection"]:
                    try:
                        bpy.data.collections.remove(coll, do_unlink=True)
                        purged += 1
                    except Exception:
                        pass
        context.view_layer.update()
        self.report({'INFO'}, f"Purged {purged} empty collections from Outliner!")
        return {'FINISHED'}