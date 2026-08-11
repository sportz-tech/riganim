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
            get_control_name("hand.fk.R"), "hand.fk.R", "wrist.R"
        ]
    elif slot == 'LEFT_HAND':
        candidates = [
            get_control_name("hand.ik.L"), "hand.ik.L", "CTRL-hand.L",
            get_deform_name("hand.L"), "DEF-hand.L", "hand.L",
            get_control_name("hand.fk.L"), "hand.fk.L", "wrist.L"
        ]
    elif slot == 'HEAD':
        candidates = [
            get_control_name("head"), "CTRL-head",
            get_deform_name("head"), "DEF-head", "head", "head.001"
        ]
    elif slot == 'CHEST':
        candidates = [
            get_control_name("spine.003"), "CTRL-spine.003",
            get_deform_name("spine.003"), "DEF-spine.003", "spine.003", "chest",
            get_control_name("spine.002"), "CTRL-spine.002", "spine.002"
        ]
    elif slot == 'RIGHT_FOOT':
        candidates = [
            get_control_name("foot.ik.R"), "foot.ik.R", "CTRL-foot.R",
            get_deform_name("foot.R"), "DEF-foot.R", "foot.R",
            get_control_name("foot.fk.R"), "foot.fk.R", "ankle.R"
        ]
    elif slot == 'LEFT_FOOT':
        candidates = [
            get_control_name("foot.ik.L"), "foot.ik.L", "CTRL-foot.L",
            get_deform_name("foot.L"), "DEF-foot.L", "foot.L",
            get_control_name("foot.fk.L"), "foot.fk.L", "ankle.L"
        ]
    else: # PELVIS / BELT
        candidates = [
            get_control_name("pelvis"), "CTRL-pelvis",
            get_deform_name("pelvis"), "DEF-pelvis", "pelvis", "root", "spine"
        ]
        
    for name in candidates:
        if name in bone_names:
            return name
            
    return bone_names[0] if bone_names else None

def get_prop_items(self, context):
    """Dynamic enum for selectable prop objects in the scene, including armatures and meshes."""
    items = [('NONE', "Select Prop / Rig", "No prop selected")]
    if not context or not hasattr(context, "scene") or not context.scene:
        return items
        
    target_actor = getattr(context.scene, "hrg_prop_target_actor", "NONE")
    
    for obj in context.scene.objects:
        # Avoid listing the holder actor as a prop to attach to itself
        if target_actor != 'NONE' and obj.name == target_actor:
            continue
            
        # Ignore internal helper objects like spawn points and markers
        if obj.name.startswith("SpawnPoint_") or obj.name.startswith("Mkr_"):
            continue
            
        # Allow Armatures, Meshes, Curves, Empties, Surfaces, Fonts
        if obj.type in {'ARMATURE', 'MESH', 'CURVE', 'EMPTY', 'SURFACE', 'FONT'}:
            type_label = "Rig" if obj.type == 'ARMATURE' else obj.type.capitalize()
            items.append((obj.name, f"{obj.name} [{type_label}]", f"Attach {obj.name} ({type_label}) to character slot"))
            
    return items

def resolve_prop_object(context, scene, target_actor_obj=None, attach_parent_rig=True):
    """Resolves the prop object from pointer property, scene enum, or selection, supporting armatures and rigged meshes."""
    prop_obj = getattr(scene, "hrg_prop_source_obj", None)
    
    if not prop_obj:
        prop_name = getattr(scene, "hrg_prop_object", 'NONE')
        if prop_name != 'NONE' and prop_name:
            prop_obj = bpy.data.objects.get(prop_name)
            
    if not prop_obj:
        # Fallback: check active or selected objects
        candidates = []
        if context.active_object:
            candidates.append(context.active_object)
        for o in context.selected_objects:
            if o not in candidates:
                candidates.append(o)
                
        for o in candidates:
            if o != target_actor_obj and o.type in {'ARMATURE', 'MESH', 'CURVE', 'EMPTY', 'SURFACE', 'FONT'}:
                if not o.name.startswith("SpawnPoint_") and not o.name.startswith("Mkr_"):
                    prop_obj = o
                    break
                    
    if prop_obj and attach_parent_rig:
        # If user picked a mesh whose parent is an armature (and not the character actor), attach the parent armature rig
        if prop_obj.type == 'MESH' and prop_obj.parent and prop_obj.parent.type == 'ARMATURE':
            if target_actor_obj is None or prop_obj.parent != target_actor_obj:
                prop_obj = prop_obj.parent
                
    return prop_obj

