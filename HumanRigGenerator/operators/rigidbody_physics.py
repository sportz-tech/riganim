# operators/rigidbody_physics.py
import bpy
import math
import mathutils
from ..utils.naming import get_deform_name

# Define the simulated bones, their collision shapes, and default properties
PHYSICS_BONES = [
    # Core Torso
    ("pelvis", "BOX", {"mass": 10.0, "thickness": 0.25}),
    ("spine", "BOX", {"mass": 8.0, "thickness": 0.22}),
    ("spine.001", "BOX", {"mass": 8.0, "thickness": 0.22}),
    ("spine.002", "BOX", {"mass": 8.0, "thickness": 0.22}),
    ("spine.003", "BOX", {"mass": 8.0, "thickness": 0.22}),
    ("head", "SPHERE", {"mass": 5.0, "thickness": 0.18}),
    
    # Left Arm
    ("upper_arm.L", "CYLINDER", {"mass": 3.0, "thickness": 0.10}),
    ("forearm.L", "CYLINDER", {"mass": 2.0, "thickness": 0.08}),
    ("hand.L", "BOX", {"mass": 1.0, "thickness": 0.06}),
    
    # Right Arm
    ("upper_arm.R", "CYLINDER", {"mass": 3.0, "thickness": 0.10}),
    ("forearm.R", "CYLINDER", {"mass": 2.0, "thickness": 0.08}),
    ("hand.R", "BOX", {"mass": 1.0, "thickness": 0.06}),
    
    # Left Leg
    ("thigh.L", "CYLINDER", {"mass": 6.0, "thickness": 0.14}),
    ("shin.L", "CYLINDER", {"mass": 4.0, "thickness": 0.11}),
    ("foot.L", "BOX", {"mass": 1.5, "thickness": 0.08}),
    
    # Right Leg
    ("thigh.R", "CYLINDER", {"mass": 6.0, "thickness": 0.14}),
    ("shin.R", "CYLINDER", {"mass": 4.0, "thickness": 0.11}),
    ("foot.R", "BOX", {"mass": 1.5, "thickness": 0.08}),
]

# Joint angular limits in radians (x_min, x_max, y_min, y_max, z_min, z_max)
JOINT_LIMITS = {
    # Knees (Hinge-like: flex on local X axis, lock Y and Z)
    "shin.L": (0.0, 2.2, -0.05, 0.05, -0.05, 0.05),
    "shin.R": (0.0, 2.2, -0.05, 0.05, -0.05, 0.05),
    
    # Elbows (Hinge-like: flex on local X axis, lock Y and Z)
    "forearm.L": (0.0, 2.4, -0.05, 0.05, -0.05, 0.05),
    "forearm.R": (0.0, 2.4, -0.05, 0.05, -0.05, 0.05),
    
    # Hips (Ball-and-Socket: wide rotation)
    "thigh.L": (-0.7, 1.5, -0.5, 0.5, -0.7, 0.7),
    "thigh.R": (-0.7, 1.5, -0.5, 0.5, -0.7, 0.7),
    
    # Shoulders (Ball-and-Socket: wide rotation)
    "upper_arm.L": (-1.2, 1.2, -0.8, 0.8, -1.2, 1.2),
    "upper_arm.R": (-1.2, 1.2, -0.8, 0.8, -1.2, 1.2),
    
    # Spine segments (Tight constraints for stability)
    "spine": (-0.15, 0.15, -0.15, 0.15, -0.15, 0.15),
    "spine.001": (-0.15, 0.15, -0.15, 0.15, -0.15, 0.15),
    "spine.002": (-0.15, 0.15, -0.15, 0.15, -0.15, 0.15),
    "spine.003": (-0.15, 0.15, -0.15, 0.15, -0.15, 0.15),
    
    # Head (Moderate rotation)
    "head": (-0.6, 0.6, -0.6, 0.6, -0.6, 0.6),
}

def create_box_mesh(name, thickness, length):
    """Creates a basic box mesh aligned with the local Y axis."""
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    
    hx = thickness / 2.0
    hy = length / 2.0
    hz = thickness / 2.0
    
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)
    ]
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return obj

