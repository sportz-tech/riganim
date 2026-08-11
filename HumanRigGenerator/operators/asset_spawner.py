# operators/asset_spawner.py
import bpy
import blf
import math
import random
import mathutils
import os
import bpy_extras.view3d_utils
from bpy_extras.io_utils import ImportHelper

# Track placed batches for modal undo
_placed_batches = []

def get_target_source_object(context):
    """Returns the object to spawn: either from picker property or active/selected object."""
    scene = context.scene
    src = getattr(scene, "hrg_spawn_source_obj", None)
    if src:
        return src
    
    # Otherwise fallback to active or first selected mesh/object
    active = context.active_object
    if active and not active.name.startswith("SpawnPoint_") and not active.name.startswith("Mkr_"):
        return active
        
    for obj in context.selected_objects:
        if not obj.name.startswith("SpawnPoint_") and not obj.name.startswith("Mkr_"):
            return obj
            
    return None

def get_source_hierarchy(root_obj):
    """Returns all objects belonging to the source object's hierarchy (root + children)."""
    objs = [root_obj]
    for child in root_obj.children_recursive:
        objs.append(child)
    return objs

def spawn_object_instance(context, source_obj, target_loc, target_normal=None, coll_name="Spawned_Assets"):
    """
    Spawns a duplicate or linked duplicate of source_obj (and its children) at target_loc,
    applying rotation, scale variation, normal alignment, and Z-offset.
    """
    scene = context.scene
    
    # Target collection
    coll = bpy.data.collections.get(coll_name)
    if not coll:
        coll = bpy.data.collections.new(coll_name)
        context.scene.collection.children.link(coll)
        
    # Deselect all
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select hierarchy
    source_hierarchy = get_source_hierarchy(source_obj)
    for o in source_hierarchy:
        o.select_set(True)
    context.view_layer.objects.active = source_obj
    
    # Duplicate
    linked = getattr(scene, "hrg_mesh_link_dups", False)
    bpy.ops.object.duplicate(linked=linked)
    
    new_root = context.active_object
    new_hierarchy = [new_root] + list(new_root.children_recursive)
    
    # Ensure in target collection
    for obj in new_hierarchy:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)
        
    # Calculate transform adjustments
    # 1. Location + Z-offset
    z_off = getattr(scene, "hrg_mesh_z_offset", 0.0)
    final_loc = target_loc.copy()
    final_loc.z += z_off
    new_root.location = final_loc
    
    # 2. Random Rotation
    if getattr(scene, "hrg_mesh_random_rot", True):
        rot_z = random.uniform(0.0, 2.0 * math.pi)
        new_root.rotation_euler.z = rot_z
        
    # 3. Align to Surface Normal
    if getattr(scene, "hrg_mesh_align_normal", False) and target_normal:
        norm = mathutils.Vector(target_normal).normalized()
        up = mathutils.Vector((0.0, 0.0, 1.0))
        rot_quat = up.rotation_difference(norm)
        # Combine normal rotation with existing rotation
        mat = rot_quat.to_matrix().to_4x4() @ mathutils.Matrix.Rotation(new_root.rotation_euler.z, 4, 'Z')
        new_root.rotation_euler = mat.to_euler()
        
    # 4. Random Scale
    if getattr(scene, "hrg_mesh_random_scale", True):
        s_min = getattr(scene, "hrg_mesh_scale_min", 0.8)
        s_max = getattr(scene, "hrg_mesh_scale_max", 1.2)
        scale_fac = random.uniform(s_min, s_max)
        new_root.scale = new_root.scale * scale_fac
        
    return new_hierarchy

def draw_asset_spawner_hud(self, context):
    """Draws real-time overlay instructions in the 3D Viewport during click-to-spawn."""
    font_id = 0
    x, y = 30, 90
    
    src = get_target_source_object(context)
    src_name = src.name if src else "None (Select Mesh in Viewport)"
    count = getattr(context.scene, "hrg_mesh_spawn_count", 1)
    
    # Header banner
    blf.size(font_id, 18)
    blf.color(font_id, 0.2, 0.85, 0.4, 1.0) # Vibrant Emerald Green
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, f"ASSET & MESH SPAWNER (Target: '{src_name}' | Count: {count})")
    
    # Subtitle
    blf.size(font_id, 13)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0) # White
    blf.position(font_id, x, y - 24, 0)
    blf.draw(font_id, "Click anywhere on ground / surface / plane to spawn selected mesh")
    
    # Shortcuts
    blf.size(font_id, 12)
    blf.color(font_id, 0.8, 0.8, 0.8, 1.0) # Light Gray
    blf.position(font_id, x, y - 48, 0)
    blf.draw(font_id, "[Left-Click: Drop Mesh | Ctrl+Z: Undo Last | ESC / Right-Click / Enter: Finish]")

