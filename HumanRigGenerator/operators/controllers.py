# operators/controllers.py
import bpy
import mathutils
from ..utils.bones import create_bone, assign_to_collection, add_constraint
from ..utils.naming import get_control_name, get_org_name, get_deform_name
from ..utils.widgets import (
    get_circle_widget,
    get_cube_widget,
    get_sphere_widget,
    get_arrow_widget,
    get_root_widget
)

def generate_body_controllers_edit(arm_data, gender="MALE"):
    """Generates the primary control bones in EDIT mode."""
    # 1. Root Control
    create_bone(
        arm_data,
        get_control_name("root"),
        mathutils.Vector((0.0, 0.0, 0.0)),
        mathutils.Vector((0.0, 0.2, 0.0)),
        0.0,
        parent_name=None,
        use_connect=False,
        is_deform=False
    )
    assign_to_collection(arm_data, get_control_name("root"), "Root")
    
    # 2. Duplicate spine & neck & head bones to create controllers
    body_ctrls = [
        ("pelvis", get_control_name("root"), False),
        ("spine", get_control_name("pelvis"), False),
        ("spine.001", get_control_name("spine"), True),
        ("spine.002", get_control_name("spine.001"), True),
        ("spine.003", get_control_name("spine.002"), True),
        ("neck", get_control_name("spine.003"), False),
        ("head", get_control_name("neck"), True),
        
        # Tail controllers
        ("tail.001", get_control_name("pelvis"), False),
        ("tail.002", get_control_name("tail.001"), False),
        ("tail.003", get_control_name("tail.002"), False),
        
        # Shoulders
        ("shoulder.L", get_control_name("spine.003"), False),
        ("shoulder.R", get_control_name("spine.003"), False),
        
        # Face details
        ("jaw", get_control_name("head"), False)
    ]
    
    for base_name, parent_name, connect in body_ctrls:
        org_bone = arm_data.edit_bones.get(get_org_name(base_name))
        if not org_bone:
            continue
            
        ctrl_name = get_control_name(base_name)
        create_bone(
            arm_data,
            ctrl_name,
            org_bone.head.copy(),
            org_bone.tail.copy(),
            org_bone.roll,
            parent_name=parent_name,
            use_connect=connect,
            is_deform=False
        )
        
        # Organize bone collections
        collection_name = "Face CTRL" if "jaw" in base_name else "Body CTRL"
        assign_to_collection(arm_data, ctrl_name, collection_name)
        
    # 3. Eyes Target Controllers (placed in front of the head)
    ctrl_head = arm_data.edit_bones.get(get_control_name("head"))
    if ctrl_head:
        for face_ctrl_name in ["CTRL-face_root", "CTRL-jaw"]:
            fc_bone = arm_data.edit_bones.get(face_ctrl_name)
            if fc_bone:
                fc_bone.parent = ctrl_head
                
    eye_l_bone = arm_data.edit_bones.get(get_org_name("eye.L"))
    if eye_l_bone:
        eye_y = eye_l_bone.head.y - 0.15
        eye_z = eye_l_bone.head.z
        
        ctrl_eyes = get_control_name("eyes_look")
        create_bone(arm_data, ctrl_eyes, 
                    mathutils.Vector((0.0, eye_y, eye_z)), 
                    mathutils.Vector((0.0, eye_y, eye_z + 0.05)), 
                    0.0, parent_name=get_control_name("head"), use_connect=False, is_deform=False)
        assign_to_collection(arm_data, ctrl_eyes, "Face CTRL")
        
        # Left eye target
        ctrl_eye_l = get_control_name("eye_look.L")
        create_bone(arm_data, ctrl_eye_l, 
                    mathutils.Vector((eye_l_bone.head.x, eye_y, eye_z)), 
                    mathutils.Vector((eye_l_bone.head.x, eye_y, eye_z + 0.02)), 
                    0.0, parent_name=ctrl_eyes, use_connect=False, is_deform=False)
        assign_to_collection(arm_data, ctrl_eye_l, "Face CTRL")
        
        # Right eye target
        ctrl_eye_r = get_control_name("eye_look.R")
        create_bone(arm_data, ctrl_eye_r, 
                    mathutils.Vector((-eye_l_bone.head.x, eye_y, eye_z)), 
                    mathutils.Vector((-eye_l_bone.head.x, eye_y, eye_z + 0.02)), 
                    0.0, parent_name=ctrl_eyes, use_connect=False, is_deform=False)
        assign_to_collection(arm_data, ctrl_eye_r, "Face CTRL")
        
    # Generate Finger Control Settings Bones
    for side in [".L", ".R"]:
        org_hand = arm_data.edit_bones.get(get_org_name(f"hand{side}"))
        if org_hand:
            ctrl_fingers = get_control_name(f"fingers{side}")
            
            # Find the normal direction of the hand (EditBone.matrix's Z axis)
            local_z = org_hand.matrix.to_3x3() @ mathutils.Vector((0.0, 0.0, 1.0))
            local_z.normalize()
            
            # Place the bone floating 5cm above the hand knuckle
            head_pos = org_hand.tail + local_z * 0.05
            tail_pos = org_hand.tail + local_z * 0.10
            
            create_bone(
                arm_data,
                ctrl_fingers,
                head_pos,
                tail_pos,
                org_hand.roll,
                parent_name=org_hand.name,
                use_connect=False,
                is_deform=False
            )
            assign_to_collection(arm_data, ctrl_fingers, "Arms IK")

