# test_rig_generator.py
import sys
import os
import bpy
import mathutils

addon_dir = os.path.dirname(os.path.realpath(__file__))
print(f"Addon directory: {addon_dir}")
sys.path.insert(0, addon_dir)

# Clear sys.modules of any previous imports to ensure we load the local code
for m in list(sys.modules.keys()):
    if m.startswith("HumanRigGenerator") or m.startswith("MotionCaptureTransfer"):
        del sys.modules[m]

try:
    import HumanRigGenerator
    print("Addon imported successfully!")
    try:
        HumanRigGenerator.register()
        print("Addon registered successfully!")
    except Exception as e:
        print(f"Addon already registered or register skipped: {e}")
    
    # 1. Test Spawning Markers
    # Clear default startup objects (like the default Cube) to ensure clean marker names
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    print("Testing object.spawn_markers...")
    bpy.ops.object.spawn_markers()
    
    # Verify markers exist
    mkr = bpy.data.objects.get("Mkr_wrist.L")
    if not mkr:
        print("ERROR: Markers were not spawned successfully.")
        sys.exit(1)
    print("Markers spawned successfully!")
    
    # 2. Test shifting a marker to verify dynamic rig alignment
    print("Shifting wrist marker for test...")
    original_mkr_pos = mkr.location.copy()
    mkr.location.x += 0.15 # Shift wrist outward
    
    # Test Mirror Markers
    print("Testing object.mirror_markers...")
    bpy.ops.object.mirror_markers()
    r_mkr = bpy.data.objects.get("Mkr_wrist.R")
    if r_mkr and abs(r_mkr.location.x - (-mkr.location.x)) > 0.0001:
        print("ERROR: Mirroring markers did not synchronize Right side coordinate.")
        sys.exit(1)
    print("Mirror markers function successfully validated!")
    
    # 3. Generate rig from these custom markers
    print("Running rig generator with custom marker coordinates...")
    bpy.ops.object.generate_human_rig(gender='MALE')
    
    # Verify rig object exists
    rig = bpy.data.objects.get("Human_Rig")
    if not rig:
        print("ERROR: Rig was not created successfully.")
        sys.exit(1)
        
    print(f"Rig created successfully: {rig.name}")
    print(f"Total bones generated: {len(rig.data.bones)}")
    
    # Verify wrist bone head is shifted outward matching the marker
    bpy.ops.object.mode_set(mode='EDIT')
    wrist_bone = rig.data.edit_bones.get("ORG-hand.L")
    if wrist_bone:
        print(f"Wrist bone head location: {wrist_bone.head}")
        # It should match the shifted marker position (wrist head = wrist marker)
        if abs(wrist_bone.head.x - mkr.location.x) > 0.001:
            print(f"ERROR: Rig hand did not align to wrist marker location: bone={wrist_bone.head.x}, marker={mkr.location.x}")
            sys.exit(1)
        print("Verified rig dynamically aligned to marker positions successfully!")
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 3b. Test Bendy Bones Generation
    print("Testing Bendy Bones Rig Generation...")
    # Enable B-Bones
    bpy.context.scene.hrg_use_bbone_legs = True
    bpy.context.scene.hrg_bbone_segments_legs = 8
    bpy.context.scene.hrg_use_bbone_arms = True
    bpy.context.scene.hrg_bbone_segments_arms = 6
    bpy.context.scene.hrg_use_bbone_spine = True
    bpy.context.scene.hrg_bbone_segments_spine = 7
    
    # Delete the standard rig first
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects.remove(rig, do_unlink=True)
    
    # Re-generate with B-Bones enabled
    print("Re-generating rig with Bendy Bones enabled...")
    bpy.ops.object.generate_human_rig(gender='MALE')
    
    # Verify the new rig
    rig = bpy.data.objects.get("Human_Rig")
    if not rig:
        print("ERROR: Rig with Bendy Bones was not created successfully.")
        sys.exit(1)
        
    # Check segment count on deform bones in EDIT mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Legs (thigh.L, shin.L, thigh.R, shin.R should have 8 segments and ease settings)
    for bname in ["DEF-thigh.L", "DEF-thigh.R"]:
        bone = rig.data.edit_bones.get(bname)
        if not bone:
            print(f"ERROR: Leg deform bone {bname} not found.")
            sys.exit(1)
        if bone.bbone_segments != 8:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 8.")
            sys.exit(1)
        if abs(bone.bbone_easein - 1.0) > 0.001 or abs(bone.bbone_easeout - 0.0) > 0.001:
            print(f"ERROR: Bone {bname} has easein={bone.bbone_easein}, easeout={bone.bbone_easeout}, expected 1.0, 0.0.")
            sys.exit(1)
            
    for bname in ["DEF-shin.L", "DEF-shin.R"]:
        bone = rig.data.edit_bones.get(bname)
        if not bone:
            print(f"ERROR: Leg deform bone {bname} not found.")
            sys.exit(1)
        if bone.bbone_segments != 8:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 8.")
            sys.exit(1)
        if abs(bone.bbone_easein - 0.0) > 0.001 or abs(bone.bbone_easeout - 1.0) > 0.001:
            print(f"ERROR: Bone {bname} has easein={bone.bbone_easein}, easeout={bone.bbone_easeout}, expected 0.0, 1.0.")
            sys.exit(1)
            
    # Arms (upper_arm.L, forearm.L, upper_arm.R, forearm.R should have 6 segments and ease settings)
    for bname in ["DEF-upper_arm.L", "DEF-upper_arm.R"]:
        bone = rig.data.edit_bones.get(bname)
        if not bone:
            print(f"ERROR: Arm deform bone {bname} not found.")
            sys.exit(1)
        if bone.bbone_segments != 6:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 6.")
            sys.exit(1)
        if abs(bone.bbone_easein - 1.0) > 0.001 or abs(bone.bbone_easeout - 0.0) > 0.001:
            print(f"ERROR: Bone {bname} has easein={bone.bbone_easein}, easeout={bone.bbone_easeout}, expected 1.0, 0.0.")
            sys.exit(1)
            
    for bname in ["DEF-forearm.L", "DEF-forearm.R"]:
        bone = rig.data.edit_bones.get(bname)
        if not bone:
            print(f"ERROR: Arm deform bone {bname} not found.")
            sys.exit(1)
        if bone.bbone_segments != 6:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 6.")
            sys.exit(1)
        if abs(bone.bbone_easein - 0.0) > 0.001 or abs(bone.bbone_easeout - 1.0) > 0.001:
            print(f"ERROR: Bone {bname} has easein={bone.bbone_easein}, easeout={bone.bbone_easeout}, expected 0.0, 1.0.")
            sys.exit(1)
            
    # Spine (spine, spine.001, spine.002, spine.003, neck should have 7 segments and 0 ease settings)
    for bname in ["DEF-spine", "DEF-spine.001", "DEF-spine.002", "DEF-spine.003", "DEF-neck"]:
        bone = rig.data.edit_bones.get(bname)
        if not bone:
            print(f"ERROR: Spine deform bone {bname} not found.")
            sys.exit(1)
        if bone.bbone_segments != 7:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 7.")
            sys.exit(1)
        if abs(bone.bbone_easein - 0.0) > 0.001 or abs(bone.bbone_easeout - 0.0) > 0.001:
            print(f"ERROR: Bone {bname} has easein={bone.bbone_easein}, easeout={bone.bbone_easeout}, expected 0.0, 0.0.")
            sys.exit(1)
            
    # Verify other bones have 1 segment (e.g. DEF-head, DEF-pelvis, DEF-hand.L)
    for bname in ["DEF-head", "DEF-pelvis", "DEF-hand.L"]:
        bone = rig.data.edit_bones.get(bname)
        if bone and bone.bbone_segments != 1:
            print(f"ERROR: Bone {bname} has {bone.bbone_segments} segments, expected 1.")
            sys.exit(1)
            
    # Verify display type is WIRE
    if rig.data.display_type != 'WIRE':
        print(f"ERROR: Armature display type is {rig.data.display_type}, expected WIRE.")
        sys.exit(1)
        
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Bendy Bones rig generation successfully verified!")
    
    # Disable B-Bones for the remaining tests
    bpy.context.scene.hrg_use_bbone_legs = False
    bpy.context.scene.hrg_use_bbone_arms = False
    bpy.context.scene.hrg_use_bbone_spine = False
    
    # 4. Test Animation Presets (Sequencing)
    # Active object must be the rig
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    
    print("Testing object.apply_animation_preset (Walk, Start Frame 1)...")
    bpy.ops.object.apply_animation_preset(preset_name='WALK', start_frame=1, clear_existing=True)
    
    print("Testing object.apply_animation_preset (Run, Start Frame 25)...")
    bpy.ops.object.apply_animation_preset(preset_name='RUN', start_frame=25, clear_existing=False)
    
    # Verify animation action was created and contains keyframes
    action = rig.animation_data.action
    if action:
        print(f"Verified action '{action.name}' created!")
    else:
        print("ERROR: Action was not generated.")
        sys.exit(1)
        
    # 5. Test NLA Track Mixer
    print("Testing object.push_to_nla...")
    bpy.ops.object.push_to_nla()
    if rig.animation_data.action is not None:
        print("ERROR: Action was not cleared from active track after push to NLA.")
        sys.exit(1)
    if len(rig.animation_data.nla_tracks) == 0:
        print("ERROR: No NLA tracks generated.")
        sys.exit(1)
    print("NLA track mixer successfully validated!")
    
    # 6. Test Path Walker Sync
    # Create test Curve path object
    print("Creating test Curve object...")
    curve_data = bpy.data.curves.new('TestCurveData', type='CURVE')
    curve_data.dimensions = '3D'
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(1) # Bezier points
    curve_obj = bpy.data.objects.new('TestCurve', curve_data)
    bpy.context.scene.collection.objects.link(curve_obj)
    
    # Assign via PointerProperty
    bpy.context.scene.hrg_path_curve_obj = curve_obj
    
    print("Testing object.bind_rig_to_path...")
    # Apply a preset first to ensure action exists
    bpy.ops.object.apply_animation_preset(preset_name='WALK', start_frame=1, clear_existing=True)
    bpy.ops.object.bind_rig_to_path(duration=120)
    
    pb_root = rig.pose.bones.get("CTRL-root")
    c_follow = pb_root.constraints.get("Follow_Path")
    if not c_follow or c_follow.target != curve_obj:
        print("ERROR: Follow path constraint was not set up correctly.")
        sys.exit(1)
    print("Path walker sync successfully validated!")
    
    # 7. Test Talking Animation Preset
    print("Testing object.apply_animation_preset (Talk, Start Frame 1)...")
    bpy.ops.object.apply_animation_preset(preset_name='TALK', start_frame=1, clear_existing=True)
    
    action = rig.animation_data.action
    if not action:
        print("ERROR: Talking action was not generated.")
        sys.exit(1)
    print("Talking preset animation successfully validated!")
    
    # 8. Test Scene Camera Setup & Tracking
    print("Testing object.setup_scene_camera...")
    bpy.context.scene.hrg_cam_shot = 'CLOSEUP'
    bpy.context.scene.hrg_cam_angle = 'FRONT'
    bpy.ops.object.setup_scene_camera()
    
    camera = bpy.data.objects.get("Rig_Camera")
    target = bpy.data.objects.get(f"Cam_Target_{rig.name}")
    if not camera or not target:
        print("ERROR: Camera or target empty was not spawned successfully.")
        sys.exit(1)
        
    # Check parent and tracking constraints
    if target.parent != rig or target.parent_bone != "CTRL-head":
        print("ERROR: Camera target empty is not parented to the rig's CTRL-head bone.")
        sys.exit(1)
        
    c_track = camera.constraints.get("Track_To")
    if not c_track or c_track.target != target:
        print("ERROR: Camera tracking constraint was not set up correctly.")
        sys.exit(1)
    print("Camera controller setup & tracking successfully validated!")
    
    # 9. Test Animal (Quadruped) Rig Generation
    print("Testing Animal (Quadruped) Rig...")
    bpy.context.scene.hrg_rig_type = 'ANIMAL'
    print("Spawning animal markers...")
    bpy.ops.object.spawn_markers()
    
    animal_mkr = bpy.data.objects.get("Mkr_tail_tip")
    if not animal_mkr:
        print("ERROR: Tail marker was not spawned for Animal.")
        sys.exit(1)
        
    print("Generating Animal Rig...")
    bpy.ops.object.generate_human_rig()
    
    animal_rig = bpy.data.objects.get("Animal_Rig")
    if not animal_rig:
        print("ERROR: Animal_Rig armature not created.")
        sys.exit(1)
        
    # Verify tail bones exist in EDIT mode
    bpy.ops.object.mode_set(mode='EDIT')
    if not animal_rig.data.edit_bones.get("ORG-tail.001"):
        print("ERROR: Animal tail bone ORG-tail.001 not generated.")
        sys.exit(1)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Animal (Quadruped) Rig successfully validated!")
    
    # 10. Test Bird (Avian) Rig Generation
    print("Testing Bird (Avian) Rig...")
    bpy.context.scene.hrg_rig_type = 'BIRD'
    print("Spawning bird markers...")
    bpy.ops.object.spawn_markers()
    
    bird_mkr = bpy.data.objects.get("Mkr_shoulder.L") # shoulder serves as wing base
    if not bird_mkr:
        print("ERROR: Wing base shoulder marker was not spawned for Bird.")
        sys.exit(1)
        
    print("Generating Bird Rig...")
    bpy.ops.object.generate_human_rig()
    
    bird_rig = bpy.data.objects.get("Bird_Rig")
    if not bird_rig:
        print("ERROR: Bird_Rig armature not created.")
        sys.exit(1)
        
    # Verify wing bones exist in EDIT mode
    bpy.ops.object.mode_set(mode='EDIT')
    if not bird_rig.data.edit_bones.get("ORG-upper_arm.L"): # wing shoulder
        print("ERROR: Bird wing bone ORG-upper_arm.L not generated.")
        sys.exit(1)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Bird (Avian) Rig successfully validated!")
    
    # 11. Test Actor Selection Manager
    print("Testing Actor Manager switching...")
    bpy.context.scene.hrg_active_actor = "Human_Rig"
    if bpy.context.view_layer.objects.active != rig:
        print("ERROR: Actor manager did not select active Human_Rig.")
        sys.exit(1)
    print("Actor Manager successfully validated!")
    
    # 12. Test Auto Mesh-Aware Marker Placement
    print("Testing Auto Mesh-Aware Marker Placement...")
    # Add a cylinder mesh of height 3.0 meters (Z bounds: 0.0 to 3.0)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=3.0, location=(0, 0, 1.5))
    cylinder_mesh = bpy.context.active_object
    
    bpy.context.scene.hrg_rig_type = 'HUMAN'
    print("Spawning markers with cylinder active (height = 3.0m)...")
    bpy.ops.object.spawn_markers()
    
    mkr_head = bpy.data.objects.get(f"{cylinder_mesh.name}_Mkr_head")
    if not mkr_head:
        print("ERROR: Head marker not found after mesh-aware spawn.")
        sys.exit(1)
        
    print(f"Mesh-aware Head Marker location Z: {mkr_head.location.z}")
    # Head marker base height is 1.88. Scaled by 3.0/1.88 should yield exactly 3.0!
    if abs(mkr_head.location.z - 3.0) > 0.001:
        print(f"ERROR: Mesh-aware marker Z position not scaled correctly: {mkr_head.location.z}")
        sys.exit(1)
    print("Auto Mesh-Aware Marker Placement successfully validated!")
    
    # 13. Test Auto-Skin Weight Painting
    print("Testing Auto-Skin Weight Painting...")
    # Select the cylinder mesh
    bpy.ops.object.select_all(action='DESELECT')
    cylinder_mesh.select_set(True)
    bpy.context.view_layer.objects.active = cylinder_mesh
    
    # Run auto-skin
    print("Running auto-skin parent...")
    bpy.ops.object.auto_skin_mesh()
    
    # Check if cylinder mesh has an Armature modifier pointing to Human_Rig
    mod_arm = None
    for m in cylinder_mesh.modifiers:
        if m.type == 'ARMATURE':
            mod_arm = m
            break
            
    if not mod_arm or mod_arm.object != rig:
        print("ERROR: Armature modifier was not applied to the mesh by Auto-Skin.")
        sys.exit(1)
    print("Auto-Skin Weight Painting successfully validated!")
    
    # Test Clear Animation
    print("Testing object.clear_rig_animation...")
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.clear_rig_animation()
    if rig.animation_data and rig.animation_data.action:
        print("ERROR: Clear animation did not strip the action from the rig.")
        sys.exit(1)
    print("Verified clear animation resets the pose successfully!")
    
    print("All tests passed successfully!")
    
except Exception as e:
    print(f"Test failed with error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        HumanRigGenerator.unregister()
        print("Addon unregistered successfully!")
    except:
        pass