class OBJECT_OT_interactive_asset_spawner(bpy.types.Operator):
    """Click anywhere on a ground plane or mesh surface to spawn the selected Tree, House, or Object."""
    bl_idname = "object.interactive_asset_spawner"
    bl_label = "Click Anywhere to Spawn Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    _handle = None
    
    def modal(self, context, event):
        global _placed_batches
        context.area.tag_redraw()
        
        # Exit placement on ESC, Right-Click, Enter, Space
        if (event.type in {'ESC', 'RIGHTMOUSE', 'RET', 'NUMPAD_ENTER', 'SPACE'}) and event.value == 'PRESS':
            self.cleanup(context)
            self.report({'INFO'}, "Finished asset spawning.")
            return {'FINISHED'}
            
        # If mouse is outside the 3D window canvas (e.g. over sidebar panel), automatically exit
        if context.region.type != 'WINDOW':
            self.cleanup(context)
            return {'PASS_THROUGH'}
            
        # Ctrl+Z undo inside modal
        if event.ctrl and event.type == 'Z' and event.value == 'PRESS':
            if _placed_batches:
                last_batch = _placed_batches.pop()
                for obj in last_batch:
                    if obj and obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                context.area.tag_redraw()
                self.report({'INFO'}, "Undid last spawned mesh batch.")
            return {'RUNNING_MODAL'}
            
        # Navigation pass-through
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NDOF_MOTION'} or event.shift or event.alt:
            return {'PASS_THROUGH'}
            
        if event.type not in {'LEFTMOUSE'}:
            return {'PASS_THROUGH'}
            
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            src = get_target_source_object(context)
            if not src:
                self.report({'WARNING'}, "No source object selected! Select a tree, house, or mesh first.")
                return {'RUNNING_MODAL'}
                
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
                        normal = mathutils.Vector((0.0, 0.0, 1.0))
                        result = True
                        
            if result:
                count = max(1, getattr(context.scene, "hrg_mesh_spawn_count", 1))
                radius = getattr(context.scene, "hrg_mesh_spawn_radius", 3.0)
                coll_name = f"{src.name.split('.')[0]}_Spawned"
                
                batch_objects = []
                
                for i in range(count):
                    if i == 0 and count == 1:
                        target_pt = location.copy()
                        norm_pt = normal
                    elif i == 0:
                        target_pt = location.copy()
                        norm_pt = normal
                    else:
                        # Cluster / scatter offset around hit point
                        angle = random.uniform(0.0, 2.0 * math.pi)
                        dist = random.uniform(0.5, max(0.6, radius))
                        offset_x = math.cos(angle) * dist
                        offset_y = math.sin(angle) * dist
                        
                        target_pt = location + mathutils.Vector((offset_x, offset_y, 0.0))
                        
                        # Raycast down to find ground elevation at offset point
                        ray_down_origin = target_pt + mathutils.Vector((0.0, 0.0, 20.0))
                        ray_down_dir = mathutils.Vector((0.0, 0.0, -1.0))
                        res_down, loc_down, norm_down, _, _, _ = context.scene.ray_cast(depsgraph, ray_down_origin, ray_down_dir)
                        if res_down:
                            target_pt = loc_down
                            norm_pt = norm_down
                        else:
                            norm_pt = normal
                            
                    spawned_items = spawn_object_instance(context, src, target_pt, norm_pt, coll_name)
                    batch_objects.extend(spawned_items)
                    
                _placed_batches.append(batch_objects)
                
                context.area.tag_redraw()
                self.report({'INFO'}, f"Spawned {count}x '{src.name}' on surface.")
                
            return {'RUNNING_MODAL'}
            
        return {'PASS_THROUGH'}
        
    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Must be run from a 3D Viewport!")
            return {'CANCELLED'}
            
        src = get_target_source_object(context)
        if not src:
            self.report({'WARNING'}, "Please select a Mesh (Tree, House, Rock, etc.) to spawn!")
            return {'CANCELLED'}
            
        global _placed_batches
        _placed_batches = []
        
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_asset_spawner_hud, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}
        
    def cleanup(self, context):
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        context.area.tag_redraw()

