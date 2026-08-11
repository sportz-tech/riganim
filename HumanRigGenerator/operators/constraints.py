# operators/constraints.py
import bpy
from ..utils.bones import add_constraint
from ..utils.naming import get_control_name, get_mch_name, get_org_name, get_deform_name

# Legacy driver setup removed in favor of native PoseBone property callbacks

def setup_all_constraints(obj, rig_type="HUMAN"):
    """Sets up pose constraints for IK/FK blending and deform copying in POSE mode."""
    # Ensure we are in POSE mode
    if obj.type != 'ARMATURE':
        return
        
    # 1. Initialize IK_FK properties on IK handles
    for side in [".L", ".R"]:
        # Arm IK switch
        pb_hand_ik = obj.pose.bones.get(get_control_name(f"hand_IK{side}"))
        if pb_hand_ik:
            pb_hand_ik.hrg_ik_fk = 1.0 # Default to IK
            
        # Leg IK switch
        pb_foot_ik = obj.pose.bones.get(get_control_name(f"foot_IK{side}"))
        if pb_foot_ik:
            pb_foot_ik.hrg_ik_fk = 1.0 # Default to IK

    # 2. Add Blend Constraints to ORG- bones
    if rig_type in ['ANIMAL', 'BIRD']:
        limbs = [
            # Arm/Wing Left
            ("upper_arm.L", "upper_arm_FK.L", "upper_arm_IK.L", "hand_IK.L"),
            ("forearm.L", "forearm_FK.L", "forearm_IK.L", "hand_IK.L"),
            ("hand.L", "hand_FK.L", "hand_IK.L", "hand_IK.L"),
            
            # Arm/Wing Right
            ("upper_arm.R", "upper_arm_FK.R", "upper_arm_IK.R", "hand_IK.R"),
            ("forearm.R", "forearm_FK.R", "forearm_IK.R", "hand_IK.R"),
            ("hand.R", "hand_FK.R", "hand_IK.R", "hand_IK.R"),
            
            # Leg Left (thigh is pelvis attachment, shin and foot are the IK chain)
            ("shin.L", "shin_FK.L", "shin_IK.L", "foot_IK.L"),
            ("foot.L", "foot_FK.L", "foot_IK.L", "foot_IK.L"),
            
            # Leg Right
            ("shin.R", "shin_FK.R", "shin_IK.R", "foot_IK.R"),
            ("foot.R", "foot_FK.R", "foot_IK.R", "foot_IK.R"),
        ]
    else: # HUMAN
        limbs = [
            # Arm Left
            ("upper_arm.L", "upper_arm_FK.L", "upper_arm_IK.L", "hand_IK.L"),
            ("forearm.L", "forearm_FK.L", "forearm_IK.L", "hand_IK.L"),
            ("hand.L", "hand_FK.L", "hand_IK.L", "hand_IK.L"),
            
            # Arm Right
            ("upper_arm.R", "upper_arm_FK.R", "upper_arm_IK.R", "hand_IK.R"),
            ("forearm.R", "forearm_FK.R", "forearm_IK.R", "hand_IK.R"),
            ("hand.R", "hand_FK.R", "hand_IK.R", "hand_IK.R"),
            
            # Leg Left
            ("thigh.L", "thigh_FK.L", "thigh_IK.L", "foot_IK.L"),
            ("shin.L", "shin_FK.L", "shin_IK.L", "foot_IK.L"),
            ("foot.L", "foot_FK.L", "foot_IK.L", "foot_IK.L"),
            ("toe.L", "toe_FK.L", "toe_IK.L", "foot_IK.L"),
            
            # Leg Right
            ("thigh.R", "thigh_FK.R", "thigh_IK.R", "foot_IK.R"),
            ("shin.R", "shin_FK.R", "shin_IK.R", "foot_IK.R"),
            ("foot.R", "foot_FK.R", "foot_IK.R", "foot_IK.R"),
            ("toe.R", "toe_FK.R", "toe_IK.R", "foot_IK.R"),
        ]
    
    for org_base, fk_base, ik_base, switch_base in limbs:
        org_name = get_org_name(org_base)
        fk_name = get_control_name(fk_base)
        
        # Determine if target is MCH or CTRL
        ik_name = get_mch_name(ik_base)
        if not obj.pose.bones.get(ik_name):
            ik_name = get_control_name(ik_base)
            
        switch_name = get_control_name(switch_base)
        
        pb_org = obj.pose.bones.get(org_name)
        if pb_org:
            # Check if this is the root of the limb chain (only roots copy location)
            is_root = ("upper_arm" in org_base) or ("thigh" in org_base)
            
            if is_root:
                # Copy Location targeting FK (influence driven by 1 - IK_FK)
                c_fk_loc = add_constraint(pb_org, 'COPY_LOCATION', "Copy_FK_Loc", obj, target_bone=fk_name)
                c_fk_loc.influence = 0.0
                
                # Copy Location targeting IK (influence driven by IK_FK)
                c_ik_loc = add_constraint(pb_org, 'COPY_LOCATION', "Copy_IK_Loc", obj, target_bone=ik_name)
                c_ik_loc.influence = 1.0
            
            # Copy Rotation targeting FK (influence driven by 1 - IK_FK)
            c_fk_rot = add_constraint(pb_org, 'COPY_ROTATION', "Copy_FK_Rot", obj, target_bone=fk_name)
            c_fk_rot.influence = 0.0
            
            # Copy Rotation targeting IK (influence driven by IK_FK)
            c_ik_rot = add_constraint(pb_org, 'COPY_ROTATION', "Copy_IK_Rot", obj, target_bone=ik_name)
            c_ik_rot.influence = 1.0
            
    # For Animal/Bird, add direct constraints for thigh and toe
    if rig_type in ['ANIMAL', 'BIRD']:
        for side in [".L", ".R"]:
            # thigh copies FK at all times (since it's a pelvis hip-attachment bone)
            org_thigh = get_org_name(f"thigh{side}")
            fk_thigh = get_control_name(f"thigh_FK{side}")
            pb_org_thigh = obj.pose.bones.get(org_thigh)
            if pb_org_thigh and obj.pose.bones.get(fk_thigh):
                add_constraint(pb_org_thigh, 'COPY_TRANSFORMS', "Copy_FK", obj, target_bone=fk_thigh)
                
            # toe custom blending (copies FK in FK mode, copies CTRL-foot_IK rotation in IK mode to stay flat)
            org_toe = get_org_name(f"toe{side}")
            fk_toe = get_control_name(f"toe_FK{side}")
            ctrl_foot = get_control_name(f"foot_IK{side}")
            pb_org_toe = obj.pose.bones.get(org_toe)
            if pb_org_toe and obj.pose.bones.get(fk_toe) and obj.pose.bones.get(ctrl_foot):
                # Remove existing Copy_FK_Loc/Copy_FK_Rot/Copy_IK_Rot if they exist
                for c in list(pb_org_toe.constraints):
                    if c.name in ["Copy_FK_Loc", "Copy_FK_Rot", "Copy_IK_Rot", "Copy_FK", "Copy_IK"]:
                        pb_org_toe.constraints.remove(c)
                        
                # 1. Copy Location from FK (influence driven by 1 - IK_FK)
                c_loc_fk = add_constraint(pb_org_toe, 'COPY_LOCATION', "Copy_FK_Loc", obj, target_bone=fk_toe)
                c_loc_fk.influence = 0.0
                
                # 2. Copy Rotation from FK (influence driven by 1 - IK_FK)
                c_rot_fk = add_constraint(pb_org_toe, 'COPY_ROTATION', "Copy_FK_Rot", obj, target_bone=fk_toe)
                c_rot_fk.influence = 0.0
                
                # 3. Copy Rotation from IK (influence driven by IK_FK)
                c_rot_ik = add_constraint(pb_org_toe, 'COPY_ROTATION', "Copy_IK_Rot", obj, target_bone=ctrl_foot)
                c_rot_ik.influence = 1.0

    # Shoulder rotation constraints (ORG copies CTRL rotation)
    for side in [".L", ".R"]:
        org_sh = obj.pose.bones.get(get_org_name(f"shoulder{side}"))
        ctrl_sh = obj.pose.bones.get(get_control_name(f"shoulder{side}"))
        if org_sh and ctrl_sh:
            # Clear existing to prevent duplicates
            for c in list(org_sh.constraints):
                if c.name == "Copy_Rot_CTRL":
                    org_sh.constraints.remove(c)
            add_constraint(org_sh, 'COPY_ROTATION', "Copy_Rot_CTRL", obj, target_bone=ctrl_sh.name)

    # 3. Add Copy Constraints from ORG- to DEF- bones
    # For central bones
    spine_bones = ["pelvis", "spine", "spine.001", "spine.002", "spine.003", "neck", "head", "jaw", "chin", "nose", "tail.001", "tail.002", "tail.003"]
    for bone_name in spine_bones:
        def_name = get_deform_name(bone_name)
        org_name = get_org_name(bone_name)
        
        pb_def = obj.pose.bones.get(def_name)
        if pb_def and obj.pose.bones.get(org_name):
            add_constraint(pb_def, 'COPY_TRANSFORMS', "Copy_ORG", obj, target_bone=org_name)
            
    # For limb bones
    limb_mapping = [
        # Arms Left
        ("shoulder.L", "shoulder.L"),
        ("upper_arm.L", "upper_arm.L"),
        ("forearm.L", "forearm.L"),
        ("hand.L", "hand.L"),
        
        # Arms Right
        ("shoulder.R", "shoulder.R"),
        ("upper_arm.R", "upper_arm.R"),
        ("forearm.R", "forearm.R"),
        ("hand.R", "hand.R"),
        
        # Legs Left
        ("thigh.L", "thigh.L"),
        ("shin.L", "shin.L"),
        ("foot.L", "foot.L"),
        ("toe.L", "toe.L"),
        
        # Legs Right
        ("thigh.R", "thigh.R"),
        ("shin.R", "shin.R"),
        ("foot.R", "foot.R"),
        ("toe.R", "toe.R"),
    ]
    
    for def_base, org_base in limb_mapping:
        def_name = get_deform_name(def_base)
        org_name = get_org_name(org_base)
        
        pb_def = obj.pose.bones.get(def_name)
        if pb_def and obj.pose.bones.get(org_name):
            # Terminal bones (hand, foot, toe, eye) copy rotation only to prevent scale/location distortion
            if "hand" in def_base or "foot" in def_base or "toe" in def_base or def_base.startswith("eye."):
                add_constraint(pb_def, 'COPY_ROTATION', "Copy_Rot_ORG", obj, target_bone=org_name)
                
                # Prevent inheriting parent stretching scale to keep hand/foot shape perfectly rigid
                try:
                    pb_def.inherit_scale = 'NONE'
                except AttributeError:
                    try:
                        pb_def.use_inherit_scale = False
                    except Exception:
                        pass
            else:
                # Arm/Leg stretching bones copy all transforms (including scale) to prevent skeletal gaps during IK stretch
                add_constraint(pb_def, 'COPY_TRANSFORMS', "Copy_ORG", obj, target_bone=org_name)
            
    # For fingers and face detail bones (they copy ORG directly)
    # We can fetch all bones starting with DEF- and check if they have a corresponding ORG- bone.
    # If they are not already constrained, we copy transforms.
    for pb in obj.pose.bones:
        if pb.name.startswith("DEF-"):
            org_counterpart = pb.name.replace("DEF-", "ORG-")
            if obj.pose.bones.get(org_counterpart) and not pb.constraints:
                add_constraint(pb, 'COPY_TRANSFORMS', "Copy_ORG", obj, target_bone=org_counterpart)
                
    # Eye and eyelid constraints setup
    setup_eye_constraints(obj)
    setup_mouth_corner_constraints(obj)

