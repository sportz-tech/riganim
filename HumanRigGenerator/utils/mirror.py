# utils/mirror.py
from .naming import get_opposite_side_name

def mirror_bone(arm_data, left_bone_name):
    """Mirrors a left bone (.L) to create or update its right counterpart (.R) in EDIT mode."""
    left_bone = arm_data.edit_bones.get(left_bone_name)
    if not left_bone:
        return None
        
    right_name = get_opposite_side_name(left_bone_name)
    right_bone = arm_data.edit_bones.get(right_name)
    if not right_bone:
        right_bone = arm_data.edit_bones.new(right_name)
        
    # Copy and mirror positions
    right_bone.head = left_bone.head.copy()
    right_bone.head.x = -left_bone.head.x
    
    right_bone.tail = left_bone.tail.copy()
    right_bone.tail.x = -left_bone.tail.x
    
    # Mirror roll: standard Blender behavior for mirroring roll is -left_bone.roll
    right_bone.roll = -left_bone.roll
    right_bone.use_deform = left_bone.use_deform
    right_bone.bbone_segments = left_bone.bbone_segments
    right_bone.bbone_easein = left_bone.bbone_easein
    right_bone.bbone_easeout = left_bone.bbone_easeout
    
    # Handle parenting
    if left_bone.parent:
        left_parent_name = left_bone.parent.name
        right_parent_name = get_opposite_side_name(left_parent_name)
        
        right_parent = arm_data.edit_bones.get(right_parent_name)
        if right_parent:
            right_bone.parent = right_parent
            right_bone.use_connect = left_bone.use_connect
        else:
            # Parent to the same central bone
            right_bone.parent = left_bone.parent
            right_bone.use_connect = left_bone.use_connect
            
    return right_bone