class OBJECT_OT_scatter_selected_mesh(bpy.types.Operator):
    """Spawns/Scatters N copies of the selected mesh (trees, houses, etc.) across the surface or plane."""
    bl_idname = "object.scatter_selected_mesh"
    bl_label = "Scatter Meshes on Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        src = get_target_source_object(context)
        if not src:
            self.report({'WARNING'}, "Please select a Mesh (Tree, House, etc.) to scatter!")
            return {'CANCELLED'}
            
        count = max(1, getattr(scene, "hrg_mesh_spawn_count", 3))
        radius = getattr(scene, "hrg_mesh_spawn_radius", 10.0)
        center_loc = scene.cursor.location.copy()
        
        coll_name = f"{src.name.split('.')[0]}_Spawned"
        depsgraph = context.evaluated_depsgraph_get()
        
        spawned_total = 0
        for i in range(count):
            angle = random.uniform(0.0, 2.0 * math.pi)
            dist = random.uniform(0.2, radius)
            offset_x = math.cos(angle) * dist
            offset_y = math.sin(angle) * dist
            
            target_pt = center_loc + mathutils.Vector((offset_x, offset_y, 0.0))
            
            # Raycast down onto terrain/surface
            ray_origin = target_pt + mathutils.Vector((0.0, 0.0, 50.0))
            ray_dir = mathutils.Vector((0.0, 0.0, -1.0))
            res, loc_hit, norm_hit, _, _, _ = scene.ray_cast(depsgraph, ray_origin, ray_dir)
            
            if res:
                target_pt = loc_hit
                norm_target = norm_hit
            else:
                target_pt.z = 0.0
                norm_target = mathutils.Vector((0.0, 0.0, 1.0))
                
            spawn_object_instance(context, src, target_pt, norm_target, coll_name)
            spawned_total += 1
            
        context.view_layer.update()
        self.report({'INFO'}, f"Successfully scattered {spawned_total}x '{src.name}' into collection '{coll_name}'!")
        return {'FINISHED'}

class OBJECT_OT_spawn_mesh_at_cursor(bpy.types.Operator):
    """Spawns the selected mesh directly at the 3D Cursor location."""
    bl_idname = "object.spawn_mesh_at_cursor"
    bl_label = "Spawn at 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        src = get_target_source_object(context)
        if not src:
            self.report({'WARNING'}, "Please select a Mesh (Tree, House, etc.) to spawn!")
            return {'CANCELLED'}
            
        count = max(1, getattr(scene, "hrg_mesh_spawn_count", 1))
        radius = getattr(scene, "hrg_mesh_spawn_radius", 3.0)
        center_loc = scene.cursor.location.copy()
        coll_name = f"{src.name.split('.')[0]}_Spawned"
        
        for i in range(count):
            if i == 0:
                target_pt = center_loc.copy()
            else:
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(0.5, radius)
                target_pt = center_loc + mathutils.Vector((math.cos(angle)*dist, math.sin(angle)*dist, 0.0))
                
            spawn_object_instance(context, src, target_pt, mathutils.Vector((0.0, 0.0, 1.0)), coll_name)
            
        context.view_layer.update()
        self.report({'INFO'}, f"Spawned {count}x '{src.name}' at 3D Cursor!")
        return {'FINISHED'}

class OBJECT_OT_clear_spawned_assets(bpy.types.Operator):
    """Removes all spawned objects and clean up their collection."""
    bl_idname = "object.clear_spawned_assets"
    bl_label = "Clear Spawned Meshes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        src = get_target_source_object(context)
        target_colls = []
        if src:
            src_coll_name = f"{src.name.split('.')[0]}_Spawned"
            if src_coll_name in bpy.data.collections:
                target_colls.append(bpy.data.collections[src_coll_name])
                
        if "Spawned_Assets" in bpy.data.collections:
            target_colls.append(bpy.data.collections["Spawned_Assets"])
            
        # Also find any collection ending with _Spawned
        for coll in bpy.data.collections:
            if coll.name.endswith("_Spawned") and coll not in target_colls:
                target_colls.append(coll)
                
        if not target_colls:
            self.report({'INFO'}, "No spawned asset collections found.")
            return {'CANCELLED'}
            
        removed_count = 0
        for coll in target_colls:
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
                removed_count += 1
            bpy.data.collections.remove(coll)
            
        self.report({'INFO'}, f"Cleared {removed_count} spawned objects and removed collection(s).")
        return {'FINISHED'}