class OBJECT_OT_pick_prop_from_selection(bpy.types.Operator):
    """Picks the currently selected 3D Viewport object or armature as the Prop to attach."""
    bl_idname = "object.pick_prop_from_selection"
    bl_label = "Pick Selected Object / Armature as Prop"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        target_actor = getattr(scene, "hrg_prop_target_actor", "NONE")
        
        picked_obj = None
        # Check active object first
        if context.active_object and context.active_object.name != target_actor:
            if not context.active_object.name.startswith("SpawnPoint_") and not context.active_object.name.startswith("Mkr_"):
                picked_obj = context.active_object
                
        if not picked_obj:
            for o in context.selected_objects:
                if o.name != target_actor and not o.name.startswith("SpawnPoint_") and not o.name.startswith("Mkr_"):
                    picked_obj = o
                    break
                    
        if not picked_obj:
            self.report({'WARNING'}, "Please click or select an object or armature in the 3D Viewport first!")
            return {'CANCELLED'}
            
        scene.hrg_prop_source_obj = picked_obj
        if hasattr(scene, "hrg_prop_object"):
            try:
                scene.hrg_prop_object = picked_obj.name
            except Exception:
                pass
                
        type_label = "Armature Rig" if picked_obj.type == 'ARMATURE' else picked_obj.type.capitalize()
        self.report({'INFO'}, f"Picked {type_label} '{picked_obj.name}' as Prop!")
        return {'FINISHED'}

class OBJECT_OT_attach_prop(bpy.types.Operator):
    """Attaches the selected prop or prop armature to a character's hand, head, chest, belt, or foot with 1-click."""
    bl_idname = "object.attach_prop"
    bl_label = "Attach Prop to Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    snap_to_bone: bpy.props.BoolProperty( # type: ignore
        name="Snap to Hand/Slot",
        description="Snaps the prop directly into the hand palm / slot location",
        default=True
    )
    
    auto_grasp: bpy.props.BoolProperty( # type: ignore
        name="Auto-Grasp Fingers",
        description="Automatically curls fingers to hold the prop naturally",
        default=True
    )

    attach_parent_rig: bpy.props.BoolProperty( # type: ignore
        name="Attach Parent Rig if Rigged",
        description="If selected mesh belongs to an armature rig, attach the root armature rig so all bones and meshes follow",
        default=True
    )
    
    def execute(self, context):
        scene = context.scene
        
        # 1. Find Character Armature
        arm_name = scene.hrg_prop_target_actor
        arm_obj = None
        if arm_name != 'NONE' and arm_name:
            arm_obj = bpy.data.objects.get(arm_name)
            
        # 2. Find prop object (mesh or armature)
        prop_obj = resolve_prop_object(context, scene, target_actor_obj=arm_obj, attach_parent_rig=self.attach_parent_rig)
        
        if not arm_obj:
            # Fallback: check active or first armature that is not the prop
            if context.active_object and context.active_object.type == 'ARMATURE' and context.active_object != prop_obj:
                arm_obj = context.active_object
            else:
                for o in context.scene.objects:
                    if o.type == 'ARMATURE' and o != prop_obj:
                        arm_obj = o
                        break
                        
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object or Armature (e.g. Weapon Rig, Dog Rig, Phone, Tool)!")
            return {'CANCELLED'}
            
        if not arm_obj:
            self.report({'WARNING'}, "No character armature found to attach prop to!")
            return {'CANCELLED'}
            
        if prop_obj == arm_obj:
            self.report({'WARNING'}, "Cannot attach character armature to itself as a prop! Select a different prop or actor.")
            return {'CANCELLED'}
            
        slot = scene.hrg_prop_slot
        bone_name = find_attach_bone(arm_obj, slot)
        if not bone_name:
            self.report({'WARNING'}, f"Could not find a valid bone for slot '{slot}' on '{arm_obj.name}'!")
            return {'CANCELLED'}
            
        # 3. Add or update CHILD_OF constraint on the prop (works for Mesh and Armature objects)
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
        if bone_name in arm_obj.pose.bones:
            c.inverse_matrix = (arm_obj.matrix_world @ arm_obj.pose.bones[bone_name].matrix).inverted()
        else:
            c.inverse_matrix = arm_obj.matrix_world.inverted()
        
        # 5. Auto Grasp Hand Fingers if attached to hand
        if self.auto_grasp and slot in {'RIGHT_HAND', 'LEFT_HAND'}:
            side = ".R" if slot == 'RIGHT_HAND' else ".L"
            hand_pb_name = get_control_name(f"hand.ik{side}")
            hand_pb = arm_obj.pose.bones.get(hand_pb_name)
            if not hand_pb:
                hand_pb = arm_obj.pose.bones.get(f"hand.ik{side}") or arm_obj.pose.bones.get(f"hand{side}")
            if hand_pb and hasattr(hand_pb, "hrg_grasp"):
                hand_pb.hrg_grasp = 0.85
                
        context.view_layer.update()
        type_str = "Armature Rig" if prop_obj.type == 'ARMATURE' else "Prop"
        self.report({'INFO'}, f"Attached {type_str} '{prop_obj.name}' to '{arm_obj.name}' ({bone_name})!")
        return {'FINISHED'}

