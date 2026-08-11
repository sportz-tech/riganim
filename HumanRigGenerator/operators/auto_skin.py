# operators/auto_skin.py
import bpy

class OBJECT_OT_auto_skin_mesh(bpy.types.Operator):
    """Automatically skins/binds the selected mesh to the generated rig with automatic weight painting."""
    bl_idname = "object.auto_skin_mesh"
    bl_label = "Auto-Skin Mesh to Rig"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        rig_type = context.scene.hrg_rig_type
        
        # 1. Resolve all selected meshes
        selected_meshes = [o for o in context.selected_objects if o.type == 'MESH']
        if not selected_meshes:
            mesh_obj = context.active_object
            if mesh_obj and mesh_obj.type == 'MESH':
                selected_meshes = [mesh_obj]
                
        if not selected_meshes:
            self.report({'WARNING'}, "Please select at least one character Mesh model first!")
            return {'CANCELLED'}
            
        # Expand selected_meshes to include all character sub-meshes automatically (eyes, teeth, tongue, hair, etc.)
        first_mesh = selected_meshes[0]
        discovered_meshes = list(selected_meshes)
        
        prefix_sub = ""
        if "_" in first_mesh.name:
            parts = first_mesh.name.split("_")
            if len(parts) > 1:
                prefix_sub = "_".join(parts[:-1]) + "_"
                
        import mathutils
        first_mesh_center = first_mesh.matrix_world @ (sum((mathutils.Vector(b) for b in first_mesh.bound_box), mathutils.Vector()) / 8.0)
        
        # Calculate character height dynamically to scale distance check
        bbox_world = [first_mesh.matrix_world @ mathutils.Vector(b) for b in first_mesh.bound_box]
        min_z = min(v.z for v in bbox_world)
        max_z = max(v.z for v in bbox_world)
        char_height = max_z - min_z
        closeness_threshold = max(1.2, char_height * 0.75)
        
        for o in context.scene.objects:
            if o.type == 'MESH' and o not in discovered_meshes:
                try:
                    if not o.visible_get():
                        continue
                except:
                    continue
                if any(x in o.name for x in ["Mkr", "Rig", "Wgt", "Widget", "Camera", "Light"]):
                    continue
                
                is_sub_mesh = False
                if prefix_sub != "" and o.name.startswith(prefix_sub):
                    is_sub_mesh = True
                else:
                    o_center = o.matrix_world @ (sum((mathutils.Vector(b) for b in o.bound_box), mathutils.Vector()) / 8.0)
                    if (o_center - first_mesh_center).length < closeness_threshold:
                        is_sub_mesh = True
                        
                # Also include by name keywords regardless of prefix
                if not is_sub_mesh:
                    o_name_lower = o.name.lower()
                    if any(k in o_name_lower for k in ["hair", "eye", "teeth", "tooth", "tongue", "lash", "eyebrow", "brow", "tear", "mouth", "glass", "eyelid"]):
                        o_center = o.matrix_world @ (sum((mathutils.Vector(b) for b in o.bound_box), mathutils.Vector()) / 8.0)
                        if (o_center - first_mesh_center).length < closeness_threshold * 1.5:
                            is_sub_mesh = True
                            
                if is_sub_mesh:
                    discovered_meshes.append(o)
                    
        selected_meshes = discovered_meshes
        
        # Guess corresponding rig from first selected mesh
        first_mesh = selected_meshes[0]
        rig_obj = None
        
        expected_rig_name = f"{first_mesh.name}_Rig"
        rig_obj = bpy.data.objects.get(expected_rig_name)
        
        if not rig_obj:
            for o in context.selected_objects:
                if o.type == 'ARMATURE':
                    rig_obj = o
                    break
                    
        if not rig_obj:
            default_rig_name = f"{rig_type.capitalize()}_Rig"
            for o in context.scene.objects:
                if o.type == 'ARMATURE' and (o.name.startswith(default_rig_name) or o.name.endswith("_Rig")):
                    rig_obj = o
                    break
                    
        if not rig_obj:
            self.report({'WARNING'}, f"Corresponding rig not found! Please generate a rig for your character first.")
            return {'CANCELLED'}
            
        # Extract prefix from the rig name robustly (e.g. "CC_Base_Body_Rig" -> "CC_Base_Body_")
        rig_name = rig_obj.name
        prefix = ""
        if "_Rig" in rig_name:
            prefix = rig_name.split("_Rig")[0] + "_"
        elif "Rig" in rig_name:
            prefix = rig_name.split("Rig")[0]
        
        import traceback
        import mathutils
        log_path = "f:\\blenderaddon\\HumanRigGenerator\\auto_skin_debug.log"
        
        # Ensure we are in Object Mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        with open(log_path, "w") as log_file:
            log_file.write(f"--- AUTO SKINNING LOG ---\n")
            log_file.write(f"Rig: {rig_obj.name}\n")
            log_file.write(f"Meshes to skin: {[m.name for m in selected_meshes]}\n")
            
            for mesh_obj in selected_meshes:
                log_file.write(f"\nProcessing Mesh: {mesh_obj.name}\n")
                

                
                # Check if this mesh is a separate eyeball object
                is_eyeball_mesh = False
                if "eye" in mesh_obj.name.lower() and not any(x in mesh_obj.name.lower() for x in ["eyelid", "eyebrow", "brow", "lash", "corner", "occlusion"]):
                    is_eyeball_mesh = True
                    
                if is_eyeball_mesh:
                    log_file.write(f"Detected separate eyeball mesh object '{mesh_obj.name}'.\n")
                    
                    # 1. Clear original parenting and parent directly to the new rig
                    matrix_world = mesh_obj.matrix_world.copy()
                    mesh_obj.parent = None
                    mesh_obj.matrix_world = matrix_world
                    mesh_obj.parent = rig_obj
                    mesh_obj.parent_type = 'OBJECT'
                    mesh_obj.matrix_world = matrix_world
                    log_file.write("Cleared parenting and reparented eyeball mesh to rig object.\n")
                    
                    # 2. Clean existing modifiers and vertex groups
                    for mod in list(mesh_obj.modifiers):
                        if mod.type == 'ARMATURE':
                            mesh_obj.modifiers.remove(mod)
                    for vg in list(mesh_obj.vertex_groups):
                        mesh_obj.vertex_groups.remove(vg)
                        
                    # 3. Apply transforms
                    bpy.ops.object.select_all(action='DESELECT')
                    try:
                        mesh_obj.select_set(True)
                        context.view_layer.objects.active = mesh_obj
                    except:
                        pass
                    try:
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                        log_file.write("Applied transforms to eyeball mesh\n")
                    except Exception as e_apply:
                        log_file.write(f"Transform apply failed on eyeball: {e_apply}\n")
                        
                    # 4. Check if it is a combined or single eyeball mesh based on bounding box center
                    bbox_coords = [mathutils.Vector(b) for b in mesh_obj.bound_box]
                    center_x = sum(v.x for v in bbox_coords) / 8.0
                    
                    if abs(center_x) < 0.015:
                        # Combined eyeballs: split by X = 0
                        vg_left = mesh_obj.vertex_groups.new(name="DEF-eye.L")
                        vg_right = mesh_obj.vertex_groups.new(name="DEF-eye.R")
                        left_v = []
                        right_v = []
                        for v in mesh_obj.data.vertices:
                            if v.co.x > 0.0:
                                left_v.append(v.index)
                            else:
                                right_v.append(v.index)
                        if left_v:
                            vg_left.add(left_v, 1.0, 'REPLACE')
                        if right_v:
                            vg_right.add(right_v, 1.0, 'REPLACE')
                        log_file.write(f"Combined eyeball split: {len(left_v)} left, {len(right_v)} right vertices.\n")
                    else:
                        # Single eyeball
                        target_eye_bone = "DEF-eye.L" if center_x > 0.0 else "DEF-eye.R"
                        vg = mesh_obj.vertex_groups.new(name=target_eye_bone)
                        all_v_indices = [v.index for v in mesh_obj.data.vertices]
                        vg.add(all_v_indices, 1.0, 'REPLACE')
                        log_file.write(f"Single eyeball assigned to {target_eye_bone}.\n")
                        
                    # 5. Add Armature Modifier
                    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
                    mod.object = rig_obj
                    log_file.write(f"Eyeball skinning for '{mesh_obj.name}' succeeded!\n")
                    continue
                
                # Check if this mesh is a separate teeth or mouth-internal object (like tongue)
                is_mouth_internal = False
                if any(x in mesh_obj.name.lower() for x in ["teeth", "tooth", "dental", "tongue"]):
                    is_mouth_internal = True
                    
                if is_mouth_internal:
                    log_file.write(f"Detected separate mouth internal mesh object '{mesh_obj.name}'. Binding to DEF-head and DEF-jaw.\n")
                    
                    # 1. Clear original parenting and parent directly to the new rig
                    matrix_world = mesh_obj.matrix_world.copy()
                    mesh_obj.parent = None
                    mesh_obj.matrix_world = matrix_world
                    mesh_obj.parent = rig_obj
                    mesh_obj.parent_type = 'OBJECT'
                    mesh_obj.matrix_world = matrix_world
                    log_file.write("Cleared parenting and reparented mouth-internal mesh to rig object.\n")
                    
                    # 2. Clean existing modifiers and vertex groups
                    for mod in list(mesh_obj.modifiers):
                        if mod.type == 'ARMATURE':
                            mesh_obj.modifiers.remove(mod)
                    for vg in list(mesh_obj.vertex_groups):
                        mesh_obj.vertex_groups.remove(vg)
                        
                    # 2. Apply transforms
                    bpy.ops.object.select_all(action='DESELECT')
                    try:
                        mesh_obj.select_set(True)
                        context.view_layer.objects.active = mesh_obj
                    except:
                        pass
                    try:
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                    except:
                        pass
                        
                    # 3. Separate upper and lower vertices by Z coordinate
                    vg_head = mesh_obj.vertex_groups.new(name="DEF-head")
                    vg_jaw = mesh_obj.vertex_groups.new(name="DEF-jaw")
                    
                    bbox_coords = [mathutils.Vector(b) for b in mesh_obj.bound_box]
                    center_z = sum(v.z for v in bbox_coords) / 8.0
                    
                    # Find the gap between upper and lower vertices robustly (largest Z gap in the middle region)
                    coords_z = sorted([v.co.z for v in mesh_obj.data.vertices])
                    n = len(coords_z)
                    split_z = center_z
                    if n > 10:
                        start_idx = int(n * 0.2)
                        end_idx = int(n * 0.8)
                        max_gap = -1.0
                        for idx in range(start_idx, end_idx):
                            gap = coords_z[idx+1] - coords_z[idx]
                            if gap > max_gap:
                                max_gap = gap
                                split_z = (coords_z[idx] + coords_z[idx+1]) / 2.0
                                
                    upper_v = []
                    lower_v = []
                    
                    if any(x in mesh_obj.name.lower() for x in ["upper", "top"]):
                        upper_v = [v.index for v in mesh_obj.data.vertices]
                    elif any(x in mesh_obj.name.lower() for x in ["lower", "bottom", "jaw"]):
                        lower_v = [v.index for v in mesh_obj.data.vertices]
                    elif "tongue" in mesh_obj.name.lower():
                        # Tongue is entirely on the lower jaw
                        lower_v = [v.index for v in mesh_obj.data.vertices]
                    else:
                        for v in mesh_obj.data.vertices:
                            if v.co.z > split_z:
                                upper_v.append(v.index)
                            else:
                                lower_v.append(v.index)
                                
                    if upper_v:
                        vg_head.add(upper_v, 1.0, 'REPLACE')
                        log_file.write(f"Assigned {len(upper_v)} upper vertices to DEF-head.\n")
                    if lower_v:
                        vg_jaw.add(lower_v, 1.0, 'REPLACE')
                        log_file.write(f"Assigned {len(lower_v)} lower vertices to DEF-jaw.\n")
                        
                    # 4. Add Armature Modifier
                    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
                    mod.object = rig_obj
                    log_file.write(f"Mouth-internal skinning for '{mesh_obj.name}' succeeded!\n")
                    continue
                
                # Full auto-skinning process for standard body meshes
                # 1. Clear original parenting and parent directly to the new rig
                matrix_world = mesh_obj.matrix_world.copy()
                mesh_obj.parent = None
                mesh_obj.matrix_world = matrix_world
                mesh_obj.parent = rig_obj
                mesh_obj.parent_type = 'OBJECT'
                mesh_obj.matrix_world = matrix_world
                log_file.write("Cleared parenting and reparented body mesh to rig object.\n")
                
                # 2. Surgical Cleanup
                for mod in list(mesh_obj.modifiers):
                    if mod.type == 'ARMATURE':
                        mesh_obj.modifiers.remove(mod)
                        
                bone_names = {b.name for b in rig_obj.data.bones}
                for vg in list(mesh_obj.vertex_groups):
                    if vg.name in bone_names or vg.name.startswith("DEF-") or vg.name.startswith("ORG-") or vg.name.startswith("MCH-"):
                        mesh_obj.vertex_groups.remove(vg)
                        
                # Apply Mirror modifier if present to ensure full geometry exists physically for skinning and symmetry cleanup
                for mod in list(mesh_obj.modifiers):
                    if mod.type == 'MIRROR':
                        try:
                            bpy.ops.object.select_all(action='DESELECT')
                            mesh_obj.select_set(True)
                            context.view_layer.objects.active = mesh_obj
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                            log_file.write(f"Applied mirror modifier: {mod.name}\n")
                        except Exception as e_mirror:
                            log_file.write(f"Failed to apply mirror modifier {mod.name}: {e_mirror}\n")
                        
                # 2. Apply transforms
                bpy.ops.object.select_all(action='DESELECT')
                try:
                    mesh_obj.select_set(True)
                    context.view_layer.objects.active = mesh_obj
                except:
                    pass
                try:
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                except:
                    pass
                    
                # Heal mesh
                try:
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.object.mode_set(mode='OBJECT')
                    v_count_before = len(mesh_obj.data.vertices)
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.remove_doubles(threshold=0.001)
                    bpy.ops.mesh.normals_make_consistent(inside=False)
                    bpy.ops.object.mode_set(mode='OBJECT')
                    v_count_after = len(mesh_obj.data.vertices)
                    log_file.write(f"Mesh healed. Vertices removed: {v_count_before - v_count_after}\n")
                except Exception as e_heal:
                    log_file.write(f"Heal mesh failed: {e_heal}\n")
                    if mesh_obj.mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                        
                # Backup and disable all pose constraints during skinning
                constraints_backup = []
                for pb in rig_obj.pose.bones:
                    for c in pb.constraints:
                        constraints_backup.append((pb.name, c.name, c.enabled))
                        c.enabled = False
                        
                # Backup and clear pose transforms so parenting happens at clean rest T-pose
                pose_backup = {}
                for pb in rig_obj.pose.bones:
                    pose_backup[pb.name] = (
                        pb.location.copy(),
                        pb.rotation_quaternion.copy(),
                        list(pb.rotation_axis_angle),
                        pb.rotation_euler.copy(),
                        pb.scale.copy()
                    )
                    pb.location = (0, 0, 0)
                    pb.rotation_quaternion = (1, 0, 0, 0)
                    pb.rotation_axis_angle = (0, 0, 1, 0)
                    pb.rotation_euler = (0, 0, 0)
                    pb.scale = (1, 1, 1)
                    
                temp_disabled_bones = []
                
                # Execute parenting
                bpy.ops.object.select_all(action='DESELECT')
                mesh_obj.select_set(True)
                rig_obj.select_set(True)
                context.view_layer.objects.active = rig_obj
                
                # Try ARMATURE_AUTO (Bone Heat) first
                parenting_success = False
                try:
                    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
                    total_weights = sum(len(v.groups) for v in mesh_obj.data.vertices)
                    if total_weights > 0:
                        log_file.write("ARMATURE_AUTO parenting succeeded with valid weights!\n")
                        parenting_success = True
                except Exception as e:
                    log_file.write(f"ARMATURE_AUTO parenting failed: {e}\n")
                    
                # If Bone Heat failed or returned 0 weights, fall back to Envelope parenting
                if not parenting_success:
                    log_file.write("Falling back to ARMATURE_ENVELOPE (Envelope Weights)...\n")
                    for mod in list(mesh_obj.modifiers):
                        if mod.type == 'ARMATURE':
                            mesh_obj.modifiers.remove(mod)
                    for vg in list(mesh_obj.vertex_groups):
                        mesh_obj.vertex_groups.remove(vg)
                        
                    bpy.ops.object.select_all(action='DESELECT')
                    mesh_obj.select_set(True)
                    rig_obj.select_set(True)
                    context.view_layer.objects.active = rig_obj
                    
                    try:
                        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
                        total_weights = sum(len(v.groups) for v in mesh_obj.data.vertices)
                        if total_weights > 0:
                            log_file.write("ARMATURE_ENVELOPE parenting succeeded with valid weights!\n")
                            parenting_success = True
                    except Exception as e:
                        log_file.write(f"ARMATURE_ENVELOPE parenting failed: {e}\n")
                        
                # If Envelope also failed or returned 0 weights, fall back to ARMATURE_NAME (Empty Groups)
                if not parenting_success:
                    log_file.write("Falling back to ARMATURE_NAME (Empty Groups)...\n")
                    for mod in list(mesh_obj.modifiers):
                        if mod.type == 'ARMATURE':
                            mesh_obj.modifiers.remove(mod)
                    for vg in list(mesh_obj.vertex_groups):
                        mesh_obj.vertex_groups.remove(vg)
                        
                    bpy.ops.object.select_all(action='DESELECT')
                    mesh_obj.select_set(True)
                    rig_obj.select_set(True)
                    context.view_layer.objects.active = rig_obj
                    
                    try:
                        bpy.ops.object.parent_set(type='ARMATURE_NAME')
                        log_file.write("ARMATURE_NAME parenting succeeded!\n")
                    except Exception as e:
                        log_file.write(f"ARMATURE_NAME parenting failed: {e}\n")
                        
                for b_name in temp_disabled_bones:
                    bone = rig_obj.data.bones.get(b_name)
                    if bone:
                        bone.use_deform = True
                        if b_name not in mesh_obj.vertex_groups:
                            mesh_obj.vertex_groups.new(name=b_name)
                            
                # Check if there is any separate eyeball mesh in the scene
                has_separate_eyeball_objs = False
                for o in bpy.data.objects:
                    if o.type == 'MESH' and o != mesh_obj:
                        if "eye" in o.name.lower() and not any(x in o.name.lower() for x in ["eyelid", "eyebrow", "brow", "lash", "corner"]):
                            has_separate_eyeball_objs = True
                            break
                            
                if not has_separate_eyeball_objs:
                    # Automatically assign eyeball weights to eye deforming bones inside body mesh
                    try:
                        adj = {i: set() for i in range(len(mesh_obj.data.vertices))}
                        for edge in mesh_obj.data.edges:
                            u, v = edge.vertices
                            adj[u].add(v)
                            adj[v].add(u)
                            
                        for side in [".L", ".R"]:
                            eye_bone_name = f"DEF-eye{side}"
                            eye_pb = rig_obj.pose.bones.get(eye_bone_name)
                            if eye_pb:
                                eye_pos = rig_obj.matrix_world @ eye_pb.head
                                threshold = 0.022
                                vg = mesh_obj.vertex_groups.get(eye_bone_name)
                                if vg:
                                    mesh_obj.vertex_groups.remove(vg)
                                    bpy.context.view_layer.update()
                                vg = mesh_obj.vertex_groups.new(name=eye_bone_name)
                                    
                                seed_indices = []
                                mw = mesh_obj.matrix_world
                                for v in mesh_obj.data.vertices:
                                    v_world = mw @ v.co
                                    if (v_world - eye_pos).length < 0.018:
                                        seed_indices.append(v.index)
                                        
                                vertices_to_assign = []
                                if seed_indices:
                                    visited = set(seed_indices)
                                    queue = list(seed_indices)
                                    head = 0
                                    while head < len(queue):
                                        curr = queue[head]
                                        head += 1
                                        for neighbor in adj[curr]:
                                            if neighbor not in visited:
                                                v_neigh_world = mw @ mesh_obj.data.vertices[neighbor].co
                                                if (v_neigh_world - eye_pos).length < threshold:
                                                    visited.add(neighbor)
                                                    queue.append(neighbor)
                                    visited_list = list(visited)
                                    
                                    for other_vg in mesh_obj.vertex_groups:
                                        if other_vg.name != eye_bone_name:
                                            other_vg.remove(visited_list)
                                    vg.add(visited_list, 1.0, 'REPLACE')
                                    log_file.write(f"Assigned {len(visited_list)} body eyeball vertices to {eye_bone_name}.\n")
                    except Exception as e_eye:
                        log_file.write(f"Eyeball BFS solver failed: {e_eye}. Moving on...\n")
                else:
                    log_file.write("Skipping eyeball BFS solver because separate eyeball objects exist in the scene.\n")
                    # Clear weights from eye deforming groups on body mesh to avoid automatic weight pollution
                    for side in [".L", ".R"]:
                        vg_eye = mesh_obj.vertex_groups.get(f"DEF-eye{side}")
                        if vg_eye:
                            vg_eye.remove(list(range(len(mesh_obj.data.vertices))))
                            log_file.write(f"Cleared vertex weights of DEF-eye{side} from body mesh '{mesh_obj.name}' because separate eyeballs exist.\n")
                    
                # Custom smooth eyelid weight painter to close eyelids completely at corners using corner markers
                try:
                    for side in [".L", ".R"]:
                        eye_bone_name = f"DEF-eye{side}"
                        up_lid_name = f"DEF-eyelid.upper{side}"
                        low_lid_name = f"DEF-eyelid.lower{side}"
                        head_bone_name = "DEF-head"
                        
                        eye_pb = rig_obj.pose.bones.get(eye_bone_name)
                        up_lid_pb = rig_obj.pose.bones.get(up_lid_name)
                        low_lid_pb = rig_obj.pose.bones.get(low_lid_name)
                        
                        if eye_pb and up_lid_pb and low_lid_pb:
                            eye_pos = rig_obj.matrix_world @ eye_pb.head
                            
                            # Retrieve placed corner markers to dynamically compute eye shape widths
                            corner_inner = bpy.data.objects.get(f"{prefix}Mkr_eye_corner_inner{side}")
                            corner_outer = bpy.data.objects.get(f"{prefix}Mkr_eye_corner_outer{side}")
                            
                            p_inner = eye_pos + mathutils.Vector((-0.02, 0.0, 0.0)) if side == ".L" else eye_pos + mathutils.Vector((0.02, 0.0, 0.0))
                            p_outer = eye_pos + mathutils.Vector((0.02, 0.0, 0.0)) if side == ".L" else eye_pos + mathutils.Vector((-0.02, 0.0, 0.0))
                            
                            if corner_inner:
                                p_inner = corner_inner.location.copy()
                            if corner_outer:
                                p_outer = corner_outer.location.copy()
                                
                            width_inner = (p_inner - eye_pos).length
                            width_outer = (p_outer - eye_pos).length
                            
                            vg_up = mesh_obj.vertex_groups.get(up_lid_name) or mesh_obj.vertex_groups.new(name=up_lid_name)
                            vg_low = mesh_obj.vertex_groups.get(low_lid_name) or mesh_obj.vertex_groups.new(name=low_lid_name)
                            vg_eye = mesh_obj.vertex_groups.get(eye_bone_name)
                            vg_head = mesh_obj.vertex_groups.get(head_bone_name) or mesh_obj.vertex_groups.new(name=head_bone_name)
                            
                            corner_inner_name = f"DEF-eye_corner.inner{side}"
                            corner_outer_name = f"DEF-eye_corner.outer{side}"
                            vg_corner_inner = mesh_obj.vertex_groups.get(corner_inner_name) or mesh_obj.vertex_groups.new(name=corner_inner_name)
                            vg_corner_outer = mesh_obj.vertex_groups.get(corner_outer_name) or mesh_obj.vertex_groups.new(name=corner_outer_name)
                            
                            mw = mesh_obj.matrix_world
                            R_max = max(0.040, max(width_inner, width_outer) * 1.3)
                            
                            for v in mesh_obj.data.vertices:
                                v_world = mw @ v.co
                                dist = (v_world - eye_pos).length
                                
                                if dist < R_max:
                                    # Skip separate eyeball vertices if any
                                    if has_separate_eyeball_objs:
                                        continue
                                    # Skip integrated eyeball vertices (painted to eye bone)
                                    if vg_eye:
                                        is_eyeball = False
                                        for g in v.groups:
                                            if g.group == vg_eye.index:
                                                is_eyeball = True
                                                break
                                        if is_eyeball:
                                            continue
                                            
                                    # Clean up all other vertex groups to ensure clean normalized weight sum (exactly 1.0)
                                    allowed_groups = {vg_up.index, vg_low.index, vg_corner_inner.index, vg_corner_outer.index, vg_head.index}
                                    for g in list(v.groups):
                                        if g.group not in allowed_groups:
                                            for vg in mesh_obj.vertex_groups:
                                                if vg.index == g.group:
                                                    try:
                                                        vg.remove([v.index])
                                                    except:
                                                        pass
                                                        
                                    # Influence falloff from center of eye to socket boundary
                                    influence = max(0.0, min(1.0, 1.0 - (dist / R_max)))
                                    influence = influence * influence * (3.0 - 2.0 * influence)
                                    
                                    dx = abs(v_world.x - eye_pos.x)
                                    is_inner = (v_world.x < eye_pos.x) if side == ".L" else (v_world.x > eye_pos.x)
                                    width = width_inner if is_inner else width_outer
                                    
                                    # Horizontal factor (1.0 at center, 0.0 at corner)
                                    factor = max(0.0, min(1.0, 1.0 - (dx / max(0.005, width))))
                                    factor = factor * factor * (3.0 - 2.0 * factor)
                                    
                                    vg_corner = vg_corner_inner if is_inner else vg_corner_outer
                                    
                                    # Split upper and lower eyelids along the slanted seam connecting inner and outer corners
                                    dx_total = p_outer.x - p_inner.x
                                    if abs(dx_total) > 0.001:
                                        t = (v_world.x - p_inner.x) / dx_total
                                        t = max(0.0, min(1.0, t))
                                        split_z = p_inner.z + t * (p_outer.z - p_inner.z)
                                    else:
                                        split_z = eye_pos.z
                                        
                                    is_upper = (v_world.z > split_z)
                                    
                                    w_eyelid = influence * factor
                                    w_corner = influence * (1.0 - factor)
                                    w_head = 1.0 - influence
                                    
                                    if is_upper:
                                        vg_up.add([v.index], w_eyelid, 'REPLACE')
                                        try:
                                            vg_low.remove([v.index])
                                        except:
                                            pass
                                    else:
                                        vg_low.add([v.index], w_eyelid, 'REPLACE')
                                        try:
                                            vg_up.remove([v.index])
                                        except:
                                            pass
                                            
                                    vg_corner.add([v.index], w_corner, 'REPLACE')
                                    vg_head.add([v.index], w_head, 'REPLACE')
                                else:
                                    # Completely remove these vertices from all eyelid and corner bones
                                    # to ensure absolutely zero movement on cheeks/nose/head!
                                    try:
                                        vg_up.remove([v.index])
                                    except:
                                        pass
                                    try:
                                        vg_low.remove([v.index])
                                    except:
                                        pass
                                    try:
                                        vg_corner_inner.remove([v.index])
                                    except:
                                        pass
                                    try:
                                        vg_corner_outer.remove([v.index])
                                    except:
                                        pass
                    log_file.write("Completed custom smooth eyelid weight painting.\n")
                except Exception as e_lids:
                    log_file.write(f"Eyelid weight painting failed: {e_lids}\n")
                    
                # Symmetrical limb weight cleanup
                try:
                    pelvis_pb = rig_obj.pose.bones.get("DEF-pelvis")
                    center_x = 0.0
                    if pelvis_pb:
                        center_x = (rig_obj.matrix_world @ pelvis_pb.head).x
                    left_is_positive_x = True
                    l_thigh_pb = rig_obj.pose.bones.get("DEF-thigh.L")
                    if l_thigh_pb:
                        l_thigh_x = (rig_obj.matrix_world @ l_thigh_pb.head).x
                        left_is_positive_x = (l_thigh_x > center_x)
                        
                    vg_left = [vg for vg in mesh_obj.vertex_groups if vg.name.endswith(".L")]
                    vg_right = [vg for vg in mesh_obj.vertex_groups if vg.name.endswith(".R")]
                    
                    cleaned_left = 0
                    cleaned_right = 0
                    mw = mesh_obj.matrix_world
                    for v in mesh_obj.data.vertices:
                        v_world_x = (mw @ v.co).x
                        if abs(v_world_x - center_x) > 0.01:
                            is_on_left_side = (v_world_x > center_x) if left_is_positive_x else (v_world_x < center_x)
                            if is_on_left_side:
                                for vg in vg_right:
                                    vg.remove([v.index])
                                cleaned_left += 1
                            else:
                                for vg in vg_left:
                                    vg.remove([v.index])
                                cleaned_right += 1
                    log_file.write(f"Symmetrical cleanup: removed cross-leg weight bleed for {cleaned_left} left and {cleaned_right} right vertices.\n")
                # Spine and Pelvis weight de-pinching
                try:
                    pelvis_pb = rig_obj.pose.bones.get("DEF-pelvis")
                    spine_pb = rig_obj.pose.bones.get("DEF-spine")
                    if pelvis_pb and spine_pb:
                        p_head_z = (rig_obj.matrix_world @ pelvis_pb.head).z
                        vg_pelvis = mesh_obj.vertex_groups.get("DEF-pelvis")
                        if vg_pelvis:
                            mw = mesh_obj.matrix_world
                            # Clear DEF-pelvis from upper waist / abdomen above pelvis head + 0.025
                            upper_waist = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z > p_head_z + 0.025]
                            if upper_waist:
                                vg_pelvis.remove(upper_waist)
                                log_file.write(f"Removed DEF-pelvis bleed from {len(upper_waist)} upper waist vertices to prevent twisting/pinching.\n")
                except Exception as e_spine:
                    log_file.write(f"Spine de-pinching failed: {e_spine}\n")
                    
                # Foot and Toe weight cleanup
                try:
                    bpy.context.view_layer.update()
                    pelvis_pb = rig_obj.pose.bones.get("DEF-pelvis")
                    center_x = 0.0
                    if pelvis_pb:
                        center_x = (rig_obj.matrix_world @ pelvis_pb.head).x
                    left_is_positive_x = True
                    l_thigh_pb = rig_obj.pose.bones.get("DEF-thigh.L")
                    if l_thigh_pb:
                        l_thigh_x = (rig_obj.matrix_world @ l_thigh_pb.head).x
                        left_is_positive_x = (l_thigh_x > center_x)
                        
                    for side in [".L", ".R"]:
                        foot_name = f"DEF-foot{side}"
                        toe_name = f"DEF-toe{side}"
                        foot_vg = mesh_obj.vertex_groups.get(foot_name) or mesh_obj.vertex_groups.new(name=foot_name)
                        toe_vg = mesh_obj.vertex_groups.get(toe_name) or mesh_obj.vertex_groups.new(name=toe_name)
                        
                        foot_pb = rig_obj.pose.bones.get(foot_name)
                        toe_pb = rig_obj.pose.bones.get(toe_name)
                        ankle_z = 0.0
                        
                        marker_obj = bpy.data.objects.get(f"Mkr_ankle{side}")
                        if marker_obj:
                            ankle_z = marker_obj.location.z
                        elif foot_pb:
                            ankle_z = (rig_obj.matrix_world @ foot_pb.head).z
                            
                        if foot_pb and toe_pb and ankle_z > 0.0:
                            f_head = rig_obj.matrix_world @ foot_pb.head
                            f_tail = rig_obj.matrix_world @ foot_pb.tail
                            t_head = rig_obj.matrix_world @ toe_pb.head
                            t_tail = rig_obj.matrix_world @ toe_pb.tail
                            mw = mesh_obj.matrix_world
                            
                            assigned_foot = 0
                            assigned_toe = 0
                            for v in mesh_obj.data.vertices:
                                v_world = mw @ v.co
                                if v_world.z < ankle_z - 0.005:
                                    is_on_left_side = (v_world.x > center_x) if left_is_positive_x else (v_world.x < center_x)
                                    correct_side = (side == ".L" and is_on_left_side) or (side == ".R" and not is_on_left_side)
                                    if correct_side:
                                        _, f_t = mathutils.geometry.intersect_point_line(v_world, f_head, f_tail)
                                        f_t = max(0.0, min(1.0, f_t))
                                        f_closest = f_head + f_t * (f_tail - f_head)
                                        f_dist = (v_world - f_closest).length
                                        
                                        _, t_t = mathutils.geometry.intersect_point_line(v_world, t_head, t_tail)
                                        t_t = max(0.0, min(1.0, t_t))
                                        t_closest = t_head + t_t * (t_tail - t_head)
                                        t_dist = (v_world - t_closest).length
                                        
                                        if f_dist < t_dist:
                                            for vg in mesh_obj.vertex_groups:
                                                if vg != foot_vg:
                                                    vg.remove([v.index])
                                            foot_vg.add([v.index], 1.0, 'REPLACE')
                                            assigned_foot += 1
                                        else:
                                            for vg in mesh_obj.vertex_groups:
                                                if vg != toe_vg:
                                                    vg.remove([v.index])
                                            toe_vg.add([v.index], 1.0, 'REPLACE')
                                            assigned_toe += 1
                            log_file.write(f"Foot weight cleanup ({side}) at Z={ankle_z:.4f}: assigned {assigned_foot} to foot, {assigned_toe} to toe.\n")
                except Exception as e_foot:
                    log_file.write(f"Foot cleanup failed: {e_foot}\n")
                    
                # Auto-assign any unweighted vertices (like loose ponytail strands) to the nearest deforming bone
                try:
                    assign_unweighted_vertices(mesh_obj, rig_obj, log_file)
                except Exception as e_unweighted:
                    log_file.write(f"Assign unweighted vertices failed: {e_unweighted}\n")
                    
                # Restore original pose transforms for this mesh
                for b_name, transforms in pose_backup.items():
                    pb = rig_obj.pose.bones.get(b_name)
                    if pb:
                        pb.location = transforms[0]
                        pb.rotation_quaternion = transforms[1]
                        pb.rotation_axis_angle = transforms[2]
                        pb.rotation_euler = transforms[3]
                        pb.scale = transforms[4]
                        
                # Restore original constraints
                for pb_name, c_name, enabled in constraints_backup:
                    pb = rig_obj.pose.bones.get(pb_name)
                    if pb:
                        c = pb.constraints.get(c_name)
                        if c:
                            c.enabled = enabled
                            
        # Ensure Armature modifier is at the top of the modifier stack (before Subdivision Surface)
        # and enable Preserve Volume (Dual Quaternion Skinning) to prevent volume loss during leg/arm stretching
        for m_obj in selected_meshes:
            # Reorder Armature before Subsurf
            for idx, mod in enumerate(m_obj.modifiers):
                if mod.type == 'ARMATURE':
                    mod.use_deform_preserve_volume = True
                    if idx > 0:
                        # Check if preceding modifiers are Subsurf
                        if any(m.type == 'SUBSURF' for m in m_obj.modifiers[:idx]):
                            try:
                                m_obj.modifiers.move(idx, 0)
                            except Exception:
                                pass
                            
        self.report({'INFO'}, f"Successfully auto-skinned {len(selected_meshes)} meshes to rig '{rig_obj.name}' with Preserve Volume enabled!")
        
        # Write diagnostic log for the active mesh
        diag_path = "f:\\blenderaddon\\HumanRigGenerator\\auto_skin_diagnostic.log"
        with open(diag_path, "w") as diag_file:
            diag_file.write("--- MESH DIAGNOSTIC LOG ---\n")
            if selected_meshes:
                active_mesh = selected_meshes[0]
                diag_file.write(f"Mesh Object Name: {active_mesh.name}\n")
                diag_file.write(f"Parent Object: {active_mesh.parent.name if active_mesh.parent else 'None'}\n")
                diag_file.write(f"Parent Type: {active_mesh.parent_type}\n\n")
                
                diag_file.write("--- MODIFIERS ---\n")
                for mod in active_mesh.modifiers:
                    diag_file.write(f"Name: {mod.name}, Type: {mod.type}, Viewport Visible: {mod.show_viewport}\n")
                    if mod.type == 'ARMATURE':
                        diag_file.write(f"  Target Object: {mod.object.name if mod.object else 'None'}\n")
                        diag_file.write(f"  Use Vertex Groups: {mod.use_vertex_groups}\n")
                        diag_file.write(f"  Use Bone Envelopes: {mod.use_bone_envelopes}\n")
                diag_file.write("\n")
                
                diag_file.write("--- VERTEX GROUPS (Non-Zero Weight Count) ---\n")
                vg_weights = {vg.index: 0 for vg in active_mesh.vertex_groups}
                for v in active_mesh.data.vertices:
                    for g in v.groups:
                        if g.group in vg_weights and g.weight > 0.0:
                            vg_weights[g.group] += 1
                            
                for vg in active_mesh.vertex_groups:
                    count = vg_weights.get(vg.index, 0)
                    diag_file.write(f"Group: {vg.name}, Index: {vg.index}, Vertices with weight: {count}\n")
            else:
                diag_file.write("No mesh object selected/found.\n")
                
        return {'FINISHED'}

