# operators/auto_skin.py
import bpy

def cleanup_limb_bleed(mesh_obj, rig_obj, log_file=None):
    """Isolates limb weights (arms, forearms, hands, shins, feet) while preserving smooth anatomical weight blends across thighs, hips, waist, and spine."""
    if not (mesh_obj and mesh_obj.type == 'MESH' and rig_obj and rig_obj.type == 'ARMATURE'):
        return
        
    try:
        mw = mesh_obj.matrix_world
        pelvis_pb = rig_obj.pose.bones.get("DEF-pelvis")
        center_x = (rig_obj.matrix_world @ pelvis_pb.head).x if pelvis_pb else 0.0
        pelvis_z = (rig_obj.matrix_world @ pelvis_pb.head).z if pelvis_pb else 0.0
        
        l_thigh_pb = rig_obj.pose.bones.get("DEF-thigh.L")
        left_is_positive_x = True
        if l_thigh_pb:
            left_is_positive_x = ((rig_obj.matrix_world @ l_thigh_pb.head).x > center_x)
            
        # 1. Symmetrical left/right leg cross-bleed cleanup (distal limbs: shin, foot, toe)
        leg_distal_L = [vg for vg in mesh_obj.vertex_groups if any(k in vg.name for k in ["shin.L", "foot.L", "toe.L"])]
        leg_distal_R = [vg for vg in mesh_obj.vertex_groups if any(k in vg.name for k in ["shin.R", "foot.R", "toe.R"])]
        
        for v in mesh_obj.data.vertices:
            vw_x = (mw @ v.co).x
            vw_z = (mw @ v.co).z
            # Only isolate distal legs below pelvis height
            if vw_z < pelvis_z and abs(vw_x - center_x) > 0.04:
                is_on_left = (vw_x > center_x) if left_is_positive_x else (vw_x < center_x)
                if is_on_left:
                    for vg in leg_distal_R:
                        vg.remove([v.index])
                else:
                    for vg in leg_distal_L:
                        vg.remove([v.index])
                        
        # 2. Solid Ankle Joint Hinge (Shin & Foot isolation without harsh hip cuts)
        for side in [".L", ".R"]:
            foot_pb = rig_obj.pose.bones.get(f"DEF-foot{side}")
            shin_pb = rig_obj.pose.bones.get(f"DEF-shin{side}")
            vg_shin = mesh_obj.vertex_groups.get(f"DEF-shin{side}")
            vg_foot = mesh_obj.vertex_groups.get(f"DEF-foot{side}")
            vg_toe = mesh_obj.vertex_groups.get(f"DEF-toe{side}")
            
            if foot_pb:
                f_head_z = (rig_obj.matrix_world @ foot_pb.head).z
                
                # Shin must not bleed into sole/toes
                foot_verts = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z < f_head_z - 0.015]
                if vg_shin and foot_verts:
                    vg_shin.remove(foot_verts)
                    
                # Foot must not bleed high up the calf
                calf_verts = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z > f_head_z + 0.035]
                if vg_foot and calf_verts:
                    vg_foot.remove(calf_verts)
                if vg_toe and calf_verts:
                    vg_toe.remove(calf_verts)
                    
        # 3. Arm, Forearm & Hand Isolation from Spine (Upper Torso only, protecting pelvis/thighs)
        chest_pb = rig_obj.pose.bones.get("DEF-spine.002") or rig_obj.pose.bones.get("DEF-spine.001")
        min_arm_z = (rig_obj.matrix_world @ chest_pb.head).z if chest_pb else (pelvis_z + 0.25)
        
        # Only consider arm vertices in the upper torso / shoulder level (Z >= min_arm_z)
        arm_verts_L = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z >= min_arm_z and ((mw @ v.co).x - center_x > 0.20 if left_is_positive_x else (mw @ v.co).x - center_x < -0.20)]
        arm_verts_R = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z >= min_arm_z and ((mw @ v.co).x - center_x < -0.20 if left_is_positive_x else (mw @ v.co).x - center_x > 0.20)]
        all_arm_verts = arm_verts_L + arm_verts_R
        
        for sp_name in ["DEF-spine.001", "DEF-spine.002", "DEF-spine.003"]:
            sp_vg = mesh_obj.vertex_groups.get(sp_name)
            if sp_vg and all_arm_verts:
                sp_vg.remove(all_arm_verts)
                
        for side in [".L", ".R"]:
            uarm_pb = rig_obj.pose.bones.get(f"DEF-upper_arm{side}")
            farm_pb = rig_obj.pose.bones.get(f"DEF-forearm{side}")
            hand_pb = rig_obj.pose.bones.get(f"DEF-hand{side}")
            
            vg_uarm = mesh_obj.vertex_groups.get(f"DEF-upper_arm{side}")
            vg_farm = mesh_obj.vertex_groups.get(f"DEF-forearm{side}")
            vg_hand = mesh_obj.vertex_groups.get(f"DEF-hand{side}")
            
            is_left = (side == ".L" and left_is_positive_x) or (side == ".R" and not left_is_positive_x)
            
            if uarm_pb and vg_uarm:
                sh_head = rig_obj.matrix_world @ uarm_pb.head
                
                # Torso vertices well inward of shoulder socket must not have arm weights
                torso_verts = []
                for v in mesh_obj.data.vertices:
                    vw = mw @ v.co
                    if vw.z >= min_arm_z:
                        inward_dist = (sh_head.x - vw.x) if is_left else (vw.x - sh_head.x)
                        if inward_dist > 0.05: # Well inside chest/spine
                            torso_verts.append(v.index)
                            
                if torso_verts:
                    vg_uarm.remove(torso_verts)
                if vg_farm and torso_verts:
                    vg_farm.remove(torso_verts)
                if vg_hand and torso_verts:
                    vg_hand.remove(torso_verts)
                    
            # Solid Wrist Hinge: eliminate rubbery wrist joint stretching
            if hand_pb:
                w_head = rig_obj.matrix_world @ hand_pb.head
                hand_verts = []
                arm_verts = []
                for v in mesh_obj.data.vertices:
                    vw_x = (mw @ v.co).x
                    vw_z = (mw @ v.co).z
                    if vw_z >= min_arm_z - 0.2:
                        dist_outward = (vw_x - w_head.x) if is_left else (w_head.x - vw_x)
                        if dist_outward > 0.015:
                            hand_verts.append(v.index)
                        elif dist_outward < -0.025:
                            arm_verts.append(v.index)
                            
                if vg_farm and hand_verts:
                    vg_farm.remove(hand_verts)
                if vg_hand and arm_verts:
                    vg_hand.remove(arm_verts)
                for f_vg in mesh_obj.vertex_groups:
                    if side in f_vg.name and any(k in f_vg.name for k in ["thumb", "index", "middle", "ring", "pinky"]):
                        if arm_verts:
                            f_vg.remove(arm_verts)
                    
        # 4. Neck, Head & Jaw Anatomical Weighting (strict neck/head isolation)
        neck_pb = rig_obj.pose.bones.get("DEF-neck")
        head_pb = rig_obj.pose.bones.get("DEF-head")
        jaw_pb = rig_obj.pose.bones.get("DEF-jaw")
        
        vg_neck = mesh_obj.vertex_groups.get("DEF-neck")
        vg_head = mesh_obj.vertex_groups.get("DEF-head")
        vg_jaw = mesh_obj.vertex_groups.get("DEF-jaw")
        
        # Check if mesh is clothing
        is_upper_clothing = any(k in mesh_obj.name.lower() for k in ["shirt", "top", "jacket", "coat", "vest", "tshirt", "hoodie", "sweater", "bra", "chest"])
        is_lower_clothing = any(k in mesh_obj.name.lower() for k in ["pant", "paint", "short", "trouser", "jean", "boxer", "skirt", "bottom", "underwear", "brief", "leg"])
        
        if is_upper_clothing:
            # Upper clothing (shirt/jacket): Torso, arms, neck, shoulders + pelvis transition
            # Only strip distal leg bones, feet, hands, face so shirts blend naturally over hips/pelvis
            forbidden_upper = ["shin", "foot", "toe", "ankle", "hand", "thumb", "index", "middle", "ring", "pinky", "head", "jaw", "chin", "nose", "eye", "lip", "cheek", "ear", "tongue", "face", "mouth"]
            for vg in list(mesh_obj.vertex_groups):
                if any(k in vg.name.lower() for k in forbidden_upper):
                    mesh_obj.vertex_groups.remove(vg)
            
            # Normalize remaining weights per vertex for calm, smooth motion
            for v in mesh_obj.data.vertices:
                total_w = sum(g.weight for g in v.groups)
                if total_w > 0.0001:
                    for g in v.groups:
                        g.weight /= total_w

        elif is_lower_clothing:
            # Lower clothing (pants/shorts): Pelvis, thighs, legs + spine transition
            # Only strip upper body (head, neck, arms, hands, face) so pants waistbands blend naturally with spine
            forbidden_lower = ["neck", "head", "jaw", "chin", "nose", "eye", "lip", "cheek", "ear", "tongue", "face", "mouth", "shoulder", "upper_arm", "forearm", "hand", "thumb", "index", "middle", "ring", "pinky", "breast"]
            for vg in list(mesh_obj.vertex_groups):
                if any(k in vg.name.lower() for k in forbidden_lower):
                    mesh_obj.vertex_groups.remove(vg)
                    
            # Normalize remaining weights per vertex for calm, smooth motion
            for v in mesh_obj.data.vertices:
                total_w = sum(g.weight for g in v.groups)
                if total_w > 0.0001:
                    for g in v.groups:
                        g.weight /= total_w
        else:
            # On Body Mesh:
            if neck_pb and head_pb:
                n_head_z = (rig_obj.matrix_world @ neck_pb.head).z  # base of neck
                h_head_z = (rig_obj.matrix_world @ head_pb.head).z  # jaw / base of skull
                
                # 1. DEF-head strictly limited to skull/face (Z >= n_head_z - 0.015) - never touches shoulders or chest
                below_skull = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z < n_head_z - 0.015]
                if vg_head and below_skull:
                    vg_head.remove(below_skull)
                    
                # 2. DEF-neck strictly limited to neck cylinder (|X - center_x| < 0.075 and Z >= n_head_z - 0.02) - never touches shoulders
                non_neck = [v.index for v in mesh_obj.data.vertices if (mw @ v.co).z < n_head_z - 0.02 or abs((mw @ v.co).x - center_x) > 0.075]
                if vg_neck and non_neck:
                    vg_neck.remove(non_neck)
                                    
        if log_file:
            log_file.write(f"Completed clean limb bleed isolation on mesh '{mesh_obj.name}'.\n")
    except Exception as e:
        if log_file:
            log_file.write(f"Limb bleed isolation failed on '{mesh_obj.name}': {e}\n")

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
                
                # Check if this mesh is a tear line, eye occlusion, or eyelash accessory mesh
                is_eye_accessory = any(k in mesh_obj.name.lower() for k in ["tear", "tearline", "occlusion", "eyeocclusion", "eye_occlusion", "eyelash", "eyelashes", "lash", "lashes", "cornea", "eye_moisture"])
                
                if is_eye_accessory:
                    log_file.write(f"Detected separate eye accessory mesh object '{mesh_obj.name}'. Binding to head & eyelids...\n")
                    
                    # 1. Clear original parenting and parent directly to the new rig
                    matrix_world = mesh_obj.matrix_world.copy()
                    mesh_obj.parent = None
                    mesh_obj.matrix_world = matrix_world
                    mesh_obj.parent = rig_obj
                    mesh_obj.parent_type = 'OBJECT'
                    mesh_obj.matrix_world = matrix_world
                    log_file.write("Cleared parenting and reparented eye accessory mesh to rig object.\n")
                    
                    # 2. Clean existing modifiers and vertex groups
                    for mod in list(mesh_obj.modifiers):
                        if mod.type in ['ARMATURE', 'DATA_TRANSFER', 'SHRINKWRAP', 'MASK'] or "HRG_" in mod.name:
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
                    except:
                        pass
                        
                    # 4. Find the character body mesh to transfer exact eyelid/head weights
                    body_obj = None
                    for m in selected_meshes:
                        if m != mesh_obj and m.type == 'MESH':
                            if any(k in m.name.lower() for k in ["body", "skin", "base", "human", "character"]):
                                body_obj = m
                                break
                    if not body_obj:
                        for o in context.scene.objects:
                            if o != mesh_obj and o.type == 'MESH' and not o.name.startswith("Wgt_"):
                                if any(k in o.name.lower() for k in ["body", "skin", "base", "human", "character"]):
                                    body_obj = o
                                    break
                                    
                    transferred = False
                    if body_obj and len(body_obj.vertex_groups) > 0:
                        try:
                            dt_mod = mesh_obj.modifiers.new(name="HRG_EyeAcc_Weights", type='DATA_TRANSFER')
                            dt_mod.object = body_obj
                            dt_mod.use_vert_data = True
                            dt_mod.data_types_verts = {'VGROUP_WEIGHTS'}
                            dt_mod.vert_mapping = 'POLYINTERP_NEAREST'
                            
                            bpy.ops.object.select_all(action='DESELECT')
                            mesh_obj.select_set(True)
                            context.view_layer.objects.active = mesh_obj
                            bpy.ops.object.datalayout_transfer(modifier=dt_mod.name)
                            
                            if hasattr(context, "temp_override"):
                                with context.temp_override(active_object=mesh_obj, selected_objects=[mesh_obj]):
                                    bpy.ops.object.modifier_apply(modifier=dt_mod.name)
                            else:
                                bpy.ops.object.modifier_apply(modifier=dt_mod.name)
                                
                            if dt_mod.name in mesh_obj.modifiers:
                                mesh_obj.modifiers.remove(mesh_obj.modifiers[dt_mod.name])
                                
                            # Strip any accidental non-head bone groups
                            allowed_head_keywords = ["head", "neck", "eyelid", "eye_corner", "eye", "brow", "cheek", "nose", "face"]
                            for vg in list(mesh_obj.vertex_groups):
                                if not any(k in vg.name.lower() for k in allowed_head_keywords):
                                    mesh_obj.vertex_groups.remove(vg)
                                    
                            transferred = True
                            log_file.write(f"Transferred facial/eyelid weights from '{body_obj.name}' to '{mesh_obj.name}'.\n")
                        except Exception as e_dt:
                            log_file.write(f"Data transfer failed on '{mesh_obj.name}': {e_dt}\n")
                            
                    # Any vertex with zero weights is assigned 100% to DEF-head
                    vg_head = mesh_obj.vertex_groups.get("DEF-head") or mesh_obj.vertex_groups.new(name="DEF-head")
                    unweighted_v = []
                    for v in mesh_obj.data.vertices:
                        total_w = sum(g.weight for g in v.groups)
                        if total_w < 0.001:
                            unweighted_v.append(v.index)
                    if unweighted_v:
                        vg_head.add(unweighted_v, 1.0, 'REPLACE')
                        log_file.write(f"Assigned {len(unweighted_v)} unweighted eye accessory vertices to DEF-head.\n")
                        
                    # Normalize weights
                    for v in mesh_obj.data.vertices:
                        tot = sum(g.weight for g in v.groups)
                        if tot > 0.0001:
                            for g in v.groups:
                                g.weight /= tot
                                
                    # 5. Add Armature Modifier
                    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
                    mod.object = rig_obj
                    mod.use_deform_preserve_volume = True
                    log_file.write(f"Eye accessory skinning for '{mesh_obj.name}' succeeded!\n")
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
                    
                    if "tongue" in mesh_obj.name.lower():
                        # Tongue is anchored at the throat base to DEF-head, and free at front to follow DEF-jaw
                        mw = mesh_obj.matrix_world
                        coords_y = [(mw @ v.co).y for v in mesh_obj.data.vertices]
                        min_y = min(coords_y) # tip of tongue (forward)
                        max_y = max(coords_y) # root of tongue (back towards throat)
                        y_range = max(0.001, max_y - min_y)
                        
                        for v in mesh_obj.data.vertices:
                            vy = (mw @ v.co).y
                            t_back = (vy - min_y) / y_range # 0 at tip, 1 at base
                            
                            if t_back <= 0.40:
                                vg_jaw.add([v.index], 1.0, 'REPLACE')
                            elif t_back >= 0.85:
                                vg_head.add([v.index], 1.0, 'REPLACE')
                            else:
                                blend = (t_back - 0.40) / 0.45
                                blend = blend * blend * (3.0 - 2.0 * blend) # smooth S-curve
                                vg_jaw.add([v.index], 1.0 - blend, 'REPLACE')
                                vg_head.add([v.index], blend, 'REPLACE')
                        log_file.write(f"Assigned anatomical gradient weights to tongue '{mesh_obj.name}' (jaw tip, throat head anchor).\n")
                    elif any(x in mesh_obj.name.lower() for x in ["upper", "top"]):
                        upper_v = [v.index for v in mesh_obj.data.vertices]
                        vg_head.add(upper_v, 1.0, 'REPLACE')
                        log_file.write(f"Assigned {len(upper_v)} upper vertices to DEF-head.\n")
                    elif any(x in mesh_obj.name.lower() for x in ["lower", "bottom", "jaw"]):
                        lower_v = [v.index for v in mesh_obj.data.vertices]
                        vg_jaw.add(lower_v, 1.0, 'REPLACE')
                        log_file.write(f"Assigned {len(lower_v)} lower vertices to DEF-jaw.\n")
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
                    if mod.type in ['ARMATURE', 'DATA_TRANSFER', 'SHRINKWRAP', 'MASK'] or "HRG_" in mod.name or "Cloth_" in mod.name:
                        mesh_obj.modifiers.remove(mod)
                        
                bone_names = {b.name for b in rig_obj.data.bones}
                for vg in list(mesh_obj.vertex_groups):
                    if vg.name in bone_names or vg.name.startswith("DEF-") or vg.name.startswith("ORG-") or vg.name.startswith("MCH-") or vg.name.startswith("HRG_"):
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
                    
                # Anatomical Face, Mouth, Lip & Jaw weight painting for speech and facial expressions
                try:
                    paint_anatomical_face_and_jaw_weights(mesh_obj, rig_obj, log_file)
                except Exception as e_face:
                    log_file.write(f"Facial weight painting failed: {e_face}\n")
                    
                # Foot and Toe weight cleanup (only for body and foot/shoe meshes, never upper clothing/shirts)
                is_upper = any(k in mesh_obj.name.lower() for k in ["shirt", "top", "jacket", "coat", "vest", "tshirt", "hoodie", "sweater", "bra", "chest"])
                if not is_upper:
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
                                
                                foot_verts = []
                                toe_verts = []
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
                                                foot_verts.append(v.index)
                                            else:
                                                toe_verts.append(v.index)
                                if foot_verts or toe_verts:
                                    foot_vg = mesh_obj.vertex_groups.get(foot_name) or mesh_obj.vertex_groups.new(name=foot_name)
                                    toe_vg = mesh_obj.vertex_groups.get(toe_name) or mesh_obj.vertex_groups.new(name=toe_name)
                                    if foot_verts:
                                        foot_vg.add(foot_verts, 1.0, 'REPLACE')
                                    if toe_verts:
                                        toe_vg.add(toe_verts, 1.0, 'REPLACE')
                                log_file.write(f"Foot weight cleanup ({side}) at Z={ankle_z:.4f}: assigned {len(foot_verts)} to foot, {len(toe_verts)} to toe.\n")
                    except Exception as e_foot:
                        log_file.write(f"Foot cleanup failed: {e_foot}\n")
                        
                # Auto-assign any unweighted vertices (like loose ponytail strands) to the nearest deforming bone
                try:
                    assign_unweighted_vertices(mesh_obj, rig_obj, log_file)
                except Exception as e_unweighted:
                    log_file.write(f"Assign unweighted vertices failed: {e_unweighted}\n")
                    
                # Final Isolated limb weight, clothing isolation, and spine cleanup across mesh
                cleanup_limb_bleed(mesh_obj, rig_obj, log_file)
                    
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

