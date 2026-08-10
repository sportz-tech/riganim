# operators/spawn_points.py
import bpy
import blf
import mathutils
import bpy_extras.view3d_utils
from ..utils.naming import get_control_name

def draw_spawn_hud(self, context):
    font_id = 0
    x, y = 30, 80
    blf.size(font_id, 18)
    blf.color(font_id, 0.2, 0.8, 1.0, 1.0) # Cyan
    blf.position(font_id, x, y, 0)
    count = len([o for o in context.scene.objects if o.name.startswith("SpawnPoint_")])
    blf.draw(font_id, f"SPAWN MARKER PLACEMENT (Placed: {count})")
    
    blf.size(font_id, 13)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0) # White
    blf.position(font_id, x, y - 24, 0)
    blf.draw(font_id, "Click anywhere on plane/surface to drop a Spawn Marker")
    
    blf.size(font_id, 12)
    blf.color(font_id, 0.7, 0.7, 0.7, 1.0) # Gray
    blf.position(font_id, x, y - 48, 0)
    blf.draw(font_id, "[Left-Click: Drop Marker | Ctrl+Z: Undo | Right-Click / ESC: Finish]")

class OBJECT_OT_interactive_spawn_point_place(bpy.types.Operator):
    """Click anywhere on a ground plane or mesh surface to place character spawn points."""
    bl_idname = "object.interactive_spawn_point_place"
    bl_label = "Click to Place Spawn Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    _handle = None
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        # Exit placement on ESC, Right-Click, Enter, Space
        if (event.type in {'ESC', 'RIGHTMOUSE', 'RET', 'NUMPAD_ENTER', 'SPACE'}) and event.value == 'PRESS':
            self.cleanup(context)
            count = len([o for o in context.scene.objects if o.name.startswith("SpawnPoint_")])
            self.report({'INFO'}, f"Finished placing spawn markers (Total: {count}).")
            return {'FINISHED'}
            
        # If mouse is outside the 3D window canvas (e.g. over sidebar panel), automatically exit and pass click to UI!
        if context.region.type != 'WINDOW':
            self.cleanup(context)
            return {'PASS_THROUGH'}
            
        # Ctrl+Z undo inside modal
        if event.ctrl and event.type == 'Z' and event.value == 'PRESS':
            points = sorted([o for o in context.scene.objects if o.name.startswith("SpawnPoint_")], key=lambda o: o.name)
            if points:
                bpy.data.objects.remove(points[-1], do_unlink=True)
                context.area.tag_redraw()
                self.report({'INFO'}, "Removed last spawn point.")
            return {'RUNNING_MODAL'}
            
        # Navigation pass-through
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NDOF_MOTION'} or event.shift or event.alt:
            return {'PASS_THROUGH'}
            
        if event.type not in {'LEFTMOUSE'}:
            return {'PASS_THROUGH'}
            
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            event_pos = (event.mouse_region_x, event.mouse_region_y)
            region = context.region
            rv3d = context.region_data
            
            ray_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, event_pos)
            ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, event_pos)
            
            # Find hit surface via scene raycast
            depsgraph = context.evaluated_depsgraph_get()
            result, location, normal, index, hit_obj, matrix = context.scene.ray_cast(depsgraph, ray_origin, ray_vector)
            
            if not result:
                # If clicked in empty space, project onto ground plane (Z=0)
                if abs(ray_vector.z) > 1e-6:
                    t = -ray_origin.z / ray_vector.z
                    if t > 0:
                        location = ray_origin + t * ray_vector
                        result = True
                        
            if result:
                # Get next spawn point number
                idx = 1
                while f"SpawnPoint_{idx:02d}" in bpy.data.objects:
                    idx += 1
                mkr_name = f"SpawnPoint_{idx:02d}"
                
                # Create visual spawn point empty
                empty = bpy.data.objects.new(mkr_name, None)
                empty.empty_display_type = 'CIRCLE'
                empty.empty_display_size = 0.4
                empty.location = location
                empty.show_name = True
                
                # Put in SpawnPoints collection
                coll_name = "Spawn_Points"
                coll = bpy.data.collections.get(coll_name)
                if not coll:
                    coll = bpy.data.collections.new(coll_name)
                    context.scene.collection.children.link(coll)
                coll.objects.link(empty)
                
                context.area.tag_redraw()
                self.report({'INFO'}, f"Placed '{mkr_name}' at ({location.x:.2f}, {location.y:.2f}, {location.z:.2f})")
                
            return {'RUNNING_MODAL'}
            
        return {'PASS_THROUGH'}
        
    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Must be run from a 3D Viewport!")
            return {'CANCELLED'}
            
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_spawn_hud, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}
        
    def cleanup(self, context):
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        context.area.tag_redraw()