def create_cylinder_mesh(name, radius, length, segments=12):
    """Creates a basic cylinder mesh aligned with the local Y axis."""
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    
    verts = []
    faces = []
    hy = length / 2.0
    
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        verts.append((x, -hy, z))
        verts.append((x, hy, z))
        
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((i * 2, next_i * 2, next_i * 2 + 1, i * 2 + 1))
        
    bottom_cap = [i * 2 for i in range(segments)]
    bottom_cap.reverse()
    top_cap = [i * 2 + 1 for i in range(segments)]
    
    faces.append(bottom_cap)
    faces.append(top_cap)
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return obj

def create_sphere_mesh(name, radius, segments=12, rings=8):
    """Creates a basic UV sphere mesh."""
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    
    verts = []
    faces = []
    
    verts.append((0, 0, radius))
    for r in range(1, rings):
        theta = math.pi * r / rings
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        for s in range(segments):
            phi = 2 * math.pi * s / segments
            x = radius * sin_t * math.cos(phi)
            y = radius * sin_t * math.sin(phi)
            z = radius * cos_t
            verts.append((x, y, z))
    verts.append((0, 0, -radius))
    
    # Connect top cap
    for s in range(segments):
        faces.append((0, s + 1, ((s + 1) % segments) + 1))
        
    # Connect rings
    for r in range(rings - 2):
        row1 = 1 + r * segments
        row2 = 1 + (r + 1) * segments
        for s in range(segments):
            next_s = (s + 1) % segments
            faces.append((row1 + s, row1 + next_s, row2 + next_s, row2 + s))
            
    # Connect bottom cap
    last_vert = len(verts) - 1
    row_last = last_vert - segments
    for s in range(segments):
        next_s = (s + 1) % segments
        faces.append((last_vert, row_last + next_s, row_last + s))
        
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return obj

def find_physics_parent(pose_bone, physics_bone_names):
    """Recursively traces up the bone hierarchy to find the nearest ancestor bone that is simulated."""
    parent = pose_bone.parent
    while parent:
        base_name = parent.name.replace("DEF-", "")
        if base_name in physics_bone_names:
            return base_name
        parent = parent.parent
    return None