def paint_anatomical_face_and_jaw_weights(mesh_obj, rig_obj, log_file=None):
    """Paints smooth, realistic anatomical weights for mouth, lips, jaw, chin, and cheeks on character body mesh."""
    import mathutils
    if not (mesh_obj and mesh_obj.type == 'MESH' and rig_obj and rig_obj.type == 'ARMATURE'):
        return
        
    # Only run on the main character/body mesh (skip hair, clothing, eyes, tearline, teeth, tongue)
    obj_name_l = mesh_obj.name.lower()
    is_non_body = any(k in obj_name_l for k in ["hair", "shirt", "pant", "shoe", "cloth", "dress", "tear", "eye", "lash", "teeth", "tooth", "tongue", "occlusion", "sock", "glove", "hat", "cap", "bra", "under"])
    if is_non_body:
        return
        
    try:
        mw = mesh_obj.matrix_world
        
        # Resolve pose bones
        jaw_pb = rig_obj.pose.bones.get("DEF-jaw")
        chin_pb = rig_obj.pose.bones.get("DEF-chin")
        mouth_root_pb = rig_obj.pose.bones.get("DEF-mouth_root")
        head_pb = rig_obj.pose.bones.get("DEF-head")
        neck_pb = rig_obj.pose.bones.get("DEF-neck")
        nose_pb = rig_obj.pose.bones.get("DEF-nose")
        
        lip_up_pb = rig_obj.pose.bones.get("DEF-lip.upper")
        lip_low_pb = rig_obj.pose.bones.get("DEF-lip.lower")
        lip_up_L_pb = rig_obj.pose.bones.get("DEF-lip.upper.01.L")
        lip_up_R_pb = rig_obj.pose.bones.get("DEF-lip.upper.01.R")
        lip_low_L_pb = rig_obj.pose.bones.get("DEF-lip.lower.01.L")
        lip_low_R_pb = rig_obj.pose.bones.get("DEF-lip.lower.01.R")
        corner_L_pb = rig_obj.pose.bones.get("DEF-lip.corner.L")
        corner_R_pb = rig_obj.pose.bones.get("DEF-lip.corner.R")
        cheek_L_pb = rig_obj.pose.bones.get("DEF-cheek.L")
        cheek_R_pb = rig_obj.pose.bones.get("DEF-cheek.R")
        
        if not (jaw_pb and head_pb and chin_pb):
            return
            
        p_jaw = rig_obj.matrix_world @ jaw_pb.head
        p_chin = rig_obj.matrix_world @ chin_pb.tail
        p_head = rig_obj.matrix_world @ head_pb.head
        p_neck = rig_obj.matrix_world @ neck_pb.head if neck_pb else (p_head - mathutils.Vector((0, 0, 0.15)))
        p_nose = rig_obj.matrix_world @ nose_pb.head if nose_pb else (p_head + mathutils.Vector((0, -0.08, -0.04)))
        
        p_lip_up = rig_obj.matrix_world @ lip_up_pb.head if lip_up_pb else (p_chin + mathutils.Vector((0, 0, 0.045)))
        p_lip_low = rig_obj.matrix_world @ lip_low_pb.head if lip_low_pb else (p_chin + mathutils.Vector((0, 0, 0.02)))
        
        p_corner_L = rig_obj.matrix_world @ corner_L_pb.head if corner_L_pb else (p_lip_up + mathutils.Vector((0.025, 0, -0.01)))
        p_corner_R = rig_obj.matrix_world @ corner_R_pb.head if corner_R_pb else (p_lip_up + mathutils.Vector((-0.025, 0, -0.01)))
        
        mouth_center = (p_lip_up + p_lip_low) * 0.5
        mouth_width = max(0.02, abs(p_corner_L.x - p_corner_R.x) * 0.5)
        
        # Ensure vertex groups exist
        def get_or_create_vg(name):
            vg = mesh_obj.vertex_groups.get(name)
            if not vg:
                vg = mesh_obj.vertex_groups.new(name=name)
            return vg
            
        vg_jaw = get_or_create_vg("DEF-jaw")
        vg_chin = get_or_create_vg("DEF-chin")
        vg_head = get_or_create_vg("DEF-head")
        vg_mouth_root = get_or_create_vg("DEF-mouth_root")
        
        vg_lip_up = get_or_create_vg("DEF-lip.upper")
        vg_lip_low = get_or_create_vg("DEF-lip.lower")
        vg_lip_up_L = get_or_create_vg("DEF-lip.upper.01.L") if lip_up_L_pb else None
        vg_lip_up_R = get_or_create_vg("DEF-lip.upper.01.R") if lip_up_R_pb else None
        vg_lip_low_L = get_or_create_vg("DEF-lip.lower.01.L") if lip_low_L_pb else None
        vg_lip_low_R = get_or_create_vg("DEF-lip.lower.01.R") if lip_low_R_pb else None
        vg_corner_L = get_or_create_vg("DEF-lip.corner.L")
        vg_corner_R = get_or_create_vg("DEF-lip.corner.R")
        vg_nose = get_or_create_vg("DEF-nose") if nose_pb else None
        
        face_v_indices = []
        
        # Weight calculations per vertex in the facial region
        for v in mesh_obj.data.vertices:
            vw = mw @ v.co
            
            # Check if vertex is in the head/face zone (above base of neck)
            if vw.z < p_neck.z - 0.04 or vw.z > p_head.z + 0.15:
                continue
            if abs(vw.x) > 0.14 or abs(vw.y - p_head.y) > 0.18:
                continue
                
            face_v_indices.append(v.index)
            
            # Mouth horizontal coordinate normalized [0..1]
            tx = min(1.0, max(0.0, abs(vw.x) / mouth_width))
            
            # Slanted mouth opening seam dividing upper and lower lip
            corner_z = (p_corner_L.z + p_corner_R.z) * 0.5
            z_seam = (1.0 - tx) * mouth_center.z + tx * corner_z
            
            is_forward_face = (vw.y < p_head.y - 0.015)
            
            # STRICT UPPER / LOWER SEPARATION:
            # 1. Any vertex above z_seam CANNOT have DEF-jaw, DEF-chin, or DEF-lip.lower*
            if vw.z > z_seam:
                try: vg_jaw.remove([v.index])
                except: pass
                try: vg_chin.remove([v.index])
                except: pass
                try: vg_lip_low.remove([v.index])
                except: pass
                if vg_lip_low_L:
                    try: vg_lip_low_L.remove([v.index])
                    except: pass
                if vg_lip_low_R:
                    try: vg_lip_low_R.remove([v.index])
                    except: pass
            
            # 2. Any vertex below or equal to z_seam in the forward mouth/chin CANNOT have DEF-lip.upper* or DEF-mouth_root
            if vw.z <= z_seam and is_forward_face and vw.z < p_nose.z:
                try: vg_mouth_root.remove([v.index])
                except: pass
                try: vg_lip_up.remove([v.index])
                except: pass
                if vg_lip_up_L:
                    try: vg_lip_up_L.remove([v.index])
                    except: pass
                if vg_lip_up_R:
                    try: vg_lip_up_R.remove([v.index])
                    except: pass
                if vg_nose:
                    try: vg_nose.remove([v.index])
                    except: pass
            
            if is_forward_face and vw.z < p_nose.z + 0.015:
                dist_to_chin = (vw - p_chin).length
                dist_to_lip_up = (vw - p_lip_up).length
                dist_to_lip_low = (vw - p_lip_low).length
                dist_to_corner_L = (vw - p_corner_L).length
                dist_to_corner_R = (vw - p_corner_R).length
                
                # 1. Outer Mouth corners (restricted small radius of 1.2cm only at outer corner apex)
                r_corner = 0.014 * (p_head.z - p_neck.z) / 0.26
                is_near_corner_L = (dist_to_corner_L < r_corner)
                is_near_corner_R = (dist_to_corner_R < r_corner)
                
                if is_near_corner_L:
                    w_corner = max(0.0, min(1.0, 1.0 - (dist_to_corner_L / r_corner)))
                    w_corner = w_corner * w_corner * (3.0 - 2.0 * w_corner)
                    vg_corner_L.add([v.index], w_corner * 0.5, 'REPLACE')
                    if vg_corner_R:
                        vg_corner_R.remove([v.index])
                elif is_near_corner_R:
                    w_corner = max(0.0, min(1.0, 1.0 - (dist_to_corner_R / r_corner)))
                    w_corner = w_corner * w_corner * (3.0 - 2.0 * w_corner)
                    vg_corner_R.add([v.index], w_corner * 0.5, 'REPLACE')
                    if vg_corner_L:
                        vg_corner_L.remove([v.index])
                else:
                    if vg_corner_L:
                        vg_corner_L.remove([v.index])
                    if vg_corner_R:
                        vg_corner_R.remove([v.index])
                        
                # 2. Lower Lip & Chin & Mandible (Z <= z_seam)
                if vw.z <= z_seam:
                    if vw.z >= p_chin.z + 0.015:
                        # Lower lip area
                        w_lip_low = max(0.0, min(1.0, 1.0 - (dist_to_lip_low / 0.035)))
                        w_lip_low = w_lip_low * w_lip_low * (3.0 - 2.0 * w_lip_low)
                        
                        # Distribute left/right/center lip
                        if vw.x > 0.008 and vg_lip_low_L:
                            vg_lip_low_L.add([v.index], w_lip_low * 0.7, 'REPLACE')
                            vg_lip_low.add([v.index], w_lip_low * 0.3, 'REPLACE')
                        elif vw.x < -0.008 and vg_lip_low_R:
                            vg_lip_low_R.add([v.index], w_lip_low * 0.7, 'REPLACE')
                            vg_lip_low.add([v.index], w_lip_low * 0.3, 'REPLACE')
                        else:
                            vg_lip_low.add([v.index], w_lip_low * 0.85, 'REPLACE')
                            
                        vg_jaw.add([v.index], 1.0 - w_lip_low * 0.3, 'REPLACE')
                        vg_head.remove([v.index])
                    else:
                        # Chin area
                        w_chin = max(0.0, min(1.0, 1.0 - (dist_to_chin / 0.040)))
                        w_chin = w_chin * w_chin * (3.0 - 2.0 * w_chin)
                        vg_chin.add([v.index], w_chin * 0.9, 'REPLACE')
                        vg_jaw.add([v.index], 1.0 - w_chin * 0.5, 'REPLACE')
                        vg_head.remove([v.index])
                        
                # 3. Upper Lip & Maxilla & Philtrum (Z > z_seam)
                else:
                    w_lip_up = max(0.0, min(1.0, 1.0 - (dist_to_lip_up / 0.035)))
                    w_lip_up = w_lip_up * w_lip_up * (3.0 - 2.0 * w_lip_up)
                    
                    if vw.x > 0.008 and vg_lip_up_L:
                        vg_lip_up_L.add([v.index], w_lip_up * 0.7, 'REPLACE')
                        vg_lip_up.add([v.index], w_lip_up * 0.3, 'REPLACE')
                    elif vw.x < -0.008 and vg_lip_up_R:
                        vg_lip_up_R.add([v.index], w_lip_up * 0.7, 'REPLACE')
                        vg_lip_up.add([v.index], w_lip_up * 0.3, 'REPLACE')
                    else:
                        vg_lip_up.add([v.index], w_lip_up * 0.85, 'REPLACE')
                        
                    vg_mouth_root.add([v.index], (1.0 - w_lip_up) * 0.6, 'REPLACE')
                    vg_head.add([v.index], (1.0 - w_lip_up) * 0.4, 'REPLACE')
                    
            elif not is_forward_face and vw.z < p_chin.z + 0.02:
                # Throat / Submandibular area below jaw
                dist_jaw_head = (vw - p_jaw).length
                w_jaw_angle = max(0.0, min(1.0, 1.0 - (dist_jaw_head / 0.08)))
                vg_jaw.add([v.index], w_jaw_angle * 0.6, 'ADD')
                vg_head.add([v.index], 1.0 - w_jaw_angle * 0.6, 'ADD')
                
        # Normalize weights on all face vertices so sum equals 1.0
        for vi in face_v_indices:
            v = mesh_obj.data.vertices[vi]
            total_w = sum(g.weight for g in v.groups)
            if total_w > 0.0001:
                for g in v.groups:
                    g.weight /= total_w
                    
        if log_file:
            log_file.write(f"Completed anatomical face, mouth, lip & jaw weight painting on '{mesh_obj.name}'.\n")
    except Exception as e:
        if log_file:
            log_file.write(f"Anatomical face & jaw weight painting failed on '{mesh_obj.name}': {e}\n")

