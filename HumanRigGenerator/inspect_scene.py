import bpy
import mathutils

def main():
    print("=== INSPECTING BLENDER SCENE ===")
    
    # 1. Objects in the scene
    print("\n--- SCENE OBJECTS ---")
    for obj in bpy.data.objects:
        print(f"Object: {obj.name}, Type: {obj.type}, Scale: {list(obj.scale)}, Location: {list(obj.location)}")
        
    # 2. Inspect CC_Base_Body and Rig
    mesh_obj = bpy.data.objects.get("CC_Base_Body")
    rig_obj = bpy.data.objects.get("CC_Base_Body_Rig")
    
    if mesh_obj:
        print(f"\n--- MESH: {mesh_obj.name} ---")
        print(f"Matrix World:\n{mesh_obj.matrix_world}")
        print(f"Vertex Count: {len(mesh_obj.data.vertices)}")
        if len(mesh_obj.data.vertices) > 0:
            first_v = mesh_obj.data.vertices[0]
            print(f"First Vertex Local: {list(first_v.co)}")
            print(f"First Vertex World: {list(mesh_obj.matrix_world @ first_v.co)}")
            
    if rig_obj:
        print(f"\n--- RIG: {rig_obj.name} ---")
        print(f"Matrix World:\n{rig_obj.matrix_world}")
        
        # Print first few bones
        print("\n--- DEF BONES ---")
        for b in rig_obj.data.bones:
            if b.name.startswith("DEF-"):
                head_w = rig_obj.matrix_world @ b.head
                tail_w = rig_obj.matrix_world @ b.tail
                print(f"Bone: {b.name}, Head Local: {list(b.head)}, Head World: {list(head_w)}, Use Deform: {b.use_deform}")
                
    # 3. Print marker names and world positions
    print("\n--- MARKERS ---")
    for obj in bpy.data.objects:
        if "Mkr_" in obj.name:
            print(f"Marker: {obj.name}, Location: {list(obj.location)}")

if __name__ == "__main__":
    main()