class OBJECT_OT_import_assets_from_blend(bpy.types.Operator, ImportHelper):
    """Imports Characters (Rig + Skinned Mesh), Objects, Trees, Houses, Rocks from another Blender project (.blend)."""
    bl_idname = "object.import_assets_from_blend"
    bl_label = "Import Assets / Character from Project"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty( # type: ignore
        name="Blender File",
        description="Select the Blender file (.blend) containing meshes, props, or characters",
        subtype='FILE_PATH'
    )
    
    filter_glob: bpy.props.StringProperty( # type: ignore
        default="*.blend",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    import_type: bpy.props.EnumProperty( # type: ignore
        name="Import Content",
        items=[
            ('ALL', "All Objects & Characters", "Imports all objects, characters, rigs, and assets from the project"),
            ('OBJECTS', "Meshes & Props Only", "Imports all mesh objects (trees, houses, rocks, props)"),
            ('CHARACTERS', "Characters & Rigs Only", "Imports armatures and their attached skinned meshes"),
        ],
        default='ALL'
    )
    
    def execute(self, context):
        if not self.filepath or not self.filepath.lower().endswith(".blend"):
            self.report({'WARNING'}, "Please select a valid Blender project file (.blend)!")
            return {'CANCELLED'}
            
        try:
            with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
                if not data_from.objects:
                    self.report({'WARNING'}, f"No objects found in '{os.path.basename(self.filepath)}'!")
                    return {'CANCELLED'}
                    
                if self.import_type == 'CHARACTERS':
                    data_to.objects = [name for name in data_from.objects if any(k in name.lower() for k in ["rig", "char", "actor", "body", "human", "armature"])]
                    if not data_to.objects:
                        data_to.objects = data_from.objects
                elif self.import_type == 'OBJECTS':
                    data_to.objects = [name for name in data_from.objects if not any(k in name.lower() for k in ["rig", "armature", "camera", "light"])]
                    if not data_to.objects:
                        data_to.objects = data_from.objects
                else:
                    data_to.objects = data_from.objects
                    
                # Also load actions if any exist
                if data_from.actions:
                    data_to.actions = data_from.actions
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load assets from '{os.path.basename(self.filepath)}': {e}")
            return {'CANCELLED'}
            
        imported_objs = [o for o in data_to.objects if o is not None]
        if not imported_objs:
            self.report({'WARNING'}, "No objects were imported!")
            return {'CANCELLED'}
            
        # Target collection
        coll_name = "Imported_Assets"
        target_coll = bpy.data.collections.get(coll_name)
        if not target_coll:
            target_coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(target_coll)
            
        for obj in imported_objs:
            if obj.name not in target_coll.objects:
                target_coll.objects.link(obj)
                
        # Link imported actions with fake user
        if hasattr(data_to, "actions") and data_to.actions:
            for act in data_to.actions:
                if act:
                    act.use_fake_user = True
                    
        # If an armature was imported, retarget constraints
        from .animation import retarget_rig_internal_constraints
        imported_armatures = [o for o in imported_objs if o.type == 'ARMATURE']
        for arm in imported_armatures:
            retarget_rig_internal_constraints(arm)
            
        # If mesh was imported, select the first mesh and set as spawn source object
        imported_meshes = [o for o in imported_objs if o.type == 'MESH']
        if imported_meshes:
            context.scene.hrg_spawn_source_obj = imported_meshes[0]
            if hasattr(context.scene, "hrg_prop_source_obj"):
                context.scene.hrg_prop_source_obj = imported_meshes[0]
                
        # Deselect all and select imported
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        for o in context.selected_objects:
            o.select_set(False)
            
        for o in imported_objs:
            o.select_set(True)
            
        if imported_objs:
            context.view_layer.objects.active = imported_objs[0]
            
        context.view_layer.update()
        self.report({'INFO'}, f"Successfully imported {len(imported_objs)} objects from '{os.path.basename(self.filepath)}' into '{coll_name}'!")
        return {'FINISHED'}
