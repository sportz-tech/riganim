# operators/generate_fk.py
import mathutils
from ..utils.bones import create_bone, assign_to_collection
from ..utils.naming import get_control_name, get_org_name

def generate_fk_controls(arm_data):
    """Generates FK control bones in EDIT mode (Left and Right)."""
    # FK Chains list: (base_name, parent_name, connect)
    fk_chains = [
        # Arms FK
        ("upper_arm_FK.L", "shoulder.L", False),
        ("forearm_FK.L", "upper_arm_FK.L", True),
        ("hand_FK.L", "forearm_FK.L", True),
        
        ("upper_arm_FK.R", "shoulder.R", False),
        ("forearm_FK.R", "upper_arm_FK.R", True),
        ("hand_FK.R", "forearm_FK.R", True),
        
        # Legs FK
        ("thigh_FK.L", "pelvis", False),
        ("shin_FK.L", "thigh_FK.L", True),
        ("foot_FK.L", "shin_FK.L", True),
        ("toe_FK.L", "foot_FK.L", True),
        
        ("thigh_FK.R", "pelvis", False),
        ("shin_FK.R", "thigh_FK.R", True),
        ("foot_FK.R", "shin_FK.R", True),
        ("toe_FK.R", "foot_FK.R", True),
    ]
    
    for base_name, parent_base, connect in fk_chains:
        ctrl_name = get_control_name(base_name)
        
        # Get source ORG bone position
        # Suffix handling
        org_source_name = base_name.replace("_FK", "")
        org_bone = arm_data.edit_bones.get(get_org_name(org_source_name))
        if not org_bone:
            continue
            
        parent_name = get_control_name(parent_base) if "_FK" in parent_base else get_org_name(parent_base)
        if not arm_data.edit_bones.get(parent_name):
            # Fallback to org if control doesn't exist
            parent_name = get_org_name(parent_name.replace("CTRL-", ""))
            
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
        
        collection_name = "Arms FK" if "arm" in base_name or "hand" in base_name else "Legs FK"
        assign_to_collection(arm_data, ctrl_name, collection_name)