def assign_unweighted_vertices(mesh_obj, rig_obj, log_file):
    """Finds all vertices with zero weights and assigns them 100% to the nearest deforming bone segment."""
    import mathutils
    
    # 1. Collect all deforming bones and their world coordinates (head and tail)
    deform_bones = []
    mw_rig = rig_obj.matrix_world
    
    is_hair = "hair" in mesh_obj.name.lower()
    
    for bone in rig_obj.data.bones:
        if bone.use_deform and bone.name.startswith("DEF-"):
            if is_hair:
                # Restrict hair to head, neck, upper spine, shoulders, and face bones
                allowed_prefixes = ["DEF-head", "DEF-neck", "DEF-spine.003", "DEF-shoulder", "DEF-clavicle"]
                allowed_face = ["DEF-ear", "DEF-eyebrow", "DEF-cheek", "DEF-nose", "DEF-jaw", "DEF-chin", "DEF-eyelid"]
                
                is_allowed = False
                for p in allowed_prefixes:
                    if bone.name.startswith(p):
                        is_allowed = True
                        break
                if not is_allowed:
                    for p in allowed_face:
                        if bone.name.startswith(p):
                            is_allowed = True
                            break
                            
                if not is_allowed:
                    continue
                    
            # Get bone head and tail in world space
            head_w = mw_rig @ bone.head
            tail_w = mw_rig @ bone.tail
            deform_bones.append((bone.name, head_w, tail_w))
            
    if not deform_bones:
        return
        
    # 2. Find vertices with zero weights
    unweighted_indices = []
    for v in mesh_obj.data.vertices:
        has_weight = False
        for g in v.groups:
            if g.weight > 0.001:
                has_weight = True
                break
        if not has_weight:
            unweighted_indices.append(v.index)
            
    if not unweighted_indices:
        log_file.write(f"No unweighted vertices found in '{mesh_obj.name}'.\n")
        return
        
    log_file.write(f"Found {len(unweighted_indices)} unweighted vertices in '{mesh_obj.name}'. Assigning to nearest bone...\n")
    
    # 3. Group vertices by target bone
    bone_assignments = {b[0]: [] for b in deform_bones}
    assigned_count = {}
    mw_mesh = mesh_obj.matrix_world
    
    for v_idx in unweighted_indices:
        v = mesh_obj.data.vertices[v_idx]
        v_world = mw_mesh @ v.co
        
        min_dist = float('inf')
        nearest_bone_name = None
        
        for name, head_w, tail_w in deform_bones:
            # Calculate distance from point to line segment
            _, t = mathutils.geometry.intersect_point_line(v_world, head_w, tail_w)
            t = max(0.0, min(1.0, t))
            closest_point = head_w + t * (tail_w - head_w)
            dist = (v_world - closest_point).length
            
            if dist < min_dist:
                min_dist = dist
                nearest_bone_name = name
                
        if nearest_bone_name:
            bone_assignments[nearest_bone_name].append(v_idx)
            assigned_count[nearest_bone_name] = assigned_count.get(nearest_bone_name, 0) + 1
            
    # Apply assignments in batch
    for bone_name, indices in bone_assignments.items():
        if indices:
            vg = mesh_obj.vertex_groups.get(bone_name)
            if not vg:
                vg = mesh_obj.vertex_groups.new(name=bone_name)
            vg.add(indices, 1.0, 'ADD')
            
    # Log assignments
    for name, count in sorted(assigned_count.items(), key=lambda x: x[1], reverse=True):
        log_file.write(f"  Assigned {count} vertices to {name}\n")


