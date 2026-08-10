# operators/props.py
import bpy
import mathutils
from ..utils.naming import get_control_name, get_deform_name, get_org_name

def find_attach_bone(arm_obj, slot='RIGHT_HAND'):
    """Resolves the best bone to attach a prop to based on available rig bones."""
    if not arm_obj or arm_obj.type != 'ARMATURE':
        return None
        
    bone_names = arm_obj.data.bones.keys()
    
    if slot == 'RIGHT_HAND':
        candidates = [
            get_control_name("hand.ik.R"), "hand.ik.R", "CTRL-hand.R",
            get_deform_name("hand.R"), "DEF-hand.R", "hand.R",
            get_control_name("hand.fk.R"), "hand.fk.R"
        ]
    elif slot == 'LEFT_HAND':
        candidates = [
            get_control_name("hand.ik.L"), "hand.ik.L", "CTRL-hand.L",
            get_deform_name("hand.L"), "DEF-hand.L", "hand.L",
            get_control_name("hand.fk.L"), "hand.fk.L"
        ]
    elif slot == 'HEAD':
        candidates = [
            get_control_name("head"), "CTRL-head",
            get_deform_name("head"), "DEF-head", "head"
        ]
    elif slot == 'CHEST':
        candidates = [
            get_control_name("spine.003"), "CTRL-spine.003",
            get_deform_name("spine.003"), "DEF-spine.003", "spine.003", "chest"
        ]
    else: # PELVIS / BELT
        candidates = [
            get_control_name("pelvis"), "CTRL-pelvis",
            get_deform_name("pelvis"), "DEF-pelvis", "pelvis", "root"
        ]
        
    for name in candidates:
        if name in bone_names:
            return name
            
    return bone_names[0] if bone_names else None

def get_prop_items(self, context):
    """Dynamic enum for selectable prop objects in the scene."""
    items = [('NONE', "Select Prop Object", "No prop selected")]
    for obj in context.scene.objects:
        # Mesh or Curve objects that are not armatures
        if obj.type in {'MESH', 'CURVE'} and not obj.parent_bone:
            # Check if not part of a character rig
            if not obj.name.startswith("SpawnPoint_") and not obj.name.startswith("Mkr_"):
                items.append((obj.name, obj.name, f"Attach {obj.name}"))
    return items

class OBJECT_OT_attach_prop(bpy.types.Operator):
    """Attaches the selected prop to a character's hand, head, chest, or belt with 1-click."""
    bl_idname = "object.attach_prop"
    bl_label = "Attach Prop to Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    snap_to_bone: bpy.props.BoolProperty(
        name="Snap to Hand/Slot",
        description="Snaps the prop directly into the hand palm / slot location",
        default=True
    ) # type: ignore
    
    auto_grasp: bpy.props.BoolProperty(
        name="Auto-Grasp Fingers",
        description="Automatically curls fingers to hold the prop naturally",
        default=True
    ) # type: ignore
    
    def execute(self, context):
        scene = context.scene
        
        # 1. Find prop object
        prop_name = scene.hrg_prop_object
        prop_obj = None
        if prop_name != 'NONE' and prop_name:
            prop_obj = bpy.data.objects.get(prop_name)
            
        if not prop_obj:
            # Fallback: check selected non-armature object
            for o in context.selected_objects:
                if o.type in {'MESH', 'CURVE'} and o.type != 'ARMATURE':
                    prop_obj = o
                    break
                    
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object (e.g. Phone, Rope, Tool, Dog)!")
            return {'CANCELLED'}
            
        # 2. Find Character Armature
        arm_name = scene.hrg_prop_target_actor
        arm_obj = None
        if arm_name != 'NONE' and arm_name:
            arm_obj = bpy.data.objects.get(arm_name)
        if not arm_obj and context.active_object and context.active_object.type == 'ARMATURE':
            arm_obj = context.active_object
        if not arm_obj:
            for o in context.scene.objects:
                if o.type == 'ARMATURE':
                    arm_obj = o
                    break
                    
        if not arm_obj:
            self.report({'WARNING'}, "No character armature found to attach prop to!")
            return {'CANCELLED'}
            
        slot = scene.hrg_prop_slot
        bone_name = find_attach_bone(arm_obj, slot)
        if not bone_name:
            self.report({'WARNING'}, f"Could not find a valid bone for slot '{slot}'!")
            return {'CANCELLED'}
            
        # 3. Add or update CHILD_OF constraint on the prop
        const_name = f"ChildOf_{arm_obj.name}"
        c = prop_obj.constraints.get(const_name)
        if not c:
            c = prop_obj.constraints.new(type='CHILD_OF')
            c.name = const_name
            
        c.target = arm_obj
        c.subtarget = bone_name
        c.influence = 1.0
        
        context.view_layer.update()
        
        # 4. Snap to bone position if requested
        if self.snap_to_bone:
            pb = arm_obj.pose.bones.get(bone_name)
            if pb:
                bone_world_matrix = arm_obj.matrix_world @ pb.matrix
                prop_obj.matrix_world = bone_world_matrix
                
        # Calculate inverse so child of is stable
        c.inverse_matrix = (arm_obj.matrix_world @ arm_obj.pose.bones[bone_name].matrix).inverted()
        
        # 5. Auto Grasp Hand Fingers if attached to hand
        if self.auto_grasp and slot in {'RIGHT_HAND', 'LEFT_HAND'}:
            side = ".R" if slot == 'RIGHT_HAND' else ".L"
            hand_pb_name = get_control_name(f"hand.ik{side}")
            hand_pb = arm_obj.pose.bones.get(hand_pb_name)
            if not hand_pb:
                hand_pb = arm_obj.pose.bones.get(f"hand.ik{side}") or arm_obj.pose.bones.get(f"hand{side}")
            if hand_pb:
                hand_pb.hrg_grasp = 0.85
                
        context.view_layer.update()
        self.report({'INFO'}, f"Attached '{prop_obj.name}' to '{arm_obj.name}' ({bone_name})!")
        return {'FINISHED'}