class OBJECT_OT_keyframe_prop_pickup(bpy.types.Operator):
    """Keyframes the prop or armature rig being picked up / grabbed at the current timeline frame."""
    bl_idname = "object.keyframe_prop_pickup"
    bl_label = "Keyframe Prop Pickup"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        
        prop_obj = resolve_prop_object(context, scene, attach_parent_rig=True)
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object or Armature to keyframe!")
            return {'CANCELLED'}
            
        # Find Child Of constraint on prop object or its parent
        child_of_consts = [c for c in prop_obj.constraints if c.type == 'CHILD_OF']
        if not child_of_consts and prop_obj.parent:
            child_of_consts = [c for c in prop_obj.parent.constraints if c.type == 'CHILD_OF']
            if child_of_consts:
                prop_obj = prop_obj.parent
                
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
    """Keyframes the prop or armature rig being dropped / released at the current timeline frame, holding its world position."""
    bl_idname = "object.keyframe_prop_drop"
    bl_label = "Keyframe Prop Drop"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        
        prop_obj = resolve_prop_object(context, scene, attach_parent_rig=True)
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object or Armature to drop!")
            return {'CANCELLED'}
            
        child_of_consts = [c for c in prop_obj.constraints if c.type == 'CHILD_OF']
        if not child_of_consts and prop_obj.parent:
            child_of_consts = [c for c in prop_obj.parent.constraints if c.type == 'CHILD_OF']
            if child_of_consts:
                prop_obj = prop_obj.parent
                
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
    """Completely detaches the prop or armature rig from the character, holding its current world transform."""
    bl_idname = "object.detach_prop"
    bl_label = "Detach Prop"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        prop_obj = resolve_prop_object(context, scene, attach_parent_rig=True)
        if not prop_obj:
            self.report({'WARNING'}, "Please select a Prop object or Armature to detach!")
            return {'CANCELLED'}
            
        # Preserve world transform
        target_objs = [prop_obj]
        if prop_obj.parent and prop_obj.parent.type == 'ARMATURE':
            target_objs.append(prop_obj.parent)
            
        detached_any = False
        for obj in target_objs:
            world_mat = obj.matrix_world.copy()
            for c in list(obj.constraints):
                if c.type == 'CHILD_OF':
                    obj.constraints.remove(c)
                    detached_any = True
            obj.matrix_world = world_mat
            
        context.view_layer.update()
        if detached_any:
            self.report({'INFO'}, f"Detached '{prop_obj.name}' from character!")
        else:
            self.report({'INFO'}, f"No active Child Of constraint found on '{prop_obj.name}'.")
        return {'FINISHED'}


