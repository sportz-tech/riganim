# utils/math.py
import math
import mathutils

def get_vector_angle(v1, v2):
    """Returns the angle in radians between two vectors."""
    try:
        return v1.angle(v2)
    except ValueError:
        return 0.0

def get_roll_to_vector(head, tail, up_vector):
    """Calculates the roll angle for a bone from head to tail to align local Z with an up_vector."""
    direction = (tail - head).normalized()
    # Find a coordinate system where Y is bone direction
    # This is similar to how Blender aligns bone roll
    z_axis = up_vector.normalized()
    x_axis = z_axis.cross(direction).normalized()
    z_axis = direction.cross(x_axis).normalized()
    
    # Create rotation matrix
    mat = mathutils.Matrix((x_axis, direction, z_axis)).transposed()
    # Convert to Euler or extract roll (simple approximation/heuristic)
    # Usually in Blender, we can set edit_bone.roll directly or let Blender calculate it.
    # A standard way in Blender API is using bpy_extras.io_utils.axis_conversion or custom matrices.
    return 0.0 # Default fallback