class OBJECT_OT_fix_clothing_clipping(bpy.types.Operator):
    """Transfers exact weights from the body mesh to clothes (shirts, pants) and adds a non-penetration safety offset."""
    bl_idname = "object.fix_clothing_clipping"
    bl_label = "Fix Clothing / Mesh Clipping"
    bl_options = {'REGISTER', 'UNDO'}
    
    offset_distance: bpy.props.FloatProperty( # type: ignore
        name="Safety Offset (m)",
        description="Minimum distance between clothing and body skin to prevent poke-through",
        default=0.002,
        min=0.0,
        max=0.05,
        step=0.1,
        precision=4
    )
    
    def execute(self, context):
        selected_objs = [o for o in context.selected_objects if o.type == 'MESH']
        
        if len(selected_objs) == 0:
            self.report({'WARNING'}, "Please select the clothing mesh (Shirt / Pants / Jacket)!")
            return {'CANCELLED'}
            
        body_obj = None
        clothing_objs = []
        
        if len(selected_objs) >= 2:
            for o in selected_objs:
                name_lower = o.name.lower()
                if any(k in name_lower for k in ["body", "skin", "base", "human", "character", "mesh"]):
                    body_obj = o
                    break
            if not body_obj:
                body_obj = selected_objs[-1]
            clothing_objs = [o for o in selected_objs if o != body_obj]
        else:
            clothing_objs = selected_objs
            for o in context.scene.objects:
                if o.type == 'MESH' and o not in clothing_objs:
                    name_lower = o.name.lower()
                    if any(k in name_lower for k in ["body", "skin", "base", "human"]):
                        body_obj = o
                        break
            if not body_obj:
                meshes = [o for o in context.scene.objects if o.type == 'MESH' and o not in clothing_objs]
                if meshes:
                    body_obj = max(meshes, key=lambda m: len(m.data.vertices))
                    
        if not body_obj:
            self.report({'WARNING'}, "Could not detect body mesh! Please select both Clothing and Body mesh together.")
            return {'CANCELLED'}
            
        # 1. Reset any active Armature rig to Rest Pose temporarily for clean weight baking
        active_arm = None
        for mod in body_obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                active_arm = mod.object
                break
                
        if not active_arm:
            for o in context.scene.objects:
                if o.type == 'ARMATURE':
                    active_arm = o
                    break
                    
        current_mode = context.mode
        if active_arm and context.view_layer.objects.get(active_arm.name):
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            active_arm.select_set(True)
            context.view_layer.objects.active = active_arm
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.transforms_clear()
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Clean any bad modifiers from body mesh
        for mod in list(body_obj.modifiers):
            if mod.type in ['DATA_TRANSFER', 'SHRINKWRAP']:
                body_obj.modifiers.remove(mod)
            elif mod.type == 'ARMATURE':
                mod.use_deform_preserve_volume = True
                
        fixed_count = 0
        for cloth in clothing_objs:
            if cloth == body_obj:
                continue
                
            # Clean old modifier artifacts
            for m in list(cloth.modifiers):
                if m.type in ['SHRINKWRAP', 'DATA_TRANSFER', 'MASK'] or "Cloth_No_Clip" in m.name or "HRG_" in m.name:
                    cloth.modifiers.remove(m)
                    
            # 2. Add Data Transfer Modifier and bake in Rest Pose
            dt_mod = cloth.modifiers.new(name="HRG_Weight_Bake", type='DATA_TRANSFER')
            dt_mod.object = body_obj
            dt_mod.use_vert_data = True
            dt_mod.data_types_verts = {'VGROUP_WEIGHTS'}
            dt_mod.vert_mapping = 'POLYINTERP_NEAREST'
            
            bpy.ops.object.select_all(action='DESELECT')
            cloth.select_set(True)
            context.view_layer.objects.active = cloth
            
            try:
                bpy.ops.object.datalayout_transfer(modifier=dt_mod.name)
            except Exception:
                pass
                
            try:
                bpy.ops.object.modifier_apply(modifier=dt_mod.name)
            except Exception:
                pass
                
            # 3. Ensure clean Armature modifier with Preserve Volume
            arm_mod = None
            for m in cloth.modifiers:
                if m.type == 'ARMATURE':
                    arm_mod = m
                    break
            if not arm_mod and active_arm:
                arm_mod = cloth.modifiers.new(name="Armature", type='ARMATURE')
                arm_mod.object = active_arm
                
            if arm_mod:
                arm_mod.use_deform_preserve_volume = True
                # Move Armature to top of stack
                cloth_arm_idx = cloth.modifiers.find(arm_mod.name)
                if cloth_arm_idx > 0:
                    try:
                        cloth.modifiers.move(cloth_arm_idx, 0)
                    except Exception:
                        pass
                    
            fixed_count += 1
            
        # Put back in Pose mode if rig exists
        if active_arm and context.view_layer.objects.get(active_arm.name):
            bpy.ops.object.select_all(action='DESELECT')
            active_arm.select_set(True)
            context.view_layer.objects.active = active_arm
            bpy.ops.object.mode_set(mode='POSE')
            
        context.view_layer.update()
        self.report({'INFO'}, f"Cleanly baked & synchronized weights for {fixed_count} clothing mesh(es) to '{body_obj.name}'!")
        return {'FINISHED'}

