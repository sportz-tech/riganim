# operators/generate_ik.py
import mathutils
import bpy
from ..utils.bones import create_bone, assign_to_collection, add_constraint, get_marker_pos
from ..utils.naming import get_control_name, get_mch_name, get_org_name

def calculate_pole_position(start_pos, mid_pos, end_pos, is_knee=True):
    """Calculates a scale- and rotation-invariant pole target position."""
    axis = end_pos - start_pos
    axis_len_sq = axis.length_squared
    
    if axis_len_sq > 0:
        proj = start_pos + axis * ((mid_pos - start_pos).dot(axis) / axis_len_sq)
        bend = mid_pos - proj
        if bend.length < 0.001:
            # Fallback to typical orientation: knees bend forward (-Y), elbows bend backward (+Y)
            direction = mathutils.Vector((0.0, -1.0, 0.0)) if is_knee else mathutils.Vector((0.0, 1.0, 0.0))
        else:
            direction = bend.normalized()
            # Anatomical correction: force elbows backward (+Y) and knees forward (-Y)
            if not is_knee and direction.y < 0:
                direction = -direction
            elif is_knee and direction.y > 0:
                direction = -direction
    else:
        direction = mathutils.Vector((0.0, -1.0, 0.0)) if is_knee else mathutils.Vector((0.0, 1.0, 0.0))
        
    distance = (start_pos - end_pos).length * (1.0 if is_knee else 0.8)
    if distance < 0.1:
        distance = 0.5 if is_knee else 0.4
        
    return mid_pos + direction * distance