def get_bone_base_scale(name):
    """Returns the default base scale (x, y, z) for a given control bone name."""
    if "root" in name:
        return (1.0, 1.0, 1.0)
    elif "pelvis" in name or "spine.003" in name: # Hips and Chest
        return (1.5, 1.5, 1.5)
    elif "neck" in name:
        return (1.2, 1.2, 1.2)
    elif "spine" in name or "tail" in name:
        return (1.2, 1.2, 1.2)
    elif "head" in name:
        return (1.4, 1.4, 1.4)
    elif "shoulder" in name:
        return (0.4, 0.4, 0.4)
    elif "hand_IK" in name:
        return (0.5, 0.5, 0.5)
    elif "foot_IK" in name:
        return (0.7, 1.2, 0.7)
    elif "elbow" in name or "knee" in name:
        return (0.2, 0.2, 0.2)
    elif "FK" in name:
        return (0.4, 0.4, 0.4)
    elif "eyes_look" in name:
        return (0.6, 0.2, 0.2)
    elif "eye_look" in name:
        return (0.1, 0.1, 0.1)
    elif "jaw" in name:
        return (0.6, 0.6, 0.6)
    elif "face_root" in name:
        return (0.8, 0.8, 0.8)
    elif "mouth_root" in name:
        return (0.5, 0.5, 0.5)
    elif "fingers" in name:
        return (0.4, 0.4, 0.4)
    else:
        return (0.15, 0.15, 0.15)


def update_armature_controller_scales(obj, scale):
    """Updates the custom shape scales for all controller bones in the armature."""
    if not obj or obj.type != 'ARMATURE':
        return
    for pb in obj.pose.bones:
        if pb.name.startswith("CTRL-") or pb.custom_shape is not None:
            base_scale = get_bone_base_scale(pb.name)
            pb.custom_shape_scale_xyz = (
                base_scale[0] * scale,
                base_scale[1] * scale,
                base_scale[2] * scale
            )


