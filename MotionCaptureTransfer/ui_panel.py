# ui_panel.py
import bpy
from .dependency_installer import check_dependencies

class VIEW3D_PT_mocap_transfer_panel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar for Motion Capture Transfer."""
    bl_label = "RigAnim Mocap: AI Performance Capture"
    bl_idname = "VIEW3D_PT_mocap_transfer_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'RigAnim Studio' # Aligned under RigAnim Studio tab!
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object
        
        # 1. Dependency Check
        cv2_ok, mp_ok = check_dependencies()
        if not cv2_ok or not mp_ok:
            box = layout.box()
            box.alert = True
            box.label(text="Dependencies Missing!", icon='ERROR')
            
            col = box.column(align=True)
            if not cv2_ok:
                col.label(text="- OpenCV (opencv-python)")
            if not mp_ok:
                col.label(text="- MediaPipe (mediapipe)")
                
            col.separator()
            col.operator("mocap.install_dependencies", text="Install Dependencies (Pip)", icon='ADD')
            return # Block drawing the rest of panel until dependencies are ready!
            
        # 2. Active Actor Verification
        box_actor = layout.box()
        box_actor.label(text="Target Actor Setup", icon='OUTLINER_OB_ARMATURE')
        
        if obj and obj.type == 'ARMATURE':
            row = box_actor.row()
            row.label(text=f"Active: {obj.name}", icon='CHECKMARK')
        else:
            box_actor.alert = True
            box_actor.label(text="Please select an Armature!", icon='ERROR')
            return
            
        # 3. Source Selection & Controls
        box_source = layout.box()
        box_source.label(text="Mocap Source & Mode", icon='CAMERA_DATA')
        box_source.prop(scene, "hrg_mocap_source", expand=True)
        
        # Detection Mode Selector (Body, Face, Both)
        box_mode = box_source.box()
        box_mode.label(text="Detection Mode", icon='TRACKING')
        box_mode.prop(scene, "hrg_mocap_capture_mode", expand=True)
        if scene.hrg_mocap_capture_mode in ['FULL', 'BODY']:
            box_mode.prop(scene, "hrg_mocap_pose_complexity", text="Pose Model")
        box_mode.prop(scene, "hrg_mocap_capture_resolution", text="Resolution")
        
        # Mocap Running status indicator
        if scene.hrg_mocap_active:
            row_status = box_source.row()
            row_status.alert = True
            row_status.label(text="CAPTURE RUNNING (ESC to Stop)", icon='REC')
            if scene.hrg_mocap_backend_mode:
                row_fps = box_source.row()
                row_fps.label(text=f"Live Tracking Speed: {scene.hrg_mocap_streaming_fps:.1f} FPS", icon='FORWARD')
            
        if scene.hrg_mocap_source == 'WEBCAM':
            col_web = box_source.column(align=True)
            col_web.prop(scene, "hrg_mocap_backend_mode", text="Use External Backend (60 FPS)")
            if scene.hrg_mocap_backend_mode:
                col_web.prop(scene, "hrg_mocap_show_visualizer", text="Show Visualizer Window")
            col_web.prop(scene, "hrg_mocap_camera_index", text="Camera")
            col_web.prop(scene, "hrg_mocap_record", text="Record Keyframes Live")
            
            col_web.separator()
            if not scene.hrg_mocap_active:
                op_live = col_web.operator("mocap.live_capture", text="Start Live Mocap Stream", icon='PLAY')
            else:
                col_web.prop(scene, "hrg_mocap_active", text="Stop Mocap Stream", toggle=True, icon='CANCEL')
                
        else: # VIDEO_FILE
            col_vid = box_source.column(align=True)
            col_vid.prop(scene, "hrg_mocap_video_path", text="Video File")
            
            row_frames = col_vid.row(align=True)
            row_frames.prop(scene, "hrg_mocap_start_frame", text="Start")
            row_frames.prop(scene, "hrg_mocap_end_frame", text="End")
            
            col_vid.separator()
            if not scene.hrg_mocap_active:
                col_vid.operator("mocap.process_video_file", text="Process Video File", icon='PREVIEW_RANGE')
            else:
                col_vid.prop(scene, "hrg_mocap_active", text="Stop Processing", toggle=True, icon='CANCEL')
                
        # 4. Calibration & Settings
        box_settings = layout.box()
        box_settings.label(text="Mocap Parameters", icon='PREFERENCES')
        
        col_settings = box_settings.column(align=True)
        col_settings.prop(scene, "hrg_mocap_smoothing", text="Smoothing", slider=True)
        col_settings.prop(scene, "hrg_mocap_face_sensitivity", text="Face Multiplier")
        col_settings.prop(scene, "hrg_mocap_detailed_face", text="Use Detailed Face Bones")
        
        box_fine = col_settings.box()
        box_fine.label(text="Facial Sensitivities", icon='POSE_HLT')
        box_fine.prop(scene, "hrg_mocap_blink_mult", text="Blink Mult", slider=True)
        box_fine.prop(scene, "hrg_mocap_brow_mult", text="Brow Mult", slider=True)
        box_fine.prop(scene, "hrg_mocap_mouth_mult", text="Smile Mult", slider=True)
        box_fine.prop(scene, "hrg_mocap_jaw_mult", text="Jaw Open Mult", slider=True)
        
        col_settings.separator()
        col_settings.operator("mocap.force_calibrate", text="Reset T-Pose Calibration", icon='LOOP_BACK')

def get_default_camera_index():
    # If Camo Studio process is running on Windows, default to 2 (Camo Camera), otherwise 0
    import subprocess
    try:
        output = subprocess.check_output('tasklist', shell=True).decode('utf-8', errors='ignore')
        if "Camo" in output or "camo" in output:
            return '2'
    except Exception:
        pass
    return '0'

def register():
    # Scene properties
    bpy.types.Scene.hrg_mocap_source = bpy.props.EnumProperty(
        name="Mocap Source",
        description="Select where the motion capture feed should come from",
        items=[
            ('WEBCAM', "Webcam Live", "Capture live webcam stream"),
            ('VIDEO_FILE', "Video File", "Extract motion from a video file")
        ],
        default='WEBCAM'
    )
    bpy.types.Scene.hrg_mocap_camera_index = bpy.props.EnumProperty(
        name="Camera Select",
        description="Select which camera device to use",
        items=[
            ('0', "Camera 0 (Default)", "First camera device"),
            ('1', "Camera 1 (Camo Studio / External)", "Second camera device"),
            ('2', "Camera 2", "Third camera device"),
            ('3', "Camera 3", "Fourth camera device"),
            ('4', "Camera 4", "Fifth camera device")
        ],
        default=get_default_camera_index()
    )
    bpy.types.Scene.hrg_mocap_capture_mode = bpy.props.EnumProperty(
        name="Detection Mode",
        description="Choose what features to capture with motion tracking",
        items=[
            ('FULL', "Both (Body & Face)", "Capture Full Body Pose, Facial Expressions, and Dual Hands simultaneously", 'COMMUNITY', 0),
            ('BODY', "Body Only", "Capture Body Pose, Arms, and Legs without facial tracking", 'ARMATURE_DATA', 1),
            ('FACE', "Face Only", "Capture Facial Expressions and Head orientation without body tracking", 'MONKEY', 2),
            ('HANDS', "Hands Only", "Capture Finger gestures and Wrist tracking only", 'RESTRICT_SELECT_OFF', 3),
        ],
        default='FULL'
    )
    bpy.types.Scene.hrg_mocap_pose_complexity = bpy.props.EnumProperty(
        name="Pose Model Complexity",
        description="Choose MediaPipe Pose model tracking complexity (Lite = fastest, Heavy = most accurate)",
        items=[
            ('LITE', "Lite (Fastest)", "Lighter model, highest frame rate"),
            ('FULL', "Full (Balanced)", "Standard model, balanced tracking & speed"),
            ('HEAVY', "Heavy (Most Accurate)", "Heavier model, best hand/leg tracking precision"),
        ],
        default='FULL'
    )
    bpy.types.Scene.hrg_mocap_capture_resolution = bpy.props.EnumProperty(
        name="Processing Resolution",
        description="Resolution of frames fed into MediaPipe (lower = higher FPS, higher = finer tracking)",
        items=[
            ('LOW', "Low (480x270)", "Fastest processing, good for older CPUs"),
            ('MEDIUM', "Medium (640x360)", "Balanced performance & detail (Default)"),
            ('HIGH', "High (1280x720)", "Sharpest tracking, higher CPU requirement"),
        ],
        default='MEDIUM'
    )
    bpy.types.Scene.hrg_mocap_active = bpy.props.BoolProperty(
        name="Mocap Stream Active",
        default=False
    )
    bpy.types.Scene.hrg_mocap_backend_mode = bpy.props.BoolProperty(
        name="Use External Backend (Optimized 60 FPS)",
        description="Run webcam capture and MediaPipe in a separate high-performance process",
        default=True
    )
    bpy.types.Scene.hrg_mocap_show_visualizer = bpy.props.BoolProperty(
        name="Show Visualizer Window",
        description="Display the webcam tracking preview window (disabling this increases FPS)",
        default=False
    )
    bpy.types.Scene.hrg_mocap_detailed_face = bpy.props.BoolProperty(
        name="Use Detailed Face Bones",
        description="Translate individual facial bones (eyebrows, cheeks, lips) for high-fidelity expressions (requires good lighting and front-facing view)",
        default=False
    )
    bpy.types.Scene.hrg_mocap_streaming_fps = bpy.props.FloatProperty(
        name="Streaming FPS",
        description="Real-time frame rate of the incoming tracking stream",
        default=0.0
    )
    bpy.types.Scene.hrg_mocap_record = bpy.props.BoolProperty(
        name="Live Recording Enabled",
        description="Write keyframes to the timeline in real-time as you capture (disabling this runs at maximum 60 FPS preview speed)",
        default=False
    )
    bpy.types.Scene.hrg_mocap_video_path = bpy.props.StringProperty(
        name="Video Path",
        description="Path to pre-recorded video file for motion transfer",
        default="",
        subtype='FILE_PATH'
    )
    bpy.types.Scene.hrg_mocap_start_frame = bpy.props.IntProperty(
        name="Mocap Start Frame",
        default=1,
        min=1
    )
    bpy.types.Scene.hrg_mocap_end_frame = bpy.props.IntProperty(
        name="Mocap End Frame",
        default=250,
        min=1
    )
    bpy.types.Scene.hrg_mocap_smoothing = bpy.props.FloatProperty(
        name="Smoothing Filter Factor",
        description="Lower values = smoother/delayed, Higher values = raw/jittery",
        default=0.25,
        min=0.01,
        max=1.0
    )
    bpy.types.Scene.hrg_mocap_face_sensitivity = bpy.props.FloatProperty(
        name="Face Sensitivity Multiplier",
        description="Multiplier for scaling facial bone offsets",
        default=1.2,
        min=0.1,
        max=5.0
    )
    bpy.types.Scene.hrg_mocap_blink_mult = bpy.props.FloatProperty(
        name="Blink Sensitivity",
        description="Sensitivity multiplier for eye blinking",
        default=1.0,
        min=0.1,
        max=5.0
    )
    bpy.types.Scene.hrg_mocap_brow_mult = bpy.props.FloatProperty(
        name="Brow Sensitivity",
        description="Sensitivity multiplier for eyebrow raise",
        default=1.0,
        min=0.1,
        max=5.0
    )
    bpy.types.Scene.hrg_mocap_mouth_mult = bpy.props.FloatProperty(
        name="Smile Sensitivity",
        description="Sensitivity multiplier for mouth smile/frown",
        default=1.0,
        min=0.1,
        max=5.0
    )
    bpy.types.Scene.hrg_mocap_jaw_mult = bpy.props.FloatProperty(
        name="Jaw Open Sensitivity",
        description="Sensitivity multiplier for jaw opening",
        default=1.0,
        min=0.1,
        max=5.0
    )
    
    bpy.utils.register_class(VIEW3D_PT_mocap_transfer_panel)

def unregister():
    # Remove properties
    del bpy.types.Scene.hrg_mocap_source
    del bpy.types.Scene.hrg_mocap_camera_index
    del bpy.types.Scene.hrg_mocap_capture_mode
    del bpy.types.Scene.hrg_mocap_pose_complexity
    del bpy.types.Scene.hrg_mocap_capture_resolution
    del bpy.types.Scene.hrg_mocap_active
    del bpy.types.Scene.hrg_mocap_backend_mode
    del bpy.types.Scene.hrg_mocap_show_visualizer
    del bpy.types.Scene.hrg_mocap_detailed_face
    del bpy.types.Scene.hrg_mocap_streaming_fps
    del bpy.types.Scene.hrg_mocap_record
    del bpy.types.Scene.hrg_mocap_video_path
    del bpy.types.Scene.hrg_mocap_start_frame
    del bpy.types.Scene.hrg_mocap_end_frame
    del bpy.types.Scene.hrg_mocap_smoothing
    del bpy.types.Scene.hrg_mocap_face_sensitivity
    del bpy.types.Scene.hrg_mocap_blink_mult
    del bpy.types.Scene.hrg_mocap_brow_mult
    del bpy.types.Scene.hrg_mocap_mouth_mult
    del bpy.types.Scene.hrg_mocap_jaw_mult
    
    bpy.utils.unregister_class(VIEW3D_PT_mocap_transfer_panel)