def generate_ik_bones_edit(arm_data, rig_type="HUMAN", marker_positions=None):
    """Generates IK control and mechanism bones in EDIT mode (Left and Right)."""
    # 1. Arm IK Setup
    for side in [".L", ".R"]:
        # MCH IK Bones
        org_uarm = arm_data.edit_bones.get(get_org_name(f"upper_arm{side}"))
        org_farm = arm_data.edit_bones.get(get_org_name(f"forearm{side}"))
        org_hand = arm_data.edit_bones.get(get_org_name(f"hand{side}"))
        
        if org_uarm and org_farm and org_hand:
            mch_uarm = get_mch_name(f"upper_arm_IK{side}")
            mch_farm = get_mch_name(f"forearm_IK{side}")
            
            create_bone(arm_data, mch_uarm, org_uarm.head.copy(), org_uarm.tail.copy(), org_uarm.roll,
                        parent_name=get_org_name(f"shoulder{side}"), use_connect=False, is_deform=False)
            create_bone(arm_data, mch_farm, org_farm.head.copy(), org_farm.tail.copy(), org_farm.roll,
                        parent_name=mch_uarm, use_connect=True, is_deform=False)
                        
            assign_to_collection(arm_data, mch_uarm, "Arms MCH")
            assign_to_collection(arm_data, mch_farm, "Arms MCH")
            
            # Hand IK Control
            ctrl_hand_ik = get_control_name(f"hand_IK{side}")
            # Pointing slightly down/out from the wrist
            dir_vec = (org_hand.tail - org_hand.head).normalized()
            hand_ik_tail = org_hand.head + dir_vec * 0.15
            
            create_bone(arm_data, ctrl_hand_ik, org_hand.head.copy(), hand_ik_tail, org_hand.roll,
                        parent_name=get_control_name("root"), use_connect=False, is_deform=False)
            assign_to_collection(arm_data, ctrl_hand_ik, "Arms IK")
            
            # Elbow Pole Target Control
            ctrl_elbow = get_control_name(f"elbow_IK{side}")
            # Push behind the elbow dynamically
            elbow_pos = calculate_pole_position(org_uarm.head, org_farm.head, org_hand.head, is_knee=False)
            elbow_tail = elbow_pos.copy()
            elbow_tail.z += 0.05
            
            parent_spine = get_control_name("spine.003") if arm_data.edit_bones.get(get_control_name("spine.003")) else None
            create_bone(arm_data, ctrl_elbow, elbow_pos, elbow_tail, 0.0,
                        parent_name=parent_spine, use_connect=False, is_deform=False)
            assign_to_collection(arm_data, ctrl_elbow, "Arms IK")
            
    # 2. Leg IK Setup
    for side in [".L", ".R"]:
        # Get floor level for the controllers dynamically
        toe_pos_z = 0.02
        if rig_type == 'ANIMAL':
            toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.18, -0.42, 0.02), marker_positions)
            toe_pos_z = toe_pos.z
        elif rig_type == 'BIRD':
            toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.09, 0.08, 0.02), marker_positions)
            toe_pos_z = toe_pos.z
        else:
            toe_pos = get_marker_pos("Mkr_foot_toe.L", (0.13, 0.16, 0.02), marker_positions)
            toe_pos_z = toe_pos.z

        # MCH IK Bones
        org_thigh = arm_data.edit_bones.get(get_org_name(f"thigh{side}"))
        org_shin = arm_data.edit_bones.get(get_org_name(f"shin{side}"))
        org_foot = arm_data.edit_bones.get(get_org_name(f"foot{side}"))
        org_toe = arm_data.edit_bones.get(get_org_name(f"toe{side}"))
        
        if rig_type in ['ANIMAL', 'BIRD']:
            # For Animal/Bird, the active leg IK chain consists of shin and foot (femur and tibia equivalents)
            if org_shin and org_foot:
                mch_shin = get_mch_name(f"shin_IK{side}")
                mch_foot = get_mch_name(f"foot_IK{side}")
                
                # Parent of shin_IK is ORG-thigh (clavicle/pelvis attachment equivalent)
                parent_name = get_org_name(f"thigh{side}")
                
                create_bone(arm_data, mch_shin, org_shin.head.copy(), org_shin.tail.copy(), org_shin.roll,
                            parent_name=parent_name, use_connect=False, is_deform=False)
                create_bone(arm_data, mch_foot, org_foot.head.copy(), org_foot.tail.copy(), org_foot.roll,
                            parent_name=mch_shin, use_connect=True, is_deform=False)
                
                assign_to_collection(arm_data, mch_shin, "Legs MCH")
                assign_to_collection(arm_data, mch_foot, "Legs MCH")
                
                # Controller: CTRL-foot_IK.L
                ctrl_foot_ik = get_control_name(f"foot_IK{side}")
                # Place it on the ground under the ankle (org_foot.tail is ankle_pos)
                foot_ik_head = org_foot.tail.copy()
                foot_ik_head.z = toe_pos_z
                foot_ik_tail = foot_ik_head.copy()
                foot_ik_tail.y += 0.15
                
                create_bone(arm_data, ctrl_foot_ik, foot_ik_head, foot_ik_tail, 0.0,
                            parent_name=get_control_name("root"), use_connect=False, is_deform=False)
                assign_to_collection(arm_data, ctrl_foot_ik, "Legs IK")
                
                # Knee Pole Target (aligned dynamically in front of the knee/hock joint)
                ctrl_knee = get_control_name(f"knee_IK{side}")
                knee_pos = calculate_pole_position(org_shin.head, org_foot.head, org_foot.tail, is_knee=True)
                knee_tail = knee_pos.copy()
                knee_tail.z += 0.05
                
                parent_pelvis = get_control_name("spine") if arm_data.edit_bones.get(get_control_name("spine")) else None
                create_bone(arm_data, ctrl_knee, knee_pos, knee_tail, 0.0,
                            parent_name=parent_pelvis, use_connect=False, is_deform=False)
                assign_to_collection(arm_data, ctrl_knee, "Legs IK")
                
        else: # HUMAN
            if org_thigh and org_shin and org_foot:
                mch_thigh = get_mch_name(f"thigh_IK{side}")
                mch_shin = get_mch_name(f"shin_IK{side}")
                
                create_bone(arm_data, mch_thigh, org_thigh.head.copy(), org_thigh.tail.copy(), org_thigh.roll,
                            parent_name=get_org_name(f"pelvis"), use_connect=False, is_deform=False)
                create_bone(arm_data, mch_shin, org_shin.head.copy(), org_shin.tail.copy(), org_shin.roll,
                            parent_name=mch_thigh, use_connect=True, is_deform=False)
                            
                assign_to_collection(arm_data, mch_thigh, "Legs MCH")
                assign_to_collection(arm_data, mch_shin, "Legs MCH")
                
                # MCH-foot_IK (goes ankle to ball, parented to MCH-foot_roll_ball)
                mch_foot = get_mch_name(f"foot_IK{side}")
                create_bone(arm_data, mch_foot, org_foot.head.copy(), org_foot.tail.copy(), org_foot.roll,
                            parent_name=get_mch_name(f"foot_roll_ball{side}"), use_connect=False, is_deform=False)
                assign_to_collection(arm_data, mch_foot, "Legs MCH")
                
                # MCH-toe_IK (goes ball to toe tip, parented to MCH-foot_roll_toe)
                if org_toe:
                    mch_toe = get_mch_name(f"toe_IK{side}")
                    create_bone(arm_data, mch_toe, org_toe.head.copy(), org_toe.tail.copy(), org_toe.roll,
                                parent_name=get_mch_name(f"foot_roll_toe{side}"), use_connect=False, is_deform=False)
                    assign_to_collection(arm_data, mch_toe, "Legs MCH")
                
                # Controller: CTRL-foot_IK
                ctrl_foot_ik = get_control_name(f"foot_IK{side}")
                foot_ik_head = org_foot.head.copy()
                foot_ik_head.z = toe_pos_z
                foot_ik_tail = foot_ik_head.copy()
                foot_ik_tail.y += 0.15
                
                create_bone(arm_data, ctrl_foot_ik, foot_ik_head, foot_ik_tail, 0.0,
                            parent_name=get_control_name("root"), use_connect=False, is_deform=False)
                assign_to_collection(arm_data, ctrl_foot_ik, "Legs IK")
                
                # Knee Pole Target (aligned dynamically)
                ctrl_knee = get_control_name(f"knee_IK{side}")
                knee_pos = calculate_pole_position(org_thigh.head, org_shin.head, org_shin.tail, is_knee=True)
                knee_tail = knee_pos.copy()
                knee_tail.z += 0.05
                
                parent_pelvis = get_control_name("spine") if arm_data.edit_bones.get(get_control_name("spine")) else None
                create_bone(arm_data, ctrl_knee, knee_pos, knee_tail, 0.0,
                            parent_name=parent_pelvis, use_connect=False, is_deform=False)
                assign_to_collection(arm_data, ctrl_knee, "Legs IK")
                
                # Parent the foot roll mechanism to the Foot IK controller
                toe_mch = arm_data.edit_bones.get(get_mch_name(f"foot_roll_toe{side}"))
                if toe_mch:
                    toe_mch.parent = arm_data.edit_bones.get(ctrl_foot_ik)

