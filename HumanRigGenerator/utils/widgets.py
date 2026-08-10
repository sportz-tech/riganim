# utils/widgets.py
import bpy
import math

def get_wgts_collection():
    """Retrieves or creates a hidden collection for widgets."""
    coll_name = "WGTS_HumanRig"
    coll = bpy.data.collections.get(coll_name)
    if not coll:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)
        # Hide the collection
        # Note: In Blender, we can hide the collection from viewport visibility
        # but keep it active for bone shapes.
        # We can set hide_viewport = True on the layer_collection.
        for layer_coll in bpy.context.view_layer.layer_collection.children:
            if layer_coll.name == coll_name:
                layer_coll.hide_viewport = True
                break
    return coll

def create_mesh_object(name, verts, edges, faces):
    """Creates a mesh object with the given geometry."""
    # Check if object already exists
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
        
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    
    obj = bpy.data.objects.new(name, mesh)
    
    # Link to widgets collection
    coll = get_wgts_collection()
    coll.objects.link(obj)
    
    # Hide the object directly so it doesn't show up in rendering
    obj.hide_render = True
    obj.hide_set(True) # Hide in viewport
    
    return obj

def get_circle_widget(name="Wgt_Circle", radius=0.5, axis='Z'):
    verts = []
    edges = []
    num_segments = 16
    for i in range(num_segments):
        angle = (2 * math.pi * i) / num_segments
        c, s = math.cos(angle) * radius, math.sin(angle) * radius
        if axis == 'Z':
            verts.append((c, s, 0.0))
        elif axis == 'Y':
            verts.append((c, 0.0, s))
        else: # X
            verts.append((0.0, c, s))
            
        edges.append((i, (i + 1) % num_segments))
        
    return create_mesh_object(name, verts, edges, [])

def get_cube_widget(name="Wgt_Cube", size=0.5):
    s = size / 2.0
    verts = [
        (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
        (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0), # Bottom
        (4, 5), (5, 6), (6, 7), (7, 4), # Top
        (0, 4), (1, 5), (2, 6), (3, 7)  # Pillars
    ]
    return create_mesh_object(name, verts, edges, [])

def get_sphere_widget(name="Wgt_Sphere", radius=0.5):
    # Simpler wireframe sphere (3 perpendicular circles)
    verts = []
    edges = []
    num_segments = 12
    
    # Circle in XY plane
    for i in range(num_segments):
        angle = (2 * math.pi * i) / num_segments
        verts.append((math.cos(angle) * radius, math.sin(angle) * radius, 0.0))
        edges.append((i, (i + 1) % num_segments))
        
    # Circle in XZ plane
    start_idx = len(verts)
    for i in range(num_segments):
        angle = (2 * math.pi * i) / num_segments
        verts.append((math.cos(angle) * radius, 0.0, math.sin(angle) * radius))
        edges.append((start_idx + i, start_idx + (i + 1) % num_segments))
        
    # Circle in YZ plane
    start_idx = len(verts)
    for i in range(num_segments):
        angle = (2 * math.pi * i) / num_segments
        verts.append((0.0, math.cos(angle) * radius, math.sin(angle) * radius))
        edges.append((start_idx + i, start_idx + (i + 1) % num_segments))
        
    return create_mesh_object(name, verts, edges, [])

def get_arrow_widget(name="Wgt_Arrow", size=0.5):
    s = size
    # An arrow pointing along +Y axis (forward)
    verts = [
        (0.0, s, 0.0),            # Tip (0)
        (-s*0.4, s*0.4, 0.0),    # Left barb (1)
        (s*0.4, s*0.4, 0.0),     # Right barb (2)
        (-s*0.15, s*0.4, 0.0),   # Left inner (3)
        (s*0.15, s*0.4, 0.0),    # Right inner (4)
        (-s*0.15, -s*0.5, 0.0),  # Left base (5)
        (s*0.15, -s*0.5, 0.0)    # Right base (6)
    ]
    edges = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (3, 5), (4, 6), (5, 6)
    ]
    return create_mesh_object(name, verts, edges, [])

def get_root_widget(name="Wgt_Root", size=1.5):
    # A root widget is usually a double circular arrow or cross hair
    # Let's make a cross with a circle
    s = size
    verts = []
    edges = []
    
    # Draw circle
    num_segments = 16
    for i in range(num_segments):
        angle = (2 * math.pi * i) / num_segments
        verts.append((math.cos(angle) * s, math.sin(angle) * s, 0.0))
        edges.append((i, (i + 1) % num_segments))
        
    # Draw crosshair extensions
    start = len(verts)
    verts.extend([
        (-s*1.3, 0.0, 0.0), (s*1.3, 0.0, 0.0),
        (0.0, -s*1.3, 0.0), (0.0, s*1.3, 0.0)
    ])
    edges.extend([
        (start, start+1),
        (start+2, start+3)
    ])
    
    return create_mesh_object(name, verts, edges, [])