class OBJECT_OT_clone_to_spawn_points(bpy.types.Operator):
    """Spawns character clones placed directly at each marked spawn point on the plane."""
    bl_idname = "object.clone_to_spawn_points"
    bl_label = "Clone to Spawn Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a character Armature rig to clone!")
            return {'CANCELLED'}
            
        orig_armature = active_obj
        
        # Find all spawn points in the scene
        spawn_points = sorted([o for o in context.scene.objects if o.name.startswith("SpawnPoint_")], key=lambda o: o.name)
        if not spawn_points:
            self.report({'WARNING'}, "No spawn points found! Click 'Click to Place Spawn Points' first.")
            return {'CANCELLED'}
            
        # Find all skinned child meshes
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
                            
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            
        created_clones = []
        
        for idx, sp in enumerate(spawn_points, start=1):
            clone_suffix = f"_{idx:02d}"
            base_name = orig_armature.name.split(".")[0]
            new_arm_name = f"{base_name}_Actor{clone_suffix}"
            
            # Select original armature + meshes
            bpy.ops.object.select_all(action='DESELECT')
            orig_armature.select_set(True)
            for m in skinned_meshes:
                m.select_set(True)
            context.view_layer.objects.active = orig_armature
            
            # Duplicate natively
            bpy.ops.object.duplicate(linked=False)
            
            new_arm_obj = context.active_object
            new_meshes = [o for o in context.selected_objects if o != new_arm_obj and o.type == 'MESH']
            
            # Rename armature
            new_arm_obj.name = new_arm_name
            if new_arm_obj.data:
                new_arm_obj.data.name = f"{new_arm_name}_Data"
                
            # Create independent animation action
            if not new_arm_obj.animation_data:
                new_arm_obj.animation_data_create()
            new_action = bpy.data.actions.new(f"{new_arm_name}_Action")
            new_arm_obj.animation_data.action = new_action
            
            # Position character directly at spawn point
            new_arm_obj.location = sp.location.copy()
            
            # Create dedicated collection for this clone
            actor_coll_name = new_arm_name
            actor_coll = bpy.data.collections.get(actor_coll_name)
            if not actor_coll:
                actor_coll = bpy.data.collections.new(actor_coll_name)
                context.scene.collection.children.link(actor_coll)
                
            for coll in list(new_arm_obj.users_collection):
                coll.objects.unlink(new_arm_obj)
            actor_coll.objects.link(new_arm_obj)
            
            # Setup meshes
            for mesh_obj in new_meshes:
                raw_name = mesh_obj.name.split(".")[0]
                mesh_obj.name = f"{raw_name}{clone_suffix}"
                mesh_obj.data = mesh_obj.data.copy()
                mesh_obj.parent = new_arm_obj
                
                for mod in mesh_obj.modifiers:
                    if mod.type == 'ARMATURE':
                        mod.object = new_arm_obj
                        
                for slot_idx, slot in enumerate(mesh_obj.material_slots):
                    if slot.material:
                        cloned_mat = slot.material.copy()
                        cloned_mat.name = f"{slot.material.name}{clone_suffix}"
                        mesh_obj.material_slots[slot_idx].material = cloned_mat
                        
                for coll in list(mesh_obj.users_collection):
                    coll.objects.unlink(mesh_obj)
                actor_coll.objects.link(mesh_obj)
                
            created_clones.append(new_arm_obj)
            
        context.view_layer.update()
        self.report({'INFO'}, f"Spawned {len(created_clones)} character clones at marked spawn points!")
        return {'FINISHED'}