class OBJECT_OT_generate_rigidbody_physics(bpy.types.Operator):
    """Generates physical collision colliders and joints for the generated rig, allowing dynamic ragdoll physics."""
    bl_idname = "object.generate_rigidbody_physics"
    bl_label = "Generate Rigidbody Physics (Ragdoll)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'
        
    def execute(self, context):
        scene = context.scene
        arm_obj = context.active_object
        
        # 1. Ensure Rigid Body World exists in the scene
        if not scene.rigidbody_world:
            bpy.ops.rigidbody.world_add()
        world = scene.rigidbody_world
        
        # 2. Setup Dedicated Collections for Physics Colliders & Joints
        colliders_name = f"{arm_obj.name}_Physics_Colliders"
        constraints_name = f"{arm_obj.name}_Physics_Constraints"
        
        colliders_col = bpy.data.collections.get(colliders_name)
        if not colliders_col:
            colliders_col = bpy.data.collections.new(colliders_name)
            scene.collection.children.link(colliders_col)
            
        constraints_col = bpy.data.collections.get(constraints_name)
        if not constraints_col:
            constraints_col = bpy.data.collections.new(constraints_name)
            scene.collection.children.link(constraints_col)
            
        world.collection = colliders_col
        world.constraints = constraints_col
        
        # Dictionary to store created collider objects: { bone_base_name: object }
        colliders = {}
        physics_bone_names = {b[0] for b in PHYSICS_BONES}
        
        # Save selection state
        prev_active = context.view_layer.objects.active
        prev_selected = [o for o in context.selected_objects]
        
        # 3. Create Colliders
        for base_name, shape_type, props in PHYSICS_BONES:
            def_name = get_deform_name(base_name)
            pb = arm_obj.pose.bones.get(def_name)
            if not pb:
                continue # Skip if bone doesn't exist on this rig
                
            # Compute bone metrics in world space
            head_world = arm_obj.matrix_world @ pb.head
            tail_world = arm_obj.matrix_world @ pb.tail
            midpoint_world = (head_world + tail_world) / 2.0
            length_world = (tail_world - head_world).length
            if length_world < 0.001:
                length_world = 0.01
                
            rotation_world = (arm_obj.matrix_world @ pb.matrix).to_quaternion()
            thickness = props["thickness"]
            
            # Spawn collider mesh
            col_name = f"Phys_Col_{base_name}"
            # Check if it already exists, remove it first
            existing = bpy.data.objects.get(col_name)
            if existing:
                bpy.data.objects.remove(existing, do_unlink=True)
                
            if shape_type == "CYLINDER":
                col_obj = create_cylinder_mesh(col_name, radius=thickness/2.0, length=length_world)
            elif shape_type == "SPHERE":
                col_obj = create_sphere_mesh(col_name, radius=thickness/2.0)
            else: # BOX
                col_obj = create_box_mesh(col_name, thickness=thickness, length=length_world)
                
            # Align with bone
            col_obj.location = midpoint_world
            col_obj.rotation_mode = 'QUATERNION'
            col_obj.rotation_quaternion = rotation_world
            
            # Visual display properties (make it transparent / outline)
            col_obj.display_type = 'WIRE'
            col_obj.show_in_front = True
            
            # Link to collection
            colliders_col.objects.link(col_obj)
            colliders[base_name] = col_obj
            
            # Add Rigid Body Component
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = col_obj
            col_obj.select_set(True)
            bpy.ops.rigidbody.object_add(type='ACTIVE')
            
            # Configure Rigid Body Settings
            col_obj.rigid_body.mass = props["mass"]
            col_obj.rigid_body.collision_shape = shape_type
            col_obj.rigid_body.use_margin = True
            col_obj.rigid_body.collision_margin = 0.005
            col_obj.rigid_body.linear_damping = 0.15
            col_obj.rigid_body.angular_damping = 0.15
            
        # 4. Create Joint Constraints
        for base_name, shape_type, props in PHYSICS_BONES:
            def_name = get_deform_name(base_name)
            pb = arm_obj.pose.bones.get(def_name)
            if not pb:
                continue
                
            physics_parent_name = find_physics_parent(pb, physics_bone_names)
            if not physics_parent_name:
                continue # Hips/Pelvis usually doesn't have parent constraint
                
            parent_col = colliders.get(physics_parent_name)
            child_col = colliders.get(base_name)
            if not parent_col or not child_col:
                continue
                
            # Joint position is exactly at the child bone's head in world space
            joint_loc = arm_obj.matrix_world @ pb.head
            joint_rot = (arm_obj.matrix_world @ pb.matrix).to_quaternion()
            
            # Create Joint Empty
            joint_name = f"Phys_Joint_{base_name}"
            existing_joint = bpy.data.objects.get(joint_name)
            if existing_joint:
                bpy.data.objects.remove(existing_joint, do_unlink=True)
                
            joint_obj = bpy.data.objects.new(joint_name, None)
            joint_obj.empty_display_type = 'ARROWS'
            joint_obj.empty_display_size = 0.05
            joint_obj.location = joint_loc
            joint_obj.rotation_mode = 'QUATERNION'
            joint_obj.rotation_quaternion = joint_rot
            
            constraints_col.objects.link(joint_obj)
            
            # Add Rigid Body Joint Constraint
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = joint_obj
            joint_obj.select_set(True)
            bpy.ops.rigidbody.constraint_add()
            
            con = joint_obj.rigid_body_constraint
            con.type = 'GENERIC_6DOF'
            con.object1 = parent_col
            con.object2 = child_col
            con.disable_collisions = True # Disable collision between direct physics joints
            
            # Lock translation (must act as standard physical joint pivot)
            con.use_limit_lin_x = True
            con.use_limit_lin_y = True
            con.use_limit_lin_z = True
            con.limit_lin_x_lower = 0.0
            con.limit_lin_x_upper = 0.0
            con.limit_lin_y_lower = 0.0
            con.limit_lin_y_upper = 0.0
            con.limit_lin_z_lower = 0.0
            con.limit_lin_z_upper = 0.0
            
            # Set rotational limits from dictionary
            limits = JOINT_LIMITS.get(base_name, (-0.2, 0.2, -0.2, 0.2, -0.2, 0.2))
            con.use_limit_ang_x = True
            con.limit_ang_x_lower = limits[0]
            con.limit_ang_x_upper = limits[1]
            
            con.use_limit_ang_y = True
            con.limit_ang_y_lower = limits[2]
            con.limit_ang_y_upper = limits[3]
            
            con.use_limit_ang_z = True
            con.limit_ang_z_lower = limits[4]
            con.limit_ang_z_upper = limits[5]
            
        # 5. Link Armature Deform Bones to physics colliders via Copy Transforms Constraints
        # Switch armature to Pose mode
        context.view_layer.objects.active = arm_obj
        arm_obj.select_set(True)
        
        for base_name, _, _ in PHYSICS_BONES:
            def_name = get_deform_name(base_name)
            pb = arm_obj.pose.bones.get(def_name)
            col_obj = colliders.get(base_name)
            if not pb or not col_obj:
                continue
                
            # Add or find constraint
            con = pb.constraints.get("Physics_Ragdoll")
            if not con:
                con = pb.constraints.new('COPY_TRANSFORMS')
                con.name = "Physics_Ragdoll"
            con.target = col_obj
            con.target_space = 'WORLD'
            con.owner_space = 'WORLD'
            con.influence = 1.0 # Enable physics by default
            
        # Restore selection state
        bpy.ops.object.select_all(action='DESELECT')
        for o in prev_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        context.view_layer.objects.active = prev_active
        
        self.report({'INFO'}, "Successfully generated physics ragdoll colliders and joints!")
        return {'FINISHED'}