def setup_eye_constraints(obj):
    """Sets up Track To constraints for the eyes and custom properties/drivers for eyelid blinking."""
    ctrl_eyes = obj.pose.bones.get(get_control_name("eyes_look"))
    if ctrl_eyes:
        for side in [".L", ".R"]:
            prop_name = f"eye_close{side}"
            if prop_name not in ctrl_eyes:
                ctrl_eyes[prop_name] = 0.0
                
            id_properties = ctrl_eyes.id_properties_ui(prop_name)
            id_properties.update(
                min=0.0,
                max=1.0,
                default=0.0,
                description=f"Close {'Left' if side == '.L' else 'Right'} Eye"
            )
            
    # Add Damped Track constraints on ORG-eye.L and ORG-eye.R targeting CTRL-eye_look.L and CTRL-eye_look.R
    for side in [".L", ".R"]:
        org_eye = obj.pose.bones.get(get_org_name(f"eye{side}"))
        ctrl_look = get_control_name(f"eye_look{side}")
        if org_eye and obj.pose.bones.get(ctrl_look):
            for c in list(org_eye.constraints):
                if c.name in ["Track_To_Target", "Damped_Track_Target"]:
                    org_eye.constraints.remove(c)
                    
            c = add_constraint(org_eye, 'DAMPED_TRACK', "Damped_Track_Target", obj, target_bone=ctrl_look)
            c.track_axis = 'TRACK_Y'
            
    # Add drivers to upper and lower 3-bone curved eyelids rotation around local X axis
    for side in [".L", ".R"]:
        prop_owner = get_control_name("eyes_look")
        prop_name = f"eye_close{side}"
        
        # Upper eyelid 3-bone curve: geometric closure from +33.7° resting angle to 0° horizontal eye slit
        upper_configs = [
            ("eyelid.upper.01", -0.26), # -14.9 deg (inner slope)
            ("eyelid.upper.02", -0.38), # -21.8 deg (apex closure)
            ("eyelid.upper.03", -0.30), # -17.2 deg (outer slope)
            ("eyelid.upper", -0.38),    # -21.8 deg (apex closure)
        ]
        
        for part, coeff in upper_configs:
            org_up = obj.pose.bones.get(get_org_name(f"{part}{side}"))
            if org_up and ctrl_eyes:
                if org_up.rotation_mode != 'XYZ':
                    org_up.rotation_mode = 'XYZ'
                org_up.driver_remove("rotation_euler", 0)
                
                fcurve = org_up.driver_add("rotation_euler", 0)
                driver = fcurve.driver
                driver.type = 'SCRIPTED'
                driver.expression = f"{coeff} * close"
                
                var = driver.variables.new()
                var.name = "close"
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id_type = 'OBJECT'
                target.id = obj
                target.data_path = f'pose.bones["{prop_owner}"]["{prop_name}"]'
                
        # Lower eyelid 3-bone curve: subtle upward meeting
        lower_configs = [
            ("eyelid.lower.01", 0.07),
            ("eyelid.lower.02", 0.12),
            ("eyelid.lower.03", 0.08),
            ("eyelid.lower", 0.12),
        ]
        
        for part, coeff in lower_configs:
            org_low = obj.pose.bones.get(get_org_name(f"{part}{side}"))
            if org_low and ctrl_eyes:
                if org_low.rotation_mode != 'XYZ':
                    org_low.rotation_mode = 'XYZ'
                org_low.driver_remove("rotation_euler", 0)
                
                fcurve = org_low.driver_add("rotation_euler", 0)
                driver = fcurve.driver
                driver.type = 'SCRIPTED'
                driver.expression = f"{coeff} * close"
                
                var = driver.variables.new()
                var.name = "close"
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id_type = 'OBJECT'
                target.id = obj
                target.data_path = f'pose.bones["{prop_owner}"]["{prop_name}"]'
            
        # Add drivers to inner and outer eye corners rotation around local X axis
        for part, coeff in [("eye_corner.inner", -0.01), ("eye_corner.outer", -0.01)]:
            org_corner = obj.pose.bones.get(get_org_name(f"{part}{side}"))
            if org_corner and ctrl_eyes:
                if org_corner.rotation_mode != 'XYZ':
                    org_corner.rotation_mode = 'XYZ'
                org_corner.driver_remove("rotation_euler", 0)
                
                fcurve = org_corner.driver_add("rotation_euler", 0)
                driver = fcurve.driver
                driver.type = 'SCRIPTED'
                driver.expression = f"{coeff} * close"
                
                var = driver.variables.new()
                var.name = "close"
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id_type = 'OBJECT'
                target.id = obj
                target.data_path = f'pose.bones["{prop_owner}"]["{prop_name}"]'
                
    # 4. Trigger initial update of constraint influences via Python property callbacks
    for side in [".L", ".R"]:
        for part in ["hand_IK", "foot_IK"]:
            pb_ik = obj.pose.bones.get(get_control_name(f"{part}{side}"))
            if pb_ik:
                # Triggers the update callback
                pb_ik.hrg_ik_fk = pb_ik.hrg_ik_fk
                