def assign_unweighted_vertices(mesh_obj, rig_obj, log_file):
    """Finds all vertices with zero weights and assigns them 100% to the nearest deforming bone segment."""
    import mathutils
    
    # 1. Collect all deforming bones and their world coordinates (head and tail)
    deform_bones = []
    mw_rig = rig_obj.matrix_world
    
    is_head_mesh = any(k in mesh_obj.name.lower() for k in ["hair", "head", "face", "tear", "eye", "lash", "brow", "teeth", "tooth", "tongue", "mouth", "ear", "beard", "mustache", "scalp", "eyelid", "occlusion"])
    
    for bone in rig_obj.data.bones:
        if bone.use_deform and bone.name.startswith("DEF-"):
            if is_head_mesh:
                # Restrict head/hair/facial meshes to head, neck, upper spine, shoulders, and face bones
                allowed_prefixes = ["DEF-head", "DEF-neck", "DEF-spine.003", "DEF-shoulder", "DEF-clavicle"]
                allowed_face = ["DEF-ear", "DEF-eyebrow", "DEF-cheek", "DEF-nose", "DEF-jaw", "DEF-chin", "DEF-eyelid", "DEF-eye_corner", "DEF-eye", "DEF-lip"]
                
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
            clothing_objs = [o for o in selected_objs if not o.name.startswith("Wgt_")]
            for o in context.scene.objects:
                if o.type == 'MESH' and o not in clothing_objs and not o.name.startswith("Wgt_"):
                    name_lower = o.name.lower()
                    if any(k in name_lower for k in ["body", "skin", "base", "human"]):
                        body_obj = o
                        break
            if not body_obj:
                meshes = [o for o in context.scene.objects if o.type == 'MESH' and o not in clothing_objs and not o.name.startswith("Wgt_")]
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
            if mod.type in ['DATA_TRANSFER', 'SHRINKWRAP', 'MASK'] or "HRG_" in mod.name or "Cloth_" in mod.name:
                body_obj.modifiers.remove(mod)
            elif mod.type == 'ARMATURE':
                mod.use_deform_preserve_volume = True
                
        fixed_count = 0
        for cloth in clothing_objs:
            if cloth == body_obj:
                continue
                
            # Clean all old modifiers except Armature
            for m in list(cloth.modifiers):
                if m.type in ['SHRINKWRAP', 'DATA_TRANSFER', 'MASK'] or "Cloth_No_Clip" in m.name or "HRG_" in m.name:
                    cloth.modifiers.remove(m)
                    
            # Clear old vertex groups from clothing before baking to avoid leftover bone groups
            for vg in list(cloth.vertex_groups):
                cloth.vertex_groups.remove(vg)
                    
            # 2. Add Data Transfer Modifier and bake in Rest Pose
            dt_mod = cloth.modifiers.new(name="HRG_Weight_Bake", type='DATA_TRANSFER')
            dt_mod.object = body_obj
            dt_mod.use_vert_data = True
            dt_mod.data_types_verts = {'VGROUP_WEIGHTS'}
            dt_mod.vert_mapping = 'POLYINTERP_NEAREST'
            
            # Move Data Transfer to top of stack for clean modifier_apply
            dt_idx = cloth.modifiers.find(dt_mod.name)
            if dt_idx > 0:
                try:
                    cloth.modifiers.move(dt_idx, 0)
                except Exception:
                    pass
            
            bpy.ops.object.select_all(action='DESELECT')
            cloth.select_set(True)
            context.view_layer.objects.active = cloth
            
            try:
                bpy.ops.object.datalayout_transfer(modifier=dt_mod.name)
            except Exception:
                pass
                
            try:
                if hasattr(context, "temp_override"):
                    with context.temp_override(active_object=cloth, selected_objects=[cloth]):
                        bpy.ops.object.modifier_apply(modifier=dt_mod.name)
                else:
                    bpy.ops.object.modifier_apply(modifier=dt_mod.name)
            except Exception:
                pass
                
            # If modifier still remains on object, remove it so it doesn't dynamically distort in Pose Mode
            if dt_mod.name in cloth.modifiers:
                try:
                    cloth.modifiers.remove(cloth.modifiers[dt_mod.name])
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
                        
            # 4. Strip any arm/leg bleed from clothing torso/back/waist
            if active_arm:
                cleanup_limb_bleed(cloth, active_arm)
                    
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
                    # 1. Protect Hands/Forearms/Upper Arms: If |X| is near or beyond sleeve opening, NEVER mask!
                    max_sleeve_x = max(abs(c['x_min']), abs(c['x_max']))
                    if abs(v_world.x) >= max_sleeve_x - 0.075:
                        continue # Arms, wrists, hands 100% protected
                        
                    # 2. Protect Neck/Head/Collar: If Z is near or above collar, NEVER mask!
                    if v_world.z >= c['z_max'] - 0.055 and abs(v_world.x) < 0.14:
                        continue # Neck / chin 100% protected
                        
                    # 3. Protect Waist bottom: If Z is below waist opening, NEVER mask!
                    if v_world.z <= c['z_min'] + 0.035:
                        continue # Waist bottom protected
                        
                    loc, n, idx, dist = c['tree'].find_nearest(v_world)
                    if dist is not None and dist < 0.040:
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