class OBJECT_OT_keyframe_prop_pickup(bpy.types.Operator):
    """Keyframes the prop being picked up / grabbed at the current timeline frame."""
    bl_idname = "object.keyframe_prop_pickup"
    bl_label = "Keyframe Prop Pickup"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        
        prop_name = scene.hrg_prop_object
        prop_obj = bpy.data.objects.get(prop_name) if prop_name != 'NONE' else None
        if not prop_obj and context.active_object and context.active_object.type in {'MESH', 'CURVE'}:
            prop_obj = context.active_object
            
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object to keyframe!")
            return {'CANCELLED'}
            
        # Find Child Of constraint
        child_of_consts = [c for c in prop_obj.constraints if c.type == 'CHILD_OF']
        if not child_of_consts:
            # Run attach first
            bpy.ops.object.attach_prop(snap_to_bone=False)
            child_of_consts = [c for c in prop_obj.constraints if c.type == 'CHILD_OF']
            
        if not child_of_consts:
            self.report({'WARNING'}, "No Child Of constraint found on prop!")
            return {'CANCELLED'}
            
        c = child_of_consts[0]
        
        # Keyframe: 0.0 influence at frame - 1, 1.0 influence at current frame
        if frame > 1:
            c.influence = 0.0
            c.keyframe_insert(data_path="influence", frame=frame - 1)
            
        c.influence = 1.0
        c.keyframe_insert(data_path="influence", frame=frame)
        
        self.report({'INFO'}, f"Keyframed pickup of '{prop_obj.name}' at frame {frame}!")
        return {'FINISHED'}

class OBJECT_OT_keyframe_prop_drop(bpy.types.Operator):
    """Keyframes the prop being dropped / released at the current timeline frame, holding its world position."""
    bl_idname = "object.keyframe_prop_drop"
    bl_label = "Keyframe Prop Drop"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        
        prop_name = scene.hrg_prop_object
        prop_obj = bpy.data.objects.get(prop_name) if prop_name != 'NONE' else None
        if not prop_obj and context.active_object and context.active_object.type in {'MESH', 'CURVE'}:
            prop_obj = context.active_object
            
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object to drop!")
            return {'CANCELLED'}
            
        child_of_consts = [c for c in prop_obj.constraints if c.type == 'CHILD_OF']
        if not child_of_consts:
            self.report({'WARNING'}, "Prop does not have an active Child Of constraint to drop!")
            return {'CANCELLED'}
            
        c = child_of_consts[0]
        
        # 1. Preserve world matrix at current frame
        context.view_layer.update()
        world_mat = prop_obj.matrix_world.copy()
        
        # 2. Keyframe influence = 1.0 at frame - 1
        if frame > 1:
            c.influence = 1.0
            c.keyframe_insert(data_path="influence", frame=frame - 1)
            
        # 3. Keyframe influence = 0.0 at current frame
        c.influence = 0.0
        c.keyframe_insert(data_path="influence", frame=frame)
        
        # 4. Set world matrix and keyframe object location & rotation so it doesn't pop
        prop_obj.matrix_world = world_mat
        prop_obj.keyframe_insert(data_path="location", frame=frame)
        prop_obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        
        context.view_layer.update()
        self.report({'INFO'}, f"Keyframed release/drop of '{prop_obj.name}' at frame {frame}!")
        return {'FINISHED'}

class OBJECT_OT_detach_prop(bpy.types.Operator):
    """Completely detaches the prop from the character, holding its current world transform."""
    bl_idname = "object.detach_prop"
    bl_label = "Detach Prop"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        prop_name = scene.hrg_prop_object
        prop_obj = bpy.data.objects.get(prop_name) if prop_name != 'NONE' else None
        if not prop_obj and context.active_object and context.active_object.type in {'MESH', 'CURVE'}:
            prop_obj = context.active_object
            
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object to detach!")
            return {'CANCELLED'}
            
        # Preserve world transform
        world_mat = prop_obj.matrix_world.copy()
        
        for c in list(prop_obj.constraints):
            if c.type == 'CHILD_OF':
                prop_obj.constraints.remove(c)
                
        prop_obj.matrix_world = world_mat
        context.view_layer.update()
        self.report({'INFO'}, f"Detached '{prop_obj.name}' from character!")
        return {'FINISHED'}