class OBJECT_OT_keyframe_move_to_point(bpy.types.Operator):
    """Moves or keyframes the selected character to a target point across a set frame duration."""
    bl_idname = "object.keyframe_move_to_point"
    bl_label = "Move Character to Point"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: bpy.props.EnumProperty( # type: ignore
        name="Move Mode",
        items=[
            ('ANIMATE', "Keyframe Travel", "Animate translation from current frame to target frame"),
            ('SNAP', "Instant Snap", "Instantly teleports character to target location")
        ],
        default='ANIMATE'
    )
    
    duration: bpy.props.IntProperty( # type: ignore
        name="Duration (Frames)",
        description="Number of frames for the character to travel from current spot to target spot",
        default=10,
        min=1,
        max=500
    )
    
    def execute(self, context):
        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "Please select a character armature or mesh!")
            return {'CANCELLED'}
            
        arm_obj = active_obj if active_obj.type == 'ARMATURE' else (active_obj.parent if active_obj.parent and active_obj.parent.type == 'ARMATURE' else None)
        if not arm_obj:
            self.report({'WARNING'}, "No Armature found on selected object!")
            return {'CANCELLED'}
            
        # Target position from selected spawn point or 3D cursor
        target_pos = None
        for o in context.selected_objects:
            if o.name.startswith("SpawnPoint_"):
                target_pos = o.location.copy()
                break
                
        if not target_pos:
            target_pos = context.scene.cursor.location.copy()
            
        if self.mode == 'SNAP':
            arm_obj.location = target_pos
            context.view_layer.update()
            self.report({'INFO'}, f"Snapped '{arm_obj.name}' to location ({target_pos.x:.2f}, {target_pos.y:.2f}, {target_pos.z:.2f})!")
            return {'FINISHED'}
            
        # ANIMATE MODE: Keyframe root bone translation across frames
        pb_root = arm_obj.pose.bones.get(get_control_name("root"))
        if not pb_root:
            pb_root = arm_obj.pose.bones.get("root")
            
        start_frame = context.scene.frame_current
        end_frame = start_frame + self.duration
        
        if not arm_obj.animation_data:
            arm_obj.animation_data_create()
        if not arm_obj.animation_data.action:
            arm_obj.animation_data.action = bpy.data.actions.new(f"{arm_obj.name}_Action")
            
        # Keyframe start position at current frame
        arm_obj.keyframe_insert(data_path="location", frame=start_frame)
        
        # Move and keyframe end position at target frame
        arm_obj.location = target_pos
        arm_obj.keyframe_insert(data_path="location", frame=end_frame)
        
        # Set linear interpolation for smooth travel
        action = arm_obj.animation_data.action
        for fc in action.fcurves if hasattr(action, "fcurves") else []:
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                    
        context.scene.frame_end = max(context.scene.frame_end, end_frame)
        context.view_layer.update()
        
        self.report({'INFO'}, f"Keyframed travel from frame {start_frame} to {end_frame} ({self.duration} frames) to target point!")
        return {'FINISHED'}

class OBJECT_OT_clear_spawn_points(bpy.types.Operator):
    """Removes all spawn points from the scene."""
    bl_idname = "object.clear_spawn_points"
    bl_label = "Clear Spawn Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        points = [o for o in list(bpy.data.objects) if o.name.startswith("SpawnPoint_")]
        for p in points:
            bpy.data.objects.remove(p, do_unlink=True)
            
        coll = bpy.data.collections.get("Spawn_Points")
        if coll:
            bpy.data.collections.remove(coll, do_unlink=True)
            
        context.view_layer.update()
        self.report({'INFO'}, f"Cleared {len(points)} spawn points.")
        return {'FINISHED'}

class OBJECT_OT_add_spawn_point_at_cursor(bpy.types.Operator):
    """Adds a single spawn point directly at the 3D Cursor position."""
    bl_idname = "object.add_spawn_point_at_cursor"
    bl_label = "Add Spawn Point at Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        location = context.scene.cursor.location.copy()
        idx = 1
        while f"SpawnPoint_{idx:02d}" in bpy.data.objects:
            idx += 1
        mkr_name = f"SpawnPoint_{idx:02d}"
        
        empty = bpy.data.objects.new(mkr_name, None)
        empty.empty_display_type = 'CIRCLE'
        empty.empty_display_size = 0.4
        empty.location = location
        empty.show_name = True
        
        coll_name = "Spawn_Points"
        coll = bpy.data.collections.get(coll_name)
        if not coll:
            coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(coll)
        coll.objects.link(empty)
        
        context.view_layer.update()
        self.report({'INFO'}, f"Added '{mkr_name}' at 3D Cursor ({location.x:.2f}, {location.y:.2f}, {location.z:.2f})")
        return {'FINISHED'}
