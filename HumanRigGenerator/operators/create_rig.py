# operators/create_rig.py
import bpy
from .generate_spine import generate_spine_bones
from .generate_arms import generate_arm_bones
from .generate_hands import generate_hand_bones
from .generate_legs import generate_leg_bones
from .generate_feet import generate_foot_mechanism_bones
from .generate_face import generate_face_bones
from .generate_fk import generate_fk_controls
from .generate_ik import generate_ik_bones_edit, generate_ik_constraints_pose
from .controllers import generate_body_controllers_edit, setup_controllers_pose
from .constraints import setup_all_constraints
from .generate_animal import generate_animal_bones
from .generate_bird import generate_bird_bones

class OBJECT_OT_generate_human_rig(bpy.types.Operator):
    """Generates a complete modular human character rig."""
    bl_idname = "object.generate_human_rig"
    bl_label = "Generate Human Rig"
    bl_options = {'REGISTER', 'UNDO'}
    
    gender: bpy.props.EnumProperty( # type: ignore
        name="Proportions Preset",
        description="Select the default human proportion skeleton template",
        items=[
            ('MALE', "Male (Realistic Height ~1.8m)", "Generate a male proportion rig"),
            ('FEMALE', "Female (Realistic Height ~1.65m)", "Generate a female proportion rig")
        ],
        default='MALE'
    )
    
    def execute(self, context):
        # 0. Capture the character mesh object in the scene robustly
        from ..utils.bones import find_character_mesh
        active_mesh = find_character_mesh(context)

        # 1. Create a fresh Armature object
        rig_type = context.scene.hrg_rig_type
        if active_mesh:
            rig_name = f"{active_mesh.name}_Rig"
        else:
            rig_name = f"{rig_type.capitalize()}_Rig"
        
        existing_obj = bpy.data.objects.get(rig_name)
        if existing_obj:
            existing_data = existing_obj.data
            bpy.data.objects.remove(existing_obj, do_unlink=True)
            if existing_data:
                bpy.data.armatures.remove(existing_data)
            
        arm_data = bpy.data.armatures.new(f"{rig_name}_Data")
        obj = bpy.data.objects.new(rig_name, arm_data)
        context.scene.collection.objects.link(obj)
        
        # Set active and select it
        context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Armature display properties
        obj.show_in_front = True
        arm_data.show_bone_custom_shapes = True
        arm_data.display_type = 'WIRE'
        
        # Retrieve computed landmark/marker coordinates dynamically
        from ..utils.bones import get_all_marker_positions
        marker_positions = get_all_marker_positions(context, rig_type, gender=self.gender, mesh_obj=active_mesh)
        
        # 2. Go to EDIT Mode to build the bones framework
        bpy.ops.object.mode_set(mode='EDIT')
        
        try:
            # Build skeleton based on rig type
            if rig_type == 'ANIMAL':
                generate_animal_bones(arm_data, marker_positions=marker_positions)
            elif rig_type == 'BIRD':
                generate_bird_bones(arm_data, marker_positions=marker_positions)
            else: # HUMAN
                generate_spine_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
                generate_arm_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
                generate_hand_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
                generate_leg_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
                generate_foot_mechanism_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
                generate_face_bones(arm_data, gender=self.gender, marker_positions=marker_positions)
            
            # Generate controllers (common to all)
            generate_body_controllers_edit(arm_data, gender=self.gender)
            generate_fk_controls(arm_data)
            generate_ik_bones_edit(arm_data, rig_type=rig_type, marker_positions=marker_positions)
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate bones: {str(e)}")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}
            
        # 3. Go to POSE Mode to apply constraints and widgets
        bpy.ops.object.mode_set(mode='POSE')
        
        # Apply the queued bone collection assignments now that we are in Pose Mode
        from ..utils.bones import apply_queued_collections
        apply_queued_collections(arm_data)
        
        try:
            # Setup IK constraints
            generate_ik_constraints_pose(obj, rig_type=rig_type)
            # Setup IK/FK blending and deform mapping constraints
            setup_all_constraints(obj, rig_type=rig_type)
            # Setup custom widget shapes and bone groups
            setup_controllers_pose(obj)
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to setup constraints/controllers: {str(e)}")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}
            
        # Auto-skin if a mesh is found in the scene
        if active_mesh:
            try:
                # Select the mesh and make it active so auto-skin finds it
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                active_mesh.select_set(True)
                obj.select_set(True) # Select the newly generated rig
                context.view_layer.objects.active = active_mesh
                context.view_layer.update()
                
                bpy.ops.object.auto_skin_mesh()
            except Exception as e_skin:
                self.report({'WARNING'}, f"Rig generated, but auto-skinning failed: {str(e_skin)}")

        # Finish and keep in Pose Mode so user can immediately animate!
        self.report({'INFO'}, f"Successfully generated {rig_type.capitalize()} Rig!")
        return {'FINISHED'}