class OBJECT_OT_remove_rigidbody_physics(bpy.types.Operator):
    """Removes all generated physics colliders, joints, and bone constraints from the active rig."""
    bl_idname = "object.remove_rigidbody_physics"
    bl_label = "Remove Rigidbody Physics"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'
        
    def execute(self, context):
        arm_obj = context.active_object
        
        # 1. Remove Copy Transforms constraints from deform bones
        for pb in arm_obj.pose.bones:
            con = pb.constraints.get("Physics_Ragdoll")
            if con:
                pb.constraints.remove(con)
                
        # 2. Delete the collections and their objects
        colliders_name = f"{arm_obj.name}_Physics_Colliders"
        constraints_name = f"{arm_obj.name}_Physics_Constraints"
        
        for col_name in [colliders_name, constraints_name]:
            col = bpy.data.collections.get(col_name)
            if col:
                # Remove all objects inside the collection
                for o in list(col.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.collections.remove(col)
                
        self.report({'INFO'}, "Successfully removed physics ragdoll systems from this rig.")
        return {'FINISHED'}

class OBJECT_OT_toggle_rigidbody_influence(bpy.types.Operator):
    """Bridges keyframed animation and physics simulation by setting constraint influence (0 = Anim, 1 = Physics)."""
    bl_idname = "object.toggle_rigidbody_influence"
    bl_label = "Set Physics Influence"
    bl_options = {'REGISTER', 'UNDO'}
    
    influence: bpy.props.FloatProperty(
        name="Influence",
        description="Blend factor. 0.0 means full custom keyframed animation, 1.0 means full physical ragdoll simulation",
        min=0.0,
        max=1.0,
        default=1.0
    )
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'
        
    def execute(self, context):
        arm_obj = context.active_object
        count = 0
        for pb in arm_obj.pose.bones:
            con = pb.constraints.get("Physics_Ragdoll")
            if con:
                con.influence = self.influence
                count += 1
                
        # Update UI property if active on the scene
        context.scene.hrg_physics_influence = self.influence
        
        self.report({'INFO'}, f"Set physics influence to {self.influence:.2f} on {count} bones.")
        return {'FINISHED'}