class OBJECT_OT_mask_body_under_clothes(bpy.types.Operator):
    """Hides the body mesh geometry under clothing using a Mask modifier so skin can never poke through."""
    bl_idname = "object.mask_body_under_clothes"
    bl_label = "Auto-Mask Body Under Clothes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        cloth_keywords = ["shirt", "pant", "paint", "short", "jean", "boxer", "trouser", "cloth", "jacket", "coat", "dress", "suit", "bottom", "top", "vest", "underwear", "garment"]
        selected_objs = [o for o in context.selected_objects if o.type == 'MESH']
        
        # 1. Identify Body Object
        body_obj = None
        if selected_objs:
            for o in selected_objs:
                name_lower = o.name.lower()
                if any(k in name_lower for k in ["body", "skin", "base", "human"]):
                    body_obj = o
                    break
            if not body_obj:
                body_obj = selected_objs[0]
        else:
            active = context.active_object
            if active and active.type == 'MESH':
                body_obj = active
            else:
                for o in context.scene.objects:
                    if o.type == 'MESH' and any(k in o.name.lower() for k in ["body", "skin", "human", "character"]):
                        body_obj = o
                        break
                        
        if not body_obj:
            self.report({'WARNING'}, "Please select your Character Body Mesh!")
            return {'CANCELLED'}
            
        # 2. Collect ALL clothing objects in the scene (both selected and unselected)
        clothing_objs = []
        for o in context.scene.objects:
            if o.type == 'MESH' and o != body_obj and not o.name.startswith("Wgt_"):
                if any(k in o.name.lower() for k in cloth_keywords):
                    clothing_objs.append(o)
                    
        if not clothing_objs:
            self.report({'WARNING'}, "No clothing meshes (shirt, pants, etc.) found to calculate body mask!")
            return {'CANCELLED'}
            
        vg_name = "HRG_Mask_Visible_Body"
        vg = body_obj.vertex_groups.get(vg_name)
        if not vg:
            vg = body_obj.vertex_groups.new(name=vg_name)
            
        body_mesh = body_obj.data
        import mathutils
        import bmesh
        
        cloth_data = []
        for cloth in clothing_objs:
            bm = bmesh.new()
            bm.from_mesh(cloth.data)
            bm.transform(cloth.matrix_world)
            tree = mathutils.bvhtree.BVHTree.FromBMesh(bm)
            
            bbox_world = [(cloth.matrix_world @ mathutils.Vector(b)) for b in cloth.bound_box]
            z_min = min(b.z for b in bbox_world)
            z_max = max(b.z for b in bbox_world)
            x_min = min(b.x for b in bbox_world)
            x_max = max(b.x for b in bbox_world)
            
            cloth_data.append({
                'obj': cloth,
                'tree': tree,
                'bm': bm,
                'z_min': z_min,
                'z_max': z_max,
                'x_min': x_min,
                'x_max': x_max,
                'is_pants': any(k in cloth.name.lower() for k in ["pant", "paint", "short", "trouser", "jean", "boxer", "underwear"]),
                'is_shirt': any(k in cloth.name.lower() for k in ["shirt", "top", "jacket", "coat", "vest", "tshirt"])
            })
            
        mw_body = body_obj.matrix_world
        hidden_indices = []
        visible_indices = []
        
        for v in body_mesh.vertices:
            v_world = mw_body @ v.co
            is_under_cloth = False
            
            for c in cloth_data:
                if c['is_pants']:
                    # Pants / Shorts interior: Keep hem (knees) and waist intact
                    if (c['z_min'] + 0.045) <= v_world.z <= (c['z_max'] - 0.02):
                        loc, n, idx, dist = c['tree'].find_nearest(v_world)
                        if dist is not None and dist < 0.055:
                            is_under_cloth = True
                            break
                        # Groin center fold
                        if abs(v_world.x) < 0.09 and (c['z_min'] + 0.055) <= v_world.z <= (c['z_max'] - 0.03):
                            is_under_cloth = True
                            break
                            
                elif c['is_shirt']:
                    # Shirt interior:
                    # 1. Protect Hands/Forearms: If |X| is beyond sleeve opening, NEVER mask!
                    max_sleeve_x = max(abs(c['x_min']), abs(c['x_max']))
                    if abs(v_world.x) >= max_sleeve_x - 0.03:
                        continue # Outside sleeve opening (arms/hands protected)
                        
                    # 2. Protect Neck/Head: If Z is near or above collar, NEVER mask!
                    if v_world.z >= c['z_max'] - 0.04 and abs(v_world.x) < 0.12:
                        continue # Neck / chin protected
                        
                    # 3. Protect Waist bottom: If Z is below waist opening, NEVER mask!
                    if v_world.z <= c['z_min'] + 0.03:
                        continue # Waist bottom protected
                        
                    loc, n, idx, dist = c['tree'].find_nearest(v_world)
                    if dist is not None and dist < 0.045:
                        is_under_cloth = True
                        break
                        
            if is_under_cloth:
                hidden_indices.append(v.index)
            else:
                visible_indices.append(v.index)
                
        # Free bmeshes
        for c in cloth_data:
            c['bm'].free()
                
        if visible_indices:
            vg.add(visible_indices, 1.0, 'REPLACE')
        if hidden_indices:
            vg.remove(hidden_indices)
            
        mask_mod_name = "HRG_Body_Cloth_Mask"
        mask_mod = body_obj.modifiers.get(mask_mod_name)
        if not mask_mod:
            mask_mod = body_obj.modifiers.new(name=mask_mod_name, type='MASK')
            
        mask_mod.vertex_group = vg_name
        mask_mod.invert_vertex_group = False
        
        # Position Mask modifier right after Armature and before Subdivision
        arm_idx = -1
        for idx, m in enumerate(body_obj.modifiers):
            if m.type == 'ARMATURE':
                arm_idx = idx
                break
        if arm_idx != -1:
            try:
                body_obj.modifiers.move(body_obj.modifiers.find(mask_mod.name), arm_idx + 1)
            except Exception:
                pass
        
        context.view_layer.update()
        self.report({'INFO'}, f"Auto-masked {len(hidden_indices)} body vertices under all {len(clothing_objs)} clothing items! Hands & Knees 100% protected.")
        return {'FINISHED'}