def setup_mouth_corner_constraints(obj):
    """Sets up drivers on mouth corner bones to follow the jaw by 50% in POSE space, preventing splitting."""
    pose_bones = obj.pose.bones
    
    org_jaw = pose_bones.get("ORG-jaw")
    if org_jaw:
        # Scale can be estimated from the jaw's rest height relative to default 1.6m
        scale = org_jaw.bone.matrix_local.translation.z / 1.60
        
        for side in [".L", ".R"]:
            bone_name = f"ORG-lip.corner{side}"
            pb = pose_bones.get(bone_name)
            if pb:
                # Remove any legacy mouth corner constraints to prevent conflicts
                for c in list(pb.constraints):
                    if c.name in ["Child_Of_Jaw_Corner", "Copy_Jaw_Corner", "Copy_MouthRoot_Corner"]:
                        pb.constraints.remove(c)
                        
                # Add Driver for Z Location (height follow)
                pb.driver_remove("location", 2) # 2 is Z index
                fcurve_z = pb.driver_add("location", 2)
                drv_z = fcurve_z.driver
                drv_z.type = 'SCRIPTED'
                drv_z.expression = f"(-0.05 * {scale}) * jaw_rot"
                
                var_z = drv_z.variables.new()
                var_z.name = "jaw_rot"
                var_z.type = 'TRANSFORMS'
                target_z = var_z.targets[0]
                target_z.id = obj
                target_z.bone_target = "ORG-jaw"
                target_z.transform_type = 'ROT_X'
                target_z.transform_space = 'TRANSFORM_SPACE'
                
                # Add Driver for Y Location (depth follow)
                pb.driver_remove("location", 1) # 1 is Y index
                fcurve_y = pb.driver_add("location", 1)
                drv_y = fcurve_y.driver
                drv_y.type = 'SCRIPTED'
                drv_y.expression = f"(-0.02 * {scale}) * jaw_rot"
                
                var_y = drv_y.variables.new()
                var_y.name = "jaw_rot"
                var_y.type = 'TRANSFORMS'
                target_y = var_y.targets[0]
                target_y.id = obj
                target_y.bone_target = "ORG-jaw"
                target_y.transform_type = 'ROT_X'
                target_y.transform_space = 'TRANSFORM_SPACE'
                