def setup_controllers_pose(obj):
    """Assigns custom widget shapes and bone color themes in POSE mode."""
    # Ensure widgets exist
    w_root = get_root_widget()
    w_circle_z = get_circle_widget("Wgt_Circle_Z", axis='Z')
    w_circle_x = get_circle_widget("Wgt_Circle_X", axis='X')
    w_cube = get_cube_widget()
    w_sphere = get_sphere_widget()
    w_arrow = get_arrow_widget()
    
    # 1. Setup Bone Colors & Widgets
    for pb in obj.pose.bones:
        name = pb.name
        
        # Color Palettes: Left = Blue (THEME_05), Right = Red (THEME_01), Center = Green (THEME_04)
        if name.startswith("CTRL-"):
            if name.endswith(".L"):
                pb.color.palette = 'THEME05' # Blue
            elif name.endswith(".R"):
                pb.color.palette = 'THEME01' # Red
            else:
                pb.color.palette = 'THEME04' # Green (Center)
                
            # Set key animation control bones to XYZ Euler mode for UI slider control
            if any(k in name for k in ["pelvis", "spine", "neck", "head", "shoulder", "jaw", "hand_IK", "hand_FK", "fingers"]):
                pb.rotation_mode = 'XYZ'
                
            # Assign Widgets
            if "root" in name:
                pb.custom_shape = w_root
            elif "pelvis" in name or "spine.003" in name: # Hips and Chest
                pb.custom_shape = w_circle_z
            elif "neck" in name:
                pb.custom_shape = w_circle_z
                pb.custom_shape_translation = (0.0, pb.bone.length * 0.5, 0.0)
            elif "spine" in name or "tail" in name:
                pb.custom_shape = w_circle_z
            elif "head" in name:
                pb.custom_shape = w_circle_z
                pb.custom_shape_translation = (0.0, pb.bone.length * 0.5, 0.0)
            elif "shoulder" in name:
                pb.custom_shape = w_sphere
            elif "hand_IK" in name:
                pb.custom_shape = w_cube
            elif "foot_IK" in name:
                pb.custom_shape = w_cube
            elif "elbow" in name or "knee" in name:
                pb.custom_shape = w_sphere
            elif "FK" in name:
                # FK limb controls get circular shapes aligned to their axes
                pb.custom_shape = w_circle_x
            elif "eyes_look" in name:
                pb.custom_shape = w_cube
            elif "eye_look" in name:
                pb.custom_shape = w_sphere
            elif "jaw" in name:
                pb.custom_shape = w_circle_z
            elif "face_root" in name:
                pb.custom_shape = w_circle_z
            elif "mouth_root" in name:
                pb.custom_shape = w_circle_z
            elif "fingers" in name:
                pb.custom_shape = w_circle_z
            else:
                # Fallback circle shape for details (fingers, face)
                pb.custom_shape = w_circle_z
                
            # Apply dynamic custom shape scale factoring in the scene setting
            base_scale = get_bone_base_scale(name)
            scale_mult = bpy.context.scene.hrg_controller_scale
            pb.custom_shape_scale_xyz = (
                base_scale[0] * scale_mult,
                base_scale[1] * scale_mult,
                base_scale[2] * scale_mult
            )
                
            # Lock eyeball location and look targets scale/rotation
            if "eye.L" in name or "eye.R" in name:
                pb.lock_location = (True, True, True)
                pb.lock_scale = (True, True, True)
            elif "eyes_look" in name or "eye_look" in name:
                pb.lock_rotation = (True, True, True)
                pb.lock_scale = (True, True, True)
            elif "fingers" in name:
                pb.lock_location = (True, True, True)
                pb.lock_rotation = (True, True, True)
                pb.lock_scale = (True, True, True)
                
    # 2. Add copy constraints from controllers to ORG bones
    # This hooks up the body controls to drive the organizational skeleton.
    body_ctrls = [
        "pelvis", "spine", "spine.001", "spine.002", "spine.003", "neck", "head",
        "face_root", "mouth_root",
        "shoulder.L", "shoulder.R", "jaw",
        "tail.001", "tail.002", "tail.003"
    ]
    for base in body_ctrls:
        ctrl_name = get_control_name(base)
        org_name = get_org_name(base)
        
        pb_org = obj.pose.bones.get(org_name)
        pb_ctrl = obj.pose.bones.get(ctrl_name)
        if pb_org and pb_ctrl:
            # Clear existing constraints from org first to prevent duplicates
            for c in list(pb_org.constraints):
                if c.name == "Copy_CTRL":
                    pb_org.constraints.remove(c)
            # Add copy transforms
            add_constraint(pb_org, 'COPY_TRANSFORMS', "Copy_CTRL", obj, target_bone=ctrl_name)
            
    # 3. Setup finger pose controllers & drivers
    setup_finger_controllers(obj)

def setup_finger_controllers(obj):
    """Sets up the custom properties and initial states for finger curl controls in POSE mode."""
    for side in [".L", ".R"]:
        ctrl_name = get_control_name(f"fingers{side}")
        ctrl_bone = obj.pose.bones.get(ctrl_name)
        if not ctrl_bone:
            continue
            
        # 1. Clean up legacy custom properties (ID properties) if they exist
        for prop in ["grasp", "thumb", "index", "middle", "ring", "pinky"]:
            if prop in ctrl_bone:
                del ctrl_bone[prop]
                
        # 2. Clean up any existing drivers on ORG finger bones to avoid residual driver locks
        from ..utils.naming import get_org_name
        finger_prefixes = ["thumb", "index", "middle", "ring", "pinky"]
        for prefix in finger_prefixes:
            for i in range(1, 4):
                org_bone_name = get_org_name(f"{prefix}.0{i}{side}")
                pb_org = obj.pose.bones.get(org_bone_name)
                if pb_org:
                    pb_org.driver_remove("rotation_euler", 0)
                    
        # 3. Trigger initial callback update
        ctrl_bone.hrg_grasp = 0.0