def generate_ik_constraints_pose(obj, rig_type="HUMAN"):
    """Sets up constraints for IK bones in POSE mode."""
    # 1. Arm IK constraints
    for side in [".L", ".R"]:
        pb_farm_ik = obj.pose.bones.get(get_mch_name(f"forearm_IK{side}"))
        if pb_farm_ik:
            pole_angle = 3.14159 if side == ".L" else 0.0
            add_constraint(
                pb_farm_ik,
                'IK',
                "IK_Constraint",
                target_obj=obj,
                target_bone=get_control_name(f"hand_IK{side}"),
                pole_target=obj,
                pole_subtarget=get_control_name(f"elbow_IK{side}"),
                chain_count=2,
                pole_angle=pole_angle
            )
            
            pb_farm_ik.use_ik_limit_x = False
            pb_farm_ik.use_ik_limit_y = False
            pb_farm_ik.use_ik_limit_z = False
            
        pb_uarm_ik = obj.pose.bones.get(get_mch_name(f"upper_arm_IK{side}"))
        if pb_uarm_ik:
            pb_uarm_ik.use_ik_limit_x = False
            pb_uarm_ik.use_ik_limit_y = False
            pb_uarm_ik.use_ik_limit_z = False
            
    # 2. Leg IK constraints
    for side in [".L", ".R"]:
        if rig_type in ['ANIMAL', 'BIRD']:
            pb_ik_bone = obj.pose.bones.get(get_mch_name(f"foot_IK{side}"))
            target_bone = get_control_name(f"foot_IK{side}")
        else:
            pb_ik_bone = obj.pose.bones.get(get_mch_name(f"shin_IK{side}"))
            target_bone = get_mch_name(f"foot_roll_ankle{side}")
            if not obj.pose.bones.get(target_bone):
                target_bone = get_control_name(f"foot_IK{side}")
                
        if pb_ik_bone:
            # -1.5708 for both legs to ensure they both bend forward
            pole_angle = -1.5708
            
            add_constraint(
                pb_ik_bone,
                'IK',
                "IK_Constraint",
                target_obj=obj,
                target_bone=target_bone,
                pole_target=obj,
                pole_subtarget=get_control_name(f"knee_IK{side}"),
                chain_count=2,
                pole_angle=pole_angle
            )
            
            pb_ik_bone.use_ik_limit_x = False
            pb_ik_bone.use_ik_limit_y = False
            pb_ik_bone.use_ik_limit_z = False
            
        pb_thigh_ik = obj.pose.bones.get(get_mch_name(f"thigh_IK{side}"))
        if pb_thigh_ik:
            pb_thigh_ik.use_ik_limit_x = False
            pb_thigh_ik.use_ik_limit_y = False
            pb_thigh_ik.use_ik_limit_z = False
            
        # Hook up human MCH-toe_IK to follow MCH-foot_IK tail (the ball joint)
        if rig_type not in ['ANIMAL', 'BIRD']:
            pb_mch_toe = obj.pose.bones.get(get_mch_name(f"toe_IK{side}"))
            pb_mch_foot = obj.pose.bones.get(get_mch_name(f"foot_IK{side}"))
            if pb_mch_toe and pb_mch_foot:
                # Clear existing Copy_Foot_IK_Tail if it exists
                for c in list(pb_mch_toe.constraints):
                    if c.name == "Copy_Foot_IK_Tail":
                        pb_mch_toe.constraints.remove(c)
                add_constraint(
                    pb_mch_toe,
                    'COPY_LOCATION',
                    "Copy_Foot_IK_Tail",
                    target_obj=obj,
                    target_bone=pb_mch_foot.name,
                    head_tail=1.0
                )
