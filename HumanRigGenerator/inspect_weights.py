import bpy

def main():
    print("=== INSPECTING WEIGHTS ===")
    mesh_obj = bpy.data.objects.get("CC_Base_Body")
    if not mesh_obj:
        print("Mesh CC_Base_Body not found!")
        return
        
    print(f"Mesh: {mesh_obj.name}")
    print(f"Vertex Groups count: {len(mesh_obj.vertex_groups)}")
    
    # Count how many vertices have weight in each group
    group_counts = {}
    for vg in mesh_obj.vertex_groups:
        group_counts[vg.name] = 0
        
    for v in mesh_obj.data.vertices:
        for g in v.groups:
            # find group name
            group_name = mesh_obj.vertex_groups[g.group].name
            if g.weight > 0.0:
                group_counts[group_name] += 1
                
    for name, count in sorted(group_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"Group: {name}, Vertices with weight > 0: {count}")

if __name__ == "__main__":
    main()
