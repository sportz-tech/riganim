# mocap_processor.py
import sys
import os
import site
import time
import math
import bpy
import mathutils

# Ensure Blender searches user site-packages where pip --user installs files
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.append(user_site)

# Safe imports for dependencies. The addon will load even if libraries are not installed.
try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    dependencies_available = True
except Exception as e:
    dependencies_available = False
    print("[Mocap Processor] Import failed:", str(e))
    import traceback
    # Log to our scratch log
    log_file_path = "C:/Users/aispv/.gemini/antigravity-ide/scratch/hrg_mocap_install_debug.log"
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"[Mocap Processor Import Error] {str(e)}\n{traceback.format_exc()}\n")
    except Exception:
        pass

# Helper to download models if missing
def ensure_models_exist():
    """Ensures the MediaPipe task models are downloaded in the addon's models folder."""
    import urllib.request
    addon_dir = os.path.dirname(__file__)
    models_dir = os.path.join(addon_dir, "models")
    import zipfile
    os.makedirs(models_dir, exist_ok=True)
    
    pose_model_path = os.path.join(models_dir, "pose_landmarker_lite.task")
    face_model_path = os.path.join(models_dir, "face_landmarker.task")
    hand_model_path = os.path.join(models_dir, "hand_landmarker.task")
    
    urls = {
        pose_model_path: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        face_model_path: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        hand_model_path: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    }
    
    for path, url in urls.items():
        is_valid = False
        if os.path.exists(path) and os.path.getsize(path) > 100000:
            try:
                if zipfile.is_zipfile(path):
                    with zipfile.ZipFile(path, 'r') as z:
                        if len(z.namelist()) > 0:
                            is_valid = True
            except Exception:
                is_valid = False
                
        if not is_valid:
            print(f"[Mocap Addon] Downloading model from {url} to {path}...")
            try:
                if os.path.exists(path):
                    os.remove(path)
                tmp_path = path + ".tmp"
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                urllib.request.urlretrieve(url, tmp_path)
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100000:
                    os.replace(tmp_path, path)
                    print(f"[Mocap Addon] Successfully verified and saved model: {path}")
                else:
                    raise RuntimeError("Incomplete download")
            except Exception as e:
                print(f"[Mocap Addon] Model download failed: {str(e)}")
                raise e
                
    return pose_model_path, face_model_path, hand_model_path

# Custom drawing indices & function since solutions.drawing_utils is legacy
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28)
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (9, 10), (10, 11), (11, 12),
    (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17)
]

FACE_CONTOURS = [
    # Left eye outline
    [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
    # Right eye outline
    [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    # Left eyebrow outline
    [276, 283, 282, 295, 285],
    # Right eyebrow outline
    [46, 53, 52, 65, 55],
    # Lips outer outline
    [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 95],
    # Lips inner outline (upper and lower lips)
    [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95],
    # Nose contours
    [168, 6, 197, 195, 5, 4, 2, 97, 98, 326, 327],
    # Face silhouette / jawline
    [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
]

def draw_custom_landmarks(frame, pose_landmarks, face_landmarks, hand_result=None):
    h, w, c = frame.shape
    pts = {}
    
    if pose_landmarks:
        for idx, lm in enumerate(pose_landmarks.landmark):
            px = int(lm.x * w)
            py = int(lm.y * h)
            pts[idx] = (px, py)
            cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)
            
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in pts and end_idx in pts:
                cv2.line(frame, pts[start_idx], pts[end_idx], (0, 255, 0), 2)
                
        # Draw neck connection
        if 0 in pts and 11 in pts and 12 in pts:
            mid_shoulder_x = int((pts[11][0] + pts[12][0]) * 0.5)
            mid_shoulder_y = int((pts[11][1] + pts[12][1]) * 0.5)
            cv2.line(frame, (mid_shoulder_x, mid_shoulder_y), pts[0], (0, 255, 0), 2)
                
    if face_landmarks:
        # Save positions
        face_pts = {}
        for idx, lm in enumerate(face_landmarks.landmark):
            face_pts[idx] = (int(lm.x * w), int(lm.y * h))
            
        # Draw outline mesh lines
        for loop in FACE_CONTOURS:
            for i in range(len(loop)):
                p1 = loop[i]
                p2 = loop[(i + 1) % len(loop)]
                if p1 in face_pts and p2 in face_pts:
                    cv2.line(frame, face_pts[p1], face_pts[p2], (255, 255, 0), 1)
                    
        # Draw sparse dots on top
        for idx in range(0, len(face_landmarks.landmark), 5):
            if idx in face_pts:
                cv2.circle(frame, face_pts[idx], 1, (0, 255, 255), -1)

    if hand_result and hand_result.hand_landmarks:
        for landmarks_list in hand_result.hand_landmarks:
            hand_pts = {}
            for idx, lm in enumerate(landmarks_list):
                px = int(lm.x * w)
                py = int(lm.y * h)
                hand_pts[idx] = (px, py)
                cv2.circle(frame, (px, py), 3, (0, 255, 255), -1)
                
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx in hand_pts and end_idx in hand_pts:
                    cv2.line(frame, hand_pts[start_idx], hand_pts[end_idx], (0, 255, 255), 1)

# Exponential moving average filter for smoothing mocap coordinates
class ExponentialSmoother:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.prev_val = None
        
    def filter(self, val):
        # Handle Euler orientation smoothing using Quaternion Slerp to avoid gimbal lock
        if isinstance(val, mathutils.Euler):
            q_val = val.to_quaternion()
            if self.prev_val is None:
                self.prev_val = q_val.copy()
                return val
            q_smoothed = self.prev_val.slerp(q_val, self.alpha)
            self.prev_val = q_smoothed
            return q_smoothed.to_euler(val.order)
            
        if self.prev_val is None:
            self.prev_val = val.copy() if hasattr(val, "copy") else val
            return val
        if hasattr(val, "lerp"): # Mathutils Vector/Quaternion support
            smoothed = self.prev_val.lerp(val, self.alpha)
        else:
            smoothed = self.alpha * val + (1.0 - self.alpha) * self.prev_val
        self.prev_val = smoothed
        return smoothed

# One Euro Filter for adaptive low-pass smoothing (industry standard for clean motion capture)
class OneEuroFilter:
    def __init__(self, mincutoff=0.8, beta=0.03, dcutoff=1.0):
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None
        
    def filter(self, x, t=None):
        if t is None:
            t = time.time()
            
        # Handle Euler rotation conversion to Quaternion for geodesic/slerp-like smoothing
        is_euler = isinstance(x, mathutils.Euler)
        if is_euler:
            val = x.to_quaternion()
        else:
            val = x
            
        if self.x_prev is None:
            self.x_prev = val.copy() if hasattr(val, "copy") else val
            if isinstance(val, mathutils.Quaternion):
                self.dx_prev = mathutils.Vector((0.0, 0.0, 0.0))
            elif isinstance(val, mathutils.Vector):
                self.dx_prev = mathutils.Vector((0.0, 0.0, 0.0))
            elif hasattr(val, "copy"):
                self.dx_prev = val.copy()
                if hasattr(self.dx_prev, "zero"):
                    self.dx_prev.zero()
                else:
                    self.dx_prev = 0.0 * val
            else:
                self.dx_prev = 0.0
            self.t_prev = t
            return x
            
        dt = t - self.t_prev
        if dt <= 0.0001:
            return x
            
        # Calculate alpha for derivative
        tau_d = 1.0 / (2.0 * math.pi * self.dcutoff)
        alpha_d = 1.0 / (1.0 + tau_d / dt)
        
        # Calculate dx = (val - x_prev) / dt
        if isinstance(val, mathutils.Quaternion):  # Quaternion
            q_diff = self.x_prev.inverted() @ val
            axis, angle = q_diff.to_axis_angle()
            angle = (angle + math.pi) % (2.0 * math.pi) - math.pi
            dx = axis * (angle / dt) if abs(angle) > 0.0001 else mathutils.Vector((0, 0, 0))
        elif isinstance(val, mathutils.Vector):  # Vector
            dx = (val - self.x_prev) * (1.0 / dt)
        else:
            dx = (val - self.x_prev) / dt
            
        # Smooth the derivative
        if self.dx_prev is None:
            self.dx_prev = dx
        else:
            if isinstance(dx, mathutils.Vector):
                self.dx_prev = self.dx_prev.lerp(dx, alpha_d)
            else:
                self.dx_prev = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev
                
        # Cutoff frequency based on speed
        if isinstance(self.dx_prev, mathutils.Vector):
            speed = self.dx_prev.length
        else:
            speed = abs(self.dx_prev)
            
        cutoff = self.mincutoff + self.beta * speed
        
        # Calculate alpha for signal
        tau = 1.0 / (2.0 * math.pi * cutoff)
        alpha = 1.0 / (1.0 + tau / dt)
        
        # Smooth signal
        if isinstance(val, mathutils.Quaternion):  # Quaternion
            x_hat = self.x_prev.slerp(val, alpha)
        elif isinstance(val, mathutils.Vector):  # Vector
            x_hat = self.x_prev.lerp(val, alpha)
        else:
            x_hat = alpha * val + (1.0 - alpha) * self.x_prev
            
        self.x_prev = x_hat
        self.t_prev = t
        
        if is_euler:
            return x_hat.to_euler(x.order)
        return x_hat

def get_or_update_filter(smoothers, key, min_cut, beta_val):
    if key not in smoothers:
        smoothers[key] = OneEuroFilter(min_cut, beta_val)
    else:
        smoothers[key].mincutoff = min_cut
        smoothers[key].beta = beta_val
    return smoothers[key]

def get_local_disp(pb, target_pos_arm):
    """Calculates the exact pb.location vector in bone local space to reach target_pos_arm in armature space."""
    if pb.parent:
        target_in_parent = pb.parent.matrix.inverted() @ target_pos_arm
        rest_in_parent = pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local.translation
        delta = target_in_parent - rest_in_parent
        return pb.bone.matrix_local.to_3x3().inverted() @ pb.parent.bone.matrix_local.to_3x3() @ delta
    else:
        delta = target_pos_arm - pb.bone.matrix_local.translation
        return pb.bone.matrix_local.to_3x3().inverted() @ delta

# Face bone mappings: {BoneName: MediaPipeLandmarkIndex}
FACE_BONE_LANDMARKS = {
    # Eyebrow control bones
    "CTRL-eyebrow.L": 63,
    "CTRL-eyebrow.R": 293,
    
    # Cheeks
    "ORG-cheek.L": 117,
    "ORG-cheek.R": 346,
    
    # Single lip corner tracking (291 is Left, 61 is Right)
    "ORG-lip.corner.L": 291,
    "ORG-lip.corner.R": 61,
}

# Calibration storage
class MocapCalibration:
    def __init__(self):
        self.is_calibrated = False
        self.frame_count = 0
        self.user_torso_length = 1.0
        self.rig_torso_length = 1.0
        self.scale_factor = 1.0
        
        # Reference/Neutral landmarks in local face space
        self.face_ref_landmarks = {}
        
        # Reference body landmark values
        self.ref_l_shoulder = None
        self.ref_r_shoulder = None
        self.ref_l_hip = None
        self.ref_r_hip = None
        self.ref_hips = None
        
        # Reference/Neutral rotations
        self.ref_face_R = None
        self.ref_face_size = 1.0
        self.ref_hip_yaw = 0.0
        self.ref_sh_yaw = 0.0
        self.ref_sh_roll = 0.0
        self.ref_spine_pitch = 0.0
        
        # Reference/Neutral coordinates for local displacement tracking
        self.ref_l_wrist = None
        self.ref_r_wrist = None
        self.ref_l_elbow = None
        self.ref_r_elbow = None
        self.ref_l_ankle = None
        self.ref_r_ankle = None
        self.ref_l_knee = None
        self.ref_r_knee = None
        
        # Reference hand rotation matrices
        self.ref_l_hand_R = None
        self.ref_r_hand_R = None
        
        # Neutral face property reference measurements
        self.ref_brow_dist_l = 0.15
        self.ref_brow_dist_r = 0.15
        self.ref_mouth_corner_z_l = 0.0
        self.ref_mouth_corner_z_r = 0.0
        self.ref_lip_dist = 0.02
        self.ref_chin_dist = 0.22
        self.min_chin_dist = 0.22
        self.min_brow_dist_l = 0.15
        self.min_brow_dist_r = 0.15

# Global calibration state
calibration_data = MocapCalibration()

def to_blender_vec(landmark):
    """Converts a MediaPipe landmark coordinate to Blender's coordinate system."""
    # MediaPipe: X horizontal (0-1, left-to-right), Y vertical (0-1, top-to-bottom), Z depth
    # Blender: X horizontal (right-positive), Y depth (back-positive), Z vertical (up-positive)
    return mathutils.Vector((landmark.x, landmark.z, -landmark.y))

def get_face_basis(landmarks):
    """Constructs a local coordinate basis matrix for the face to ensure rotation invariance."""
    p_origin = to_blender_vec(landmarks[168]) # Nose bridge center
    
    # Up vector (nose bridge to forehead center)
    v_up = (to_blender_vec(landmarks[10]) - p_origin).normalized()
    
    # Right vector (right temple to left temple to point positive X)
    # Swap temples since X is not inverted in to_blender_vec anymore
    v_right = (to_blender_vec(landmarks[356]) - to_blender_vec(landmarks[127])).normalized()
    
    # Forward vector (orthogonal cross product pointing positive Y for right-handedness)
    v_forward = v_up.cross(v_right).normalized()
    v_right = v_forward.cross(v_up).normalized() # Re-orthogonalize
    
    # Rotation matrix to align points into face-local space (Column 0=X, Column 1=Y, Column 2=Z)
    R = mathutils.Matrix((v_right, v_forward, v_up)).transposed()
    return p_origin, R

def get_hand_orientation(landmarks_list):
    """Computes the 3D rotation matrix (basis) of a hand from its knuckles."""
    wrist = to_blender_vec(landmarks_list[0])
    index_mcp = to_blender_vec(landmarks_list[5])
    pinky_mcp = to_blender_vec(landmarks_list[17])
    
    forward = (index_mcp - wrist).normalized()
    across = (pinky_mcp - index_mcp).normalized()
    normal = forward.cross(across).normalized()
    
    # Re-align across to ensure perfect orthogonal basis
    across = normal.cross(forward).normalized()
    
    # Orientation matrix: X = across, Y = normal, Z = forward
    R = mathutils.Matrix((across, normal, forward)).transposed()
    return R

def calibrate_mocap(landmarks, hand_result, rig_obj):
    """Calibrates scale and reference neutral transforms using the current frame."""
    global calibration_data
    
    if not landmarks.pose_landmarks and not landmarks.face_landmarks and not (hand_result and hand_result.hand_landmarks):
        return False
        
    if landmarks.pose_landmarks:
        has_world = hasattr(landmarks, "pose_world_landmarks") and landmarks.pose_world_landmarks is not None
        pl = landmarks.pose_landmarks.landmark
        wl = landmarks.pose_world_landmarks.landmark if has_world else pl
        
        # Calculate key landmarks
        mp_shoulders = (to_blender_vec(pl[11]) + to_blender_vec(pl[12])) * 0.5
        
        # Check hip visibility to ensure torso calibration is valid
        hips_visible = (pl[23].visibility > 0.4 and pl[24].visibility > 0.4)
        
        if hips_visible:
            mp_hips = (to_blender_vec(pl[23]) + to_blender_vec(pl[24])) * 0.5
            user_torso = (mp_shoulders - mp_hips).length
            if user_torso <= 0.1 or user_torso > 0.8:
                user_torso = 0.35
                mp_hips = mp_shoulders.copy()
                mp_hips.z -= user_torso
        else:
            user_torso = 0.35
            mp_hips = mp_shoulders.copy()
            mp_hips.z -= user_torso
            
        # Rig torso length (chest to pelvis center)
        pb_chest = rig_obj.pose.bones.get("CTRL-spine.003") or rig_obj.pose.bones.get("CTRL-chest")
        pb_pelvis = rig_obj.pose.bones.get("CTRL-pelvis")
        if pb_chest and pb_pelvis:
            rig_torso = (pb_chest.bone.matrix_local.translation - pb_pelvis.bone.matrix_local.translation).length
        else:
            rig_torso = 0.65
            
        calibration_data.user_torso_length = user_torso
        calibration_data.rig_torso_length = rig_torso
        calibration_data.scale_factor = rig_torso / max(0.01, user_torso)
        
        # Store reference body landmarks
        calibration_data.ref_l_shoulder = to_blender_vec(pl[11])
        calibration_data.ref_r_shoulder = to_blender_vec(pl[12])
        calibration_data.ref_hips = mp_hips.copy()
        
        # Force symmetric shoulder width for calibration to prevent offset bias
        sh_half_width = (calibration_data.ref_l_shoulder - calibration_data.ref_r_shoulder).length * 0.5
        calibration_data.ref_l_shoulder = mp_shoulders + mathutils.Vector((sh_half_width, 0, 0))
        calibration_data.ref_r_shoulder = mp_shoulders + mathutils.Vector((-sh_half_width, 0, 0))
        
        if hips_visible:
            calibration_data.ref_l_hip = to_blender_vec(pl[23])
            calibration_data.ref_r_hip = to_blender_vec(pl[24])
            hip_half_width = (calibration_data.ref_l_hip - calibration_data.ref_r_hip).length * 0.5
            calibration_data.ref_l_hip = mp_hips + mathutils.Vector((hip_half_width, 0, 0))
            calibration_data.ref_r_hip = mp_hips + mathutils.Vector((-hip_half_width, 0, 0))
        else:
            hip_half_width = sh_half_width * 0.8
            calibration_data.ref_l_hip = mp_hips + mathutils.Vector((hip_half_width, 0, 0))
            calibration_data.ref_r_hip = mp_hips + mathutils.Vector((-hip_half_width, 0, 0))
        
        # Reference body positions for displacement-based tracking (using metric world landmarks)
        calibration_data.ref_l_wrist = to_blender_vec(wl[15])
        calibration_data.ref_r_wrist = to_blender_vec(wl[16])
        calibration_data.ref_l_elbow = to_blender_vec(wl[13])
        calibration_data.ref_r_elbow = to_blender_vec(wl[14])
        calibration_data.ref_l_ankle = to_blender_vec(wl[27])
        calibration_data.ref_r_ankle = to_blender_vec(wl[28])
        calibration_data.ref_l_knee = to_blender_vec(wl[25])
        calibration_data.ref_r_knee = to_blender_vec(wl[26])
        
        # Metric rotation calibration (using wl)
        wl_l_hip = to_blender_vec(wl[23])
        wl_r_hip = to_blender_vec(wl[24])
        hip_vec_ref = (wl_l_hip - wl_r_hip).normalized()
        calibration_data.ref_hip_yaw = math.atan2(hip_vec_ref.y, hip_vec_ref.x)
        
        wl_l_shoulder = to_blender_vec(wl[11])
        wl_r_shoulder = to_blender_vec(wl[12])
        sh_vec_ref = (wl_l_shoulder - wl_r_shoulder).normalized()
        calibration_data.ref_sh_yaw = math.atan2(sh_vec_ref.y, sh_vec_ref.x)
        calibration_data.ref_sh_roll = math.atan2(sh_vec_ref.z, sh_vec_ref.x)
        
        wl_mp_shoulders = (wl_l_shoulder + wl_r_shoulder) * 0.5
        if hips_visible:
            wl_mp_hips = (wl_l_hip + wl_r_hip) * 0.5
        else:
            wl_mp_hips = wl_mp_shoulders.copy()
            wl_mp_hips.z -= 0.55  # average torso length in meters
        ref_spine_vec = (wl_mp_shoulders - wl_mp_hips).normalized()
        calibration_data.ref_spine_pitch = math.atan2(ref_spine_vec.y, ref_spine_vec.z)
    else:
        calibration_data.scale_factor = 1.0
        calibration_data.ref_l_shoulder = mathutils.Vector((0.2, 0, 0))
        calibration_data.ref_r_shoulder = mathutils.Vector((-0.2, 0, 0))
        calibration_data.ref_l_wrist = mathutils.Vector((0.4, 0, -0.4))
        calibration_data.ref_r_wrist = mathutils.Vector((-0.4, 0, -0.4))
    
    # Face reference coordinate calibration
    if landmarks.face_landmarks:
        fl = landmarks.face_landmarks.landmark
        p_origin, R = get_face_basis(fl)
        R_inv = R.inverted()
        calibration_data.ref_face_R = R.copy()
        # Compute rigid face reference size using temple-to-temple distance
        calibration_data.ref_face_size = (to_blender_vec(fl[356]) - to_blender_vec(fl[127])).length
        
        for name, idx in FACE_BONE_LANDMARKS.items():
            p_lm = to_blender_vec(fl[idx])
            local_pos = R_inv @ (p_lm - p_origin)
            calibration_data.face_ref_landmarks[name] = local_pos
            
        # Store neutral eyebrow-to-eye vertical distances
        dist_l = math.sqrt((fl[70].x - fl[159].x)**2 + (fl[70].y - fl[159].y)**2)
        dist_r = math.sqrt((fl[300].x - fl[386].x)**2 + (fl[300].y - fl[386].y)**2)
        calibration_data.ref_brow_dist_l = dist_l / max(0.001, calibration_data.ref_face_size)
        calibration_data.ref_brow_dist_r = dist_r / max(0.001, calibration_data.ref_face_size)
        
        # Store neutral mouth corner local Z coordinates
        lc_local = R_inv @ (to_blender_vec(fl[291]) - p_origin)
        rc_local = R_inv @ (to_blender_vec(fl[61]) - p_origin)
        calibration_data.ref_mouth_corner_z_l = lc_local.z
        calibration_data.ref_mouth_corner_z_r = rc_local.z
        
        # Store neutral lip distance (capped to prevent calibration from locking mouth closed)
        lip_dist = math.sqrt((fl[13].x - fl[14].x)**2 + (fl[13].y - fl[14].y)**2)
        head_dist = math.sqrt((fl[10].x - fl[152].x)**2 + (fl[10].y - fl[152].y)**2)
        calibration_data.ref_lip_dist = min(0.010, lip_dist / max(0.001, head_dist))
        
        # Store neutral mouth width and inner lip aperture for phonetic speech tracking
        calibration_data.ref_mouth_width = max(0.02, (lc_local - rc_local).length)
        p_13_local = R_inv @ (to_blender_vec(fl[13]) - p_origin)
        p_14_local = R_inv @ (to_blender_vec(fl[14]) - p_origin)
        calibration_data.ref_inner_lip_open = max(0.001, p_13_local.z - p_14_local.z)
        
        # Store neutral forehead-to-chin local Z distance
        p_10_local = R_inv @ (to_blender_vec(fl[10]) - p_origin)
        p_152_local = R_inv @ (to_blender_vec(fl[152]) - p_origin)
        calibration_data.ref_chin_dist = p_10_local.z - p_152_local.z
        
        calibration_data.min_chin_dist = calibration_data.ref_chin_dist
        calibration_data.min_brow_dist_l = calibration_data.ref_brow_dist_l
        calibration_data.min_brow_dist_r = calibration_data.ref_brow_dist_r
    else:
        calibration_data.ref_face_R = mathutils.Matrix.Identity(3)
        calibration_data.ref_face_size = 1.0
        calibration_data.ref_brow_dist_l = 0.15
        calibration_data.ref_brow_dist_r = 0.15
        calibration_data.ref_mouth_corner_z_l = 0.0
        calibration_data.ref_mouth_corner_z_r = 0.0
        calibration_data.ref_lip_dist = 0.02
        calibration_data.ref_mouth_width = 0.065
        calibration_data.ref_inner_lip_open = 0.005
        calibration_data.ref_chin_dist = 0.22
        calibration_data.min_chin_dist = 0.22
        calibration_data.min_brow_dist_l = 0.15
        calibration_data.min_brow_dist_r = 0.15
        
    calibration_data.is_calibrated = True
    return True

def auto_heal_rig_constraints(rig_obj):
    """Checks and automatically adds missing Copy_CTRL constraints between controllers and ORG bones."""
    body_ctrls = [
        "pelvis", "spine", "spine.001", "spine.002", "spine.003", "neck", "head",
        "shoulder.L", "shoulder.R", "jaw",
        "tail.001", "tail.002", "tail.003"
    ]
    for base in body_ctrls:
        ctrl_name = f"CTRL-{base}"
        org_name = f"ORG-{base}"
        def_name = f"DEF-{base}"
        
        pb_ctrl = rig_obj.pose.bones.get(ctrl_name)
        pb_org = rig_obj.pose.bones.get(org_name)
        pb_def = rig_obj.pose.bones.get(def_name)
        
        # 1. ORG copies CTRL
        if pb_org and pb_ctrl:
            has_copy_ctrl = False
            for c in pb_org.constraints:
                if c.type == 'COPY_TRANSFORMS' and c.subtarget == ctrl_name:
                    has_copy_ctrl = True
                    break
            if not has_copy_ctrl:
                # Remove duplicate constraints first
                for c in list(pb_org.constraints):
                    if c.name == "Copy_CTRL":
                        pb_org.constraints.remove(c)
                c_new = pb_org.constraints.new(type='COPY_TRANSFORMS')
                c_new.name = "Copy_CTRL"
                c_new.target = rig_obj
                c_new.subtarget = ctrl_name
                c_new.owner_space = 'WORLD'
                c_new.target_space = 'WORLD'
                
        # 2. DEF copies ORG
        if pb_def and pb_org:
            has_copy_org = False
            for c in pb_def.constraints:
                if c.type == 'COPY_TRANSFORMS' and c.subtarget == org_name:
                    has_copy_org = True
                    break
            if not has_copy_org:
                # Remove duplicate constraints first
                for c in list(pb_def.constraints):
                    if c.name == "Copy_ORG":
                        pb_def.constraints.remove(c)
                c_new = pb_def.constraints.new(type='COPY_TRANSFORMS')
                c_new.name = "Copy_ORG"
                c_new.target = rig_obj
                c_new.subtarget = org_name
                c_new.owner_space = 'WORLD'
                c_new.target_space = 'WORLD'

def apply_mocap_to_rig(landmarks, hand_result, rig_obj, scene, smoothers):
    """Processes captured frame landmarks and writes transforms to the active rig."""
    global calibration_data
    
    # Auto-heal rig copy constraints
    try:
        auto_heal_rig_constraints(rig_obj)
    except Exception as e_heal:
        print("Rig heal error:", e_heal)
    
    # One-time structure diagnostic
    if not hasattr(calibration_data, "diagnostic_run"):
        calibration_data.diagnostic_run = True
        try:
            with open("f:/blenderaddon/mocap_debug.log", "a") as f_log:
                f_log.write("=== RIG DIAGNOSTIC REPORT ===\n")
                f_log.write(f"Active Rig: {rig_obj.name} | Type: {rig_obj.type} | Mode: {rig_obj.mode}\n")
                f_log.write("Bones list containing 'jaw':\n")
                for b in rig_obj.pose.bones:
                    if "jaw" in b.name.lower():
                        f_log.write(f"  Bone: {b.name} | Rotation Mode: {b.rotation_mode} | Parent: {b.parent.name if b.parent else 'None'}\n")
                        for c in b.constraints:
                            target_str = c.subtarget if hasattr(c, "subtarget") else "None"
                            f_log.write(f"    Constraint: {c.name} ({c.type}) | Target: {target_str} | Influence: {c.influence} | Mute: {c.mute}\n")
                
                f_log.write("Mesh objects child of rig & their vertex groups:\n")
                for child in rig_obj.children:
                    if child.type == 'MESH':
                        vg_names = [vg.name for vg in child.vertex_groups if "jaw" in vg.name.lower()]
                        f_log.write(f"  Mesh: {child.name} | Jaw Vertex Groups: {vg_names}\n")
                f_log.write("=== END DIAGNOSTIC REPORT ===\n")
        except Exception as diag_err:
            try:
                with open("f:/blenderaddon/mocap_debug.log", "a") as f_log:
                    f_log.write(f"DIAG_ERROR: {str(diag_err)}\n")
            except:
                pass
    
    if not calibration_data.is_calibrated:
        calibration_data.frame_count += 1
        remaining_s = max(0, 45 - calibration_data.frame_count) / 30.0
        if remaining_s > 0:
            print(f"Mocap stabilizing... calibrating in {remaining_s:.1f}s. Please stand in neutral T-pose.")
            return
        success = calibrate_mocap(landmarks, hand_result, rig_obj)
        if not success:
            return
        
    # Setup custom settings and map UI smoothing (0 to 1) to One Euro Filter parameters
    ui_smooth = scene.hrg_mocap_smoothing
    
    # 1. Location smoothing parameters (high reactivity)
    min_cut_loc = max(0.005, 1.0 * (1.0 - ui_smooth))
    beta_loc = 0.15 * (1.0 - ui_smooth)
    
    # 2. Rotation smoothing parameters (prioritize smoothness)
    min_cut_rot = max(0.002, 0.5 * (1.0 - ui_smooth))
    beta_rot = 0.08 * (1.0 - ui_smooth)
    
    # 3. Face smoothing parameters (ultra-smooth face)
    min_cut_face = max(0.001, 0.3 * (1.0 - ui_smooth))
    beta_face = 0.05 * (1.0 - ui_smooth)
    
    face_mult = scene.hrg_mocap_face_sensitivity
    
    # Get base world matrix factoring in root control bone (which handles follow-path constraint)
    pb_root = rig_obj.pose.bones.get("CTRL-root")
    if pb_root:
        mat_base = rig_obj.matrix_world @ pb_root.matrix
    else:
        mat_base = rig_obj.matrix_world
        
    # Get inverted world matrix to apply offsets in rig space
    mat_world_inv = mat_base.inverted()
    # Extract scale-free orientation component to rotate offsets without double-scaling them
    R_world_inv = mat_world_inv.to_quaternion().to_matrix()
    
    # ------------------
    # 1. Body Pose Mocap
    # ------------------
    if landmarks.pose_landmarks:
        # Force IK mode for arms and legs to ensure deforming bones follow the tracked IK targets
        try:
            from HumanRigGenerator.registration import update_ik_fk_blend
        except ImportError:
            update_ik_fk_blend = None
            
        for side in [".L", ".R"]:
            for prefix_ik in ["hand_IK", "foot_IK"]:
                pb_ik = rig_obj.pose.bones.get(f"CTRL-{prefix_ik}{side}")
                if pb_ik:
                    # For HumanRigGenerator rigs: 1.0 is IK
                    if hasattr(pb_ik, "hrg_ik_fk"):
                        pb_ik.hrg_ik_fk = 1.0
                    if update_ik_fk_blend:
                        try:
                            update_ik_fk_blend(pb_ik, bpy.context)
                        except Exception:
                            pass
                            
                    # For standard Rigify / CC4 Pipeline rigs: 0.0 is IK, 1.0 is FK
                    for prop in list(pb_ik.keys()):
                        prop_lower = prop.lower()
                        if "ik" in prop_lower and "fk" in prop_lower:
                            pb_ik[prop] = 0.0
                        elif "ikfk" in prop_lower:
                            pb_ik[prop] = 0.0
            # Reset pole targets block removed to allow active tracking
                    
        mocap_mode = getattr(scene, "hrg_mocap_capture_mode", "FULL")
        track_body = mocap_mode in ['FULL', 'BODY']
        track_face = mocap_mode in ['FULL', 'FACE']
        track_hands = mocap_mode in ['FULL', 'BODY', 'HANDS']
        
        has_world = hasattr(landmarks, "pose_world_landmarks") and landmarks.pose_world_landmarks is not None
        pl = landmarks.pose_landmarks.landmark if landmarks.pose_landmarks else None
        wl = landmarks.pose_world_landmarks.landmark if has_world else pl
        scale = calibration_data.scale_factor
        
        # Calculate key landmarks
        if pl and track_body:
            mp_l_shoulder = to_blender_vec(pl[11])
            mp_r_shoulder = to_blender_vec(pl[12])
            mp_shoulders = (mp_l_shoulder + mp_r_shoulder) * 0.5
            hips_visible = (pl[23].visibility > 0.4 and pl[24].visibility > 0.4)
            if hips_visible:
                mp_hips = (to_blender_vec(pl[23]) + to_blender_vec(pl[24])) * 0.5
            else:
                mp_hips = mp_shoulders.copy()
                mp_hips.z -= calibration_data.user_torso_length
        else:
            mp_shoulders = mathutils.Vector((0, 0, 0))
            mp_hips = mathutils.Vector((0, 0, 0))
            hips_visible = False
        
        # Always obtain global wrist coordinates from the Pose Landmarker (screen coordinates)
        left_wrist_coords = None
        right_wrist_coords = None
        left_hand_landmarks = None
        right_hand_landmarks = None
        
        # Holistic direct hand extraction
        if hasattr(landmarks, 'left_hand_landmarks') and landmarks.left_hand_landmarks:
            l_lms = landmarks.left_hand_landmarks.landmark if hasattr(landmarks.left_hand_landmarks, 'landmark') else landmarks.left_hand_landmarks
            if len(l_lms) > 0:
                left_hand_landmarks = l_lms
                depth_l = to_blender_vec(pl[15]).y if (pl and pl[15].visibility > 0.1) else calibration_data.ref_l_wrist.y
                left_wrist_coords = mathutils.Vector((
                    to_blender_vec(l_lms[0]).x,
                    depth_l,
                    to_blender_vec(l_lms[0]).z
                ))

        if hasattr(landmarks, 'right_hand_landmarks') and landmarks.right_hand_landmarks:
            r_lms = landmarks.right_hand_landmarks.landmark if hasattr(landmarks.right_hand_landmarks, 'landmark') else landmarks.right_hand_landmarks
            if len(r_lms) > 0:
                right_hand_landmarks = r_lms
                depth_r = to_blender_vec(pl[16]).y if (pl and pl[16].visibility > 0.1) else calibration_data.ref_r_wrist.y
                right_wrist_coords = mathutils.Vector((
                    to_blender_vec(r_lms[0]).x,
                    depth_r,
                    to_blender_vec(r_lms[0]).z
                ))

        if left_hand_landmarks is None or right_hand_landmarks is None:
            if hand_result and hand_result.hand_landmarks:
                for hand_idx, landmarks_list in enumerate(hand_result.hand_landmarks):
                    if len(landmarks_list) > 0:
                        handedness = hand_result.handedness[hand_idx][0].category_name
                        # Mirrored frame: Left category is user's left hand
                        if handedness == "Left" and left_hand_landmarks is None:
                            depth_l = to_blender_vec(pl[15]).y if (pl and pl[15].visibility > 0.1) else calibration_data.ref_l_wrist.y
                            left_wrist_coords = mathutils.Vector((
                                to_blender_vec(landmarks_list[0]).x,
                                depth_l,
                                to_blender_vec(landmarks_list[0]).z
                            ))
                            left_hand_landmarks = landmarks_list
                        elif handedness != "Left" and right_hand_landmarks is None:
                            depth_r = to_blender_vec(pl[16]).y if (pl and pl[16].visibility > 0.1) else calibration_data.ref_r_wrist.y
                            right_wrist_coords = mathutils.Vector((
                                to_blender_vec(landmarks_list[0]).x,
                                depth_r,
                                to_blender_vec(landmarks_list[0]).z
                            ))
                            right_hand_landmarks = landmarks_list
                            
        if left_wrist_coords is None:
            left_wrist_coords = to_blender_vec(wl[15]) if wl else mathutils.Vector((0, 0, 0))
            
        if right_wrist_coords is None:
            right_wrist_coords = to_blender_vec(wl[16]) if wl else mathutils.Vector((0, 0, 0))
        
        # Temp debug file logging
        try:
            with open("f:/blenderaddon/mocap_debug.log", "a") as f_log:
                f_log.write(f"TIME: {time.time():.2f} | scale: {scale:.4f} | hips_visible: {hips_visible}\n")
                pb_spine = rig_obj.pose.bones.get("CTRL-spine")
                pb_chest = rig_obj.pose.bones.get("CTRL-spine.003")
                pb_pelvis = rig_obj.pose.bones.get("CTRL-pelvis")
                if pb_spine:
                    f_log.write(f"  Spine rot: {pb_spine.rotation_euler}\n")
                if pb_chest:
                    f_log.write(f"  Chest rot: {pb_chest.rotation_euler}\n")
                if pb_pelvis:
                    f_log.write(f"  Pelvis loc: {pb_pelvis.location} | rot: {pb_pelvis.rotation_euler}\n")
        except Exception as e:
            try:
                with open("f:/blenderaddon/mocap_debug.log", "a") as f_log:
                    f_log.write(f"  DIAG_ERROR: {str(e)}\n")
            except:
                pass
            
        root_mat_inv = mathutils.Matrix.Identity(4)
        R_world_inv = mathutils.Matrix.Identity(3)
        if pl and track_body:
            pb_root = rig_obj.pose.bones.get("CTRL-root")
            if pb_root:
                root_mat_inv = pb_root.matrix.inverted()
                R_world_inv = root_mat_inv.to_3x3()

        # Pelvis translation displacement
        # Force pelvis to stay in place if lower body is not visible to prevent crouching/snapping
        if hips_visible:
            disp_pelvis = (mp_hips - calibration_data.ref_hips) * scale
            # Force vertical pelvis translation to 0.0 ALWAYS to prevent camera distance distortion/crouching bugs
            disp_pelvis.z = 0.0
        else:
            disp_pelvis = mathutils.Vector((0, 0, 0))
            
        pb_pelvis = rig_obj.pose.bones.get("CTRL-pelvis")
        if pb_pelvis:
            target_pelvis = R_world_inv @ disp_pelvis
            filter_p_loc = get_or_update_filter(smoothers, "pelvis_loc", min_cut_loc, beta_loc)
            pb_pelvis.location = filter_p_loc.filter(target_pelvis)
            
            # Pelvis rotation: align to hips rotation vector
            if hips_visible:
                wl_l_hip = to_blender_vec(wl[23])
                wl_r_hip = to_blender_vec(wl[24])
                hip_vec = (wl_l_hip - wl_r_hip).normalized()
                hip_yaw = math.atan2(hip_vec.y, hip_vec.x)
                rel_hip_yaw = hip_yaw - calibration_data.ref_hip_yaw
                rel_hip_yaw = (rel_hip_yaw + math.pi) % (2 * math.pi) - math.pi
            else:
                rel_hip_yaw = 0.0
            
            filter_p_rot = get_or_update_filter(smoothers, "pelvis_rot", min_cut_rot, beta_rot)
            yaw_smoothed = filter_p_rot.filter(rel_hip_yaw)
            
            # Rotate pelvis around vertical axis using our robust basis transform
            R_yaw = mathutils.Matrix.Rotation(yaw_smoothed, 3, 'Z')
            B_rest = pb_pelvis.bone.matrix_local.to_3x3()
            R_local = B_rest.inverted() @ R_yaw @ B_rest
            pb_pelvis.rotation_euler = R_local.to_euler(pb_pelvis.rotation_mode)
            
        # Spine rotation (CTRL-spine.003 - chest, distributed with CTRL-spine)
        pb_chest = rig_obj.pose.bones.get("CTRL-spine.003")
        if pb_chest:
            wl_l_shoulder = to_blender_vec(wl[11])
            wl_r_shoulder = to_blender_vec(wl[12])
            wl_shoulders = (wl_l_shoulder + wl_r_shoulder) * 0.5
            wl_l_hip = to_blender_vec(wl[23])
            wl_r_hip = to_blender_vec(wl[24])
            
            if hips_visible:
                wl_hips = (wl_l_hip + wl_r_hip) * 0.5
                sh_vec = (wl_l_shoulder - wl_r_shoulder).normalized()
                sh_yaw = math.atan2(sh_vec.y, sh_vec.x)
                
                # Relative chest yaw (twist)
                rel_sh_yaw = sh_yaw - calibration_data.ref_sh_yaw
                rel_sh_yaw = (rel_sh_yaw + math.pi) % (2 * math.pi) - math.pi
                
                # Torso pitch (bend forward/backward)
                spine_vec = (wl_shoulders - wl_hips).normalized()
                spine_pitch = math.atan2(spine_vec.y, spine_vec.z)
                
                # Relative chest pitch
                rel_spine_pitch = spine_pitch - calibration_data.ref_spine_pitch
                rel_spine_pitch = (rel_spine_pitch + math.pi) % (2 * math.pi) - math.pi
                
                # Torso roll (bend side-to-side)
                sh_roll = math.atan2(sh_vec.z, sh_vec.x)
                rel_sh_roll = sh_roll - calibration_data.ref_sh_roll
                rel_sh_roll = (rel_sh_roll + math.pi) % (2 * math.pi) - math.pi
            else:
                # Lock chest and spine to straight upright T-pose when hips are cut off (sitting / close-up)
                rel_sh_yaw = 0.0
                rel_spine_pitch = 0.0
                rel_sh_roll = 0.0
            
            filter_c_rot = get_or_update_filter(smoothers, "chest_rot", min_cut_rot, beta_rot)
            # Vector mapping: X = pitch, Y = twist (yaw), Z = roll (side-bend)
            rot_smoothed = filter_c_rot.filter(mathutils.Vector((rel_spine_pitch, rel_sh_yaw, rel_sh_roll)))
            
            # Clamp spine rotation to human limits (X=pitch, Y=yaw/twist, Z=roll/bend)
            rot_smoothed.x = max(-0.52, min(0.87, rot_smoothed.x))  # Pitch: [-30, 50] deg
            rot_smoothed.y = max(-0.70, min(0.70, rot_smoothed.y))  # Yaw/Twist: [-40, 40] deg
            rot_smoothed.z = max(-0.61, min(0.61, rot_smoothed.z))  # Roll/Side: [-35, 35] deg
            
            # Distribute torso bending: 40% to lower spine, 60% to chest
            euler_spine = mathutils.Euler(rot_smoothed * 0.4, 'XYZ')
            euler_chest = mathutils.Euler(rot_smoothed * 0.6, 'XYZ')
            euler_full = mathutils.Euler(rot_smoothed, 'XYZ')
            
            pb_spine = rig_obj.pose.bones.get("CTRL-spine")
            if pb_spine:
                if pb_spine.rotation_mode == 'QUATERNION':
                    pb_spine.rotation_quaternion = euler_spine.to_quaternion()
                else:
                    pb_spine.rotation_euler = euler_spine
                    
                if pb_chest.rotation_mode == 'QUATERNION':
                    pb_chest.rotation_quaternion = euler_chest.to_quaternion()
                else:
                    pb_chest.rotation_euler = euler_chest
            else:
                if pb_chest.rotation_mode == 'QUATERNION':
                    pb_chest.rotation_quaternion = euler_full.to_quaternion()
                else:
                    pb_chest.rotation_euler = euler_full

        # ------------------
        # Head rotation (CTRL-head)
        # ------------------
        if track_face or track_body:
            pb_head = rig_obj.pose.bones.get("CTRL-head")
            if pb_head:
                has_head_rot = False
                R_rel = None
                
                if landmarks.face_landmarks:
                    fl = landmarks.face_landmarks.landmark
                    p_origin, R = get_face_basis(fl)
                    ref_R = getattr(calibration_data, "ref_face_R", None)
                    if ref_R is None:
                        ref_R = mathutils.Matrix.Identity(3)
                    R_rel = R @ ref_R.inverted()
                    has_head_rot = True
                elif landmarks.pose_landmarks:
                    # Fallback: estimate head rotation from pose ear and nose landmarks
                    pl = landmarks.pose_landmarks.landmark
                    wl_l_ear = to_blender_vec(pl[7])
                    wl_r_ear = to_blender_vec(pl[8])
                    wl_nose = to_blender_vec(pl[0])
                    
                    # Yaw & Roll from ears
                    ear_vec = (wl_l_ear - wl_r_ear).normalized()
                    yaw = math.atan2(ear_vec.y, ear_vec.x)
                    roll = math.atan2(ear_vec.z, ear_vec.x)
                    
                    # Pitch from nose relative to ears midpoint
                    ears_mid = (wl_l_ear + wl_r_ear) * 0.5
                    nose_dir = (wl_nose - ears_mid).normalized()
                    pitch = math.atan2(nose_dir.z, -nose_dir.y) # Nose pitch
                    
                    # Create relative rotation matrix
                    R_rel = mathutils.Euler((pitch, roll, yaw), 'XYZ').to_matrix()
                    has_head_rot = True
                    
                if has_head_rot and R_rel is not None:
                    B_rest = pb_head.bone.matrix_local.to_3x3()
                    R_local = B_rest.inverted() @ R_rel @ B_rest
                    
                    filter_h_rot = get_or_update_filter(smoothers, "head_rot", min_cut_rot, beta_rot)
                    q_local = R_local.to_quaternion()
                    q_smoothed = filter_h_rot.filter(q_local)
                    
                    if pb_head.rotation_mode == 'QUATERNION':
                        pb_head.rotation_quaternion = q_smoothed
                    elif pb_head.rotation_mode == 'AXIS_ANGLE':
                        pb_head.rotation_axis_angle = q_smoothed.to_axis_angle()
                    else:
                        pb_head.rotation_euler = q_smoothed.to_euler(pb_head.rotation_mode)

        # ------------------
        # Hands & Elbows (IK targets)
        # ------------------
        if track_hands:
            # Left Arm
            pb_hand_l = rig_obj.pose.bones.get("CTRL-hand_IK.L")
        if pb_hand_l:
            pb_upper_l = rig_obj.pose.bones.get("ORG-upper_arm.L")
            pb_forearm_l = rig_obj.pose.bones.get("ORG-forearm.L")
            
            if pb_upper_l and pb_forearm_l:
                len_uarm = pb_upper_l.bone.length
                len_farm = pb_forearm_l.bone.length
                shoulder_pose_pos = pb_upper_l.matrix.translation
                
                # Check if arm is actually visible (either by Hand landmarker or Pose wrist/elbow)
                arm_visible = (left_hand_landmarks is not None) or (pl[15].visibility > 0.15) or (pl[13].visibility > 0.15)
                
                if arm_visible:
                    # If direct hand wrist is detected (from Hand landmarker), use direct wrist tracking
                    if left_hand_landmarks is not None:
                        hand_delta = (left_wrist_coords - calibration_data.ref_l_shoulder) * scale
                        target_wrist = shoulder_pose_pos + R_world_inv @ hand_delta
                    else:
                        # Direct metric wrist tracking from Pose world landmarks
                        wrist_delta = (to_blender_vec(wl[15]) - to_blender_vec(wl[11])) * scale
                        target_wrist = shoulder_pose_pos + R_world_inv @ wrist_delta
                        
                    # Clamp max reach to arm total length to avoid IK overextension
                    arm_total = (len_uarm + len_farm) * 0.98
                    reach_vec = target_wrist - shoulder_pose_pos
                    if reach_vec.length > arm_total:
                        target_wrist = shoulder_pose_pos + reach_vec.normalized() * arm_total
                    
                    disp_arm = get_local_disp(pb_hand_l, target_wrist)
                else:
                    disp_arm = mathutils.Vector((0, 0, 0))
                
            filter_hand_l = get_or_update_filter(smoothers, "hand_l_loc", min_cut_loc, beta_loc)
            smoothed_loc = filter_hand_l.filter(disp_arm)
            pb_hand_l.location = smoothed_loc
            
            # Left Elbow (Pole Target)
            pb_elbow_l = rig_obj.pose.bones.get("CTRL-elbow_IK.L")
            if pb_elbow_l and pb_upper_l:
                # Require reasonable visibility for elbow
                elbow_visible = pl[13].visibility > 0.25 and pl[11].visibility > 0.25
                
                if arm_visible and elbow_visible:
                    # Calculate stable pole target projected outward and behind the elbow to prevent joint flipping/twisting
                    shoulder_vec = to_blender_vec(wl[11])
                    elbow_vec = to_blender_vec(wl[13])
                    wrist_vec = to_blender_vec(wl[15])
                    
                    bend_dir = elbow_vec - (shoulder_vec + wrist_vec) * 0.5
                    if bend_dir.length > 0.015:
                        v_bend = bend_dir.normalized()
                    else:
                        v_bend = mathutils.Vector((0.4, 0.3, 0.0)).normalized() # Natural lateral-backward elbow bend
                        
                    pole_world = elbow_vec + v_bend * 0.35
                    rel_elbow_arm = R_world_inv @ ((pole_world - shoulder_vec) * scale)
                    target_elbow = pb_upper_l.matrix.translation + rel_elbow_arm
                    disp_elbow = get_local_disp(pb_elbow_l, target_elbow)
                else:
                    disp_elbow = mathutils.Vector((0, 0, 0))
                filter_elbow_l = get_or_update_filter(smoothers, "elbow_l_loc", min_cut_loc, beta_loc)
                pb_elbow_l.location = filter_elbow_l.filter(disp_elbow)
            
            # Hand Rotation Tracking (Natural anatomical wrist limits, shortest quaternion path)
            if left_hand_landmarks is not None and getattr(calibration_data, "ref_l_hand_R", None) is not None:
                R_hand = get_hand_orientation(left_hand_landmarks)
                R_rel_hand = R_hand @ calibration_data.ref_l_hand_R.inverted()
                M_local = pb_hand_l.bone.matrix_local.to_3x3()
                R_local = M_local.inverted() @ R_rel_hand @ M_local
                q_local = R_local.to_quaternion()
                
                # Shortest quaternion path to prevent 180/360 degree wrist flips
                filter_hand_l_rot = get_or_update_filter(smoothers, "hand_l_rot", min_cut_rot, beta_rot)
                if filter_hand_l_rot.x_prev is not None and isinstance(filter_hand_l_rot.x_prev, mathutils.Quaternion):
                    if filter_hand_l_rot.x_prev.dot(q_local) < 0.0:
                        q_local = -q_local
                q_smoothed = filter_hand_l_rot.filter(q_local)
                
                # Clamp hand rotation strictly to realistic human wrist limits (Y=twist, X=pitch, Z=yaw)
                euler = q_smoothed.to_euler('XYZ')
                euler.x = max(-0.85, min(0.85, euler.x)) # Pitch: ±49 deg
                euler.y = max(-0.95, min(0.95, euler.y)) # Twist: ±55 deg (prevents candy-wrapper overtwisting)
                euler.z = max(-0.45, min(0.45, euler.z)) # Yaw: ±26 deg
                q_smoothed = euler.to_quaternion()
                
                if pb_hand_l.rotation_mode == 'QUATERNION':
                    pb_hand_l.rotation_quaternion = q_smoothed
                elif pb_hand_l.rotation_mode == 'AXIS_ANGLE':
                    pb_hand_l.rotation_axis_angle = q_smoothed.to_axis_angle()
                else:
                    pb_hand_l.rotation_euler = q_smoothed.to_euler(pb_hand_l.rotation_mode)
                
        # Right Arm
        pb_hand_r = rig_obj.pose.bones.get("CTRL-hand_IK.R")
        if pb_hand_r:
            pb_upper_r = rig_obj.pose.bones.get("ORG-upper_arm.R")
            pb_forearm_r = rig_obj.pose.bones.get("ORG-forearm.R")
            
            if pb_upper_r and pb_forearm_r:
                len_uarm = pb_upper_r.bone.length
                len_farm = pb_forearm_r.bone.length
                shoulder_pose_pos = pb_upper_r.matrix.translation
                
                # Check if arm is actually visible (either by Hand landmarker or Pose wrist/elbow)
                arm_visible = (right_hand_landmarks is not None) or (pl[16].visibility > 0.15) or (pl[14].visibility > 0.15)
                
                if arm_visible:
                    # If direct hand wrist is detected (from Hand landmarker), use direct wrist tracking
                    if right_hand_landmarks is not None:
                        hand_delta = (right_wrist_coords - calibration_data.ref_r_shoulder) * scale
                        target_wrist = shoulder_pose_pos + R_world_inv @ hand_delta
                    else:
                        # Direct metric wrist tracking from Pose world landmarks
                        wrist_delta = (to_blender_vec(wl[16]) - to_blender_vec(wl[12])) * scale
                        target_wrist = shoulder_pose_pos + R_world_inv @ wrist_delta

                    # Clamp max reach to arm total length to avoid IK overextension
                    arm_total = (len_uarm + len_farm) * 0.98
                    reach_vec = target_wrist - shoulder_pose_pos
                    if reach_vec.length > arm_total:
                        target_wrist = shoulder_pose_pos + reach_vec.normalized() * arm_total
                    
                    disp_arm = get_local_disp(pb_hand_r, target_wrist)
                else:
                    disp_arm = mathutils.Vector((0, 0, 0))
                
            filter_hand_r = get_or_update_filter(smoothers, "hand_r_loc", min_cut_loc, beta_loc)
            smoothed_loc = filter_hand_r.filter(disp_arm)
            pb_hand_r.location = smoothed_loc
            
            # Right Elbow (Pole Target)
            pb_elbow_r = rig_obj.pose.bones.get("CTRL-elbow_IK.R")
            if pb_elbow_r and pb_upper_r:
                # Require reasonable visibility for elbow
                elbow_visible = pl[14].visibility > 0.35 and pl[12].visibility > 0.35
                
                if arm_visible and elbow_visible:
                    # Calculate stable pole target projected outward and behind the elbow to prevent joint flipping/twisting
                    shoulder_vec = to_blender_vec(wl[12])
                    elbow_vec = to_blender_vec(wl[14])
                    wrist_vec = to_blender_vec(wl[16])
                    
                    bend_dir = elbow_vec - (shoulder_vec + wrist_vec) * 0.5
                    if bend_dir.length > 0.015:
                        v_bend = bend_dir.normalized()
                    else:
                        v_bend = mathutils.Vector((-0.4, 0.3, 0.0)).normalized() # Natural lateral-backward elbow bend
                        
                    pole_world = elbow_vec + v_bend * 0.35
                    rel_elbow_arm = R_world_inv @ ((pole_world - shoulder_vec) * scale)
                    target_elbow = pb_upper_r.matrix.translation + rel_elbow_arm
                    disp_elbow = get_local_disp(pb_elbow_r, target_elbow)
                else:
                    disp_elbow = mathutils.Vector((0, 0, 0))
                filter_elbow_r = get_or_update_filter(smoothers, "elbow_r_loc", min_cut_loc, beta_loc)
                pb_elbow_r.location = filter_elbow_r.filter(disp_elbow)
            
            # Hand Rotation Tracking (Natural anatomical wrist limits, shortest quaternion path)
            if right_hand_landmarks is not None and getattr(calibration_data, "ref_r_hand_R", None) is not None:
                R_hand = get_hand_orientation(right_hand_landmarks)
                R_rel_hand = R_hand @ calibration_data.ref_r_hand_R.inverted()
                M_local = pb_hand_r.bone.matrix_local.to_3x3()
                R_local = M_local.inverted() @ R_rel_hand @ M_local
                q_local = R_local.to_quaternion()
                
                # Shortest quaternion path to prevent 180/360 degree wrist flips
                filter_hand_r_rot = get_or_update_filter(smoothers, "hand_r_rot", min_cut_rot, beta_rot)
                if filter_hand_r_rot.x_prev is not None and isinstance(filter_hand_r_rot.x_prev, mathutils.Quaternion):
                    if filter_hand_r_rot.x_prev.dot(q_local) < 0.0:
                        q_local = -q_local
                q_smoothed = filter_hand_r_rot.filter(q_local)
                
                # Clamp hand rotation strictly to realistic human wrist limits (Y=twist, X=pitch, Z=yaw)
                euler = q_smoothed.to_euler('XYZ')
                euler.x = max(-0.85, min(0.85, euler.x)) # Pitch: ±49 deg
                euler.y = max(-0.95, min(0.95, euler.y)) # Twist: ±55 deg (prevents candy-wrapper overtwisting)
                euler.z = max(-0.45, min(0.45, euler.z)) # Yaw: ±26 deg
                q_smoothed = euler.to_quaternion()
                
                if pb_hand_r.rotation_mode == 'QUATERNION':
                    pb_hand_r.rotation_quaternion = q_smoothed
                elif pb_hand_r.rotation_mode == 'AXIS_ANGLE':
                    pb_hand_r.rotation_axis_angle = q_smoothed.to_axis_angle()
                else:
                    pb_hand_r.rotation_euler = q_smoothed.to_euler(pb_hand_r.rotation_mode)
                
        # ------------------
        # Feet & Knees (IK targets)
        # ------------------
        if pl and track_body:
            # Left Leg (Foot IK & Forward-Projected Knee Pole Target)
            pb_foot_l = rig_obj.pose.bones.get("CTRL-foot_IK.L")
        if pb_foot_l:
            leg_visible = (pl[25].visibility > 0.2 and pl[27].visibility > 0.2)
            
            if leg_visible:
                # Direct ankle displacement tracking relative to calibrated neutral ground
                disp_foot_world = (to_blender_vec(wl[27]) - calibration_data.ref_l_ankle) * scale
                disp_foot_arm = R_world_inv @ disp_foot_world
                disp_leg = pb_foot_l.bone.matrix_local.to_3x3().inverted() @ disp_foot_arm
            else:
                disp_leg = mathutils.Vector((0, 0, 0))
                
            filter_foot_l = get_or_update_filter(smoothers, "foot_l_loc", min_cut_loc, beta_loc)
            pb_foot_l.location = filter_foot_l.filter(disp_leg)
            
            # Left Foot Rotation Tracking (Ankle pitch/roll/yaw clamped to human limits)
            if leg_visible and pl[31].visibility > 0.2 and pl[29].visibility > 0.2:
                heel = to_blender_vec(wl[29])
                toe = to_blender_vec(wl[31])
                ankle = to_blender_vec(wl[27])
                
                dir_foot = (toe - heel).normalized()
                up_foot = ((ankle - heel).cross(dir_foot)).cross(dir_foot).normalized()
                across_foot = up_foot.cross(dir_foot).normalized()
                R_foot = mathutils.Matrix((across_foot, up_foot, dir_foot)).transposed()
                
                ref_f = getattr(calibration_data, "ref_l_foot_R", None)
                if ref_f is None:
                    calibration_data.ref_l_foot_R = R_foot.copy()
                    ref_f = R_foot
                    
                R_rel_foot = R_foot @ ref_f.inverted()
                M_local = pb_foot_l.bone.matrix_local.to_3x3()
                R_local = M_local.inverted() @ R_rel_foot @ M_local
                q_local = R_local.to_quaternion()
                
                filter_foot_l_rot = get_or_update_filter(smoothers, "foot_l_rot", min_cut_rot, beta_rot)
                if filter_foot_l_rot.x_prev is not None and isinstance(filter_foot_l_rot.x_prev, mathutils.Quaternion):
                    if filter_foot_l_rot.x_prev.dot(q_local) < 0.0:
                        q_local = -q_local
                q_smoothed = filter_foot_l_rot.filter(q_local)
                
                euler = q_smoothed.to_euler('XYZ')
                euler.x = max(-0.65, min(0.70, euler.x)) # Pitch (Plantar/Dorsi): [-37, 40] deg
                euler.y = max(-0.28, min(0.28, euler.y)) # Roll (Inversion/Eversion): [-16, 16] deg
                euler.z = max(-0.35, min(0.35, euler.z)) # Yaw: [-20, 20] deg
                q_smoothed = euler.to_quaternion()
                
                if pb_foot_l.rotation_mode == 'QUATERNION':
                    pb_foot_l.rotation_quaternion = q_smoothed
                else:
                    pb_foot_l.rotation_euler = q_smoothed.to_euler(pb_foot_l.rotation_mode)
            
            # Left Knee (Pole Target - Strictly projected forward in front of leg)
            pb_knee_l = rig_obj.pose.bones.get("CTRL-knee_IK.L")
            if pb_knee_l:
                if leg_visible:
                    hip_vec = to_blender_vec(wl[23])
                    knee_vec = to_blender_vec(wl[25])
                    ankle_vec = to_blender_vec(wl[27])
                    
                    bend_dir = knee_vec - (hip_vec + ankle_vec) * 0.5
                    if bend_dir.length > 0.015:
                        v_bend = bend_dir.normalized()
                    else:
                        v_bend = mathutils.Vector((0.0, -0.4, 0.0)).normalized() # Natural forward knee bend
                        
                    # Guarantee forward component strictly points in front of the character
                    if v_bend.y > -0.05:
                        v_bend.y = -0.35
                        v_bend = v_bend.normalized()
                        
                    pole_world = knee_vec + v_bend * 0.35
                    rel_knee_arm = R_world_inv @ ((pole_world - hip_vec) * scale)
                    target_knee = rig_obj.pose.bones.get("ORG-thigh.L").matrix.translation + rel_knee_arm if rig_obj.pose.bones.get("ORG-thigh.L") else knee_vec
                    disp_knee = get_local_disp(pb_knee_l, target_knee)
                else:
                    disp_knee = mathutils.Vector((0, 0, 0))
                filter_knee_l = get_or_update_filter(smoothers, "knee_l_loc", min_cut_loc, beta_loc)
                pb_knee_l.location = filter_knee_l.filter(disp_knee)
            
        # Right Leg (Foot IK & Forward-Projected Knee Pole Target)
        pb_foot_r = rig_obj.pose.bones.get("CTRL-foot_IK.R")
        if pb_foot_r:
            leg_visible = (pl[26].visibility > 0.2 and pl[28].visibility > 0.2)
            
            if leg_visible:
                # Direct ankle displacement tracking relative to calibrated neutral ground
                disp_foot_world = (to_blender_vec(wl[28]) - calibration_data.ref_r_ankle) * scale
                disp_foot_arm = R_world_inv @ disp_foot_world
                disp_leg = pb_foot_r.bone.matrix_local.to_3x3().inverted() @ disp_foot_arm
            else:
                disp_leg = mathutils.Vector((0, 0, 0))
                
            filter_foot_r = get_or_update_filter(smoothers, "foot_r_loc", min_cut_loc, beta_loc)
            pb_foot_r.location = filter_foot_r.filter(disp_leg)
            
            # Right Foot Rotation Tracking (Ankle pitch/roll/yaw clamped to human limits)
            if leg_visible and pl[32].visibility > 0.2 and pl[30].visibility > 0.2:
                heel = to_blender_vec(wl[30])
                toe = to_blender_vec(wl[32])
                ankle = to_blender_vec(wl[28])
                
                dir_foot = (toe - heel).normalized()
                up_foot = ((ankle - heel).cross(dir_foot)).cross(dir_foot).normalized()
                across_foot = up_foot.cross(dir_foot).normalized()
                R_foot = mathutils.Matrix((across_foot, up_foot, dir_foot)).transposed()
                
                ref_f = getattr(calibration_data, "ref_r_foot_R", None)
                if ref_f is None:
                    calibration_data.ref_r_foot_R = R_foot.copy()
                    ref_f = R_foot
                    
                R_rel_foot = R_foot @ ref_f.inverted()
                M_local = pb_foot_r.bone.matrix_local.to_3x3()
                R_local = M_local.inverted() @ R_rel_foot @ M_local
                q_local = R_local.to_quaternion()
                
                filter_foot_r_rot = get_or_update_filter(smoothers, "foot_r_rot", min_cut_rot, beta_rot)
                if filter_foot_r_rot.x_prev is not None and isinstance(filter_foot_r_rot.x_prev, mathutils.Quaternion):
                    if filter_foot_r_rot.x_prev.dot(q_local) < 0.0:
                        q_local = -q_local
                q_smoothed = filter_foot_r_rot.filter(q_local)
                
                euler = q_smoothed.to_euler('XYZ')
                euler.x = max(-0.65, min(0.70, euler.x)) # Pitch (Plantar/Dorsi): [-37, 40] deg
                euler.y = max(-0.28, min(0.28, euler.y)) # Roll (Inversion/Eversion): [-16, 16] deg
                euler.z = max(-0.35, min(0.35, euler.z)) # Yaw: [-20, 20] deg
                q_smoothed = euler.to_quaternion()
                
                if pb_foot_r.rotation_mode == 'QUATERNION':
                    pb_foot_r.rotation_quaternion = q_smoothed
                else:
                    pb_foot_r.rotation_euler = q_smoothed.to_euler(pb_foot_r.rotation_mode)
            
            # Right Knee (Pole Target - Strictly projected forward in front of leg)
            pb_knee_r = rig_obj.pose.bones.get("CTRL-knee_IK.R")
            if pb_knee_r:
                if leg_visible:
                    hip_vec = to_blender_vec(wl[24])
                    knee_vec = to_blender_vec(wl[26])
                    ankle_vec = to_blender_vec(wl[28])
                    
                    bend_dir = knee_vec - (hip_vec + ankle_vec) * 0.5
                    if bend_dir.length > 0.015:
                        v_bend = bend_dir.normalized()
                    else:
                        v_bend = mathutils.Vector((0.0, -0.4, 0.0)).normalized() # Natural forward knee bend
                        
                    # Guarantee forward component strictly points in front of the character
                    if v_bend.y > -0.05:
                        v_bend.y = -0.35
                        v_bend = v_bend.normalized()
                        
                    pole_world = knee_vec + v_bend * 0.35
                    rel_knee_arm = R_world_inv @ ((pole_world - hip_vec) * scale)
                    target_knee = rig_obj.pose.bones.get("ORG-thigh.R").matrix.translation + rel_knee_arm if rig_obj.pose.bones.get("ORG-thigh.R") else knee_vec
                    disp_knee = get_local_disp(pb_knee_r, target_knee)
                else:
                    disp_knee = mathutils.Vector((0, 0, 0))
                filter_knee_r = get_or_update_filter(smoothers, "knee_r_loc", min_cut_loc, beta_loc)
                pb_knee_r.location = filter_knee_r.filter(disp_knee)
  
    # ------------------
    # 2. Facial Mocap
    # ------------------
    if landmarks.face_landmarks and track_face:
        fl = landmarks.face_landmarks.landmark
        p_origin, R = get_face_basis(fl)
        R_inv = R.inverted()
        curr_face_size = (to_blender_vec(fl[356]) - to_blender_vec(fl[127])).length
        ref_face_size = getattr(calibration_data, "ref_face_size", 1.0)
        dynamic_face_scale = ref_face_size / max(0.01, curr_face_size)
        
        # Head-Pitch & Tilt Invariant Lip Gap Tracking in Local Head Space
        p_13_local = R_inv @ (to_blender_vec(fl[13]) - p_origin)
        p_14_local = R_inv @ (to_blender_vec(fl[14]) - p_origin)
        
        # Local vertical distance between upper and lower lips (completely immune to head tilting/nodding)
        local_lip_gap = max(0.0, p_13_local.z - p_14_local.z)
        
        # Track neutral baseline for lips closed
        if local_lip_gap < getattr(calibration_data, "min_local_lip_gap", 999.0) and local_lip_gap > 0.001:
            calibration_data.min_local_lip_gap = local_lip_gap
        ref_local_gap = getattr(calibration_data, "min_local_lip_gap", 0.004)
        
        # True mouth opening: ONLY increases when mouth physically opens, NEVER when head tilts up/down
        lower_lip_drop = max(0.0, (local_lip_gap - ref_local_gap) / max(0.01, curr_face_size * 0.14))
        
        jaw_mult = scene.hrg_mocap_jaw_mult
        speech_opening = lower_lip_drop * 4.5 * face_mult * jaw_mult
        
        # Speech-optimized low latency One Euro Filter
        min_cut_jaw = max(0.08, 2.5 * (1.0 - ui_smooth))
        beta_jaw = 0.35 * (1.0 - ui_smooth)
        filter_jaw = get_or_update_filter(smoothers, "jaw_open", min_cut_jaw, beta_jaw)
        smoothed_jaw = filter_jaw.filter(speech_opening)
        
        pb_jaw = rig_obj.pose.bones.get("CTRL-jaw")
        pb_org = rig_obj.pose.bones.get("ORG-jaw")
        pb_def = rig_obj.pose.bones.get("DEF-jaw")
        
        # Temp debug file logging
        try:
            with open("f:/blenderaddon/mocap_debug.log", "a") as f_log:
                ctrl_rot = pb_jaw.rotation_euler[0] if pb_jaw else -9.0
                org_rot = pb_org.rotation_euler[0] if pb_org else -9.0
                def_rot = pb_def.rotation_euler[0] if pb_def else -9.0
                f_log.write(f"JAW_DEBUG: lower_lip_drop={lower_lip_drop:.4f} | speech_opening={speech_opening:.4f} | smoothed={smoothed_jaw:.4f}\n")
        except Exception as log_err:
            print("Log error:", log_err)
        
        try:
            rig_obj.hrg_jaw_open = min(1.0, max(0.0, smoothed_jaw))
        except Exception:
            pass
        
        norm_jaw = min(1.0, max(0.0, smoothed_jaw))
        if pb_jaw:
            if pb_jaw.rotation_mode != 'XYZ':
                pb_jaw.rotation_mode = 'XYZ'
            # Lock jaw hinge location strictly at (0, 0, 0) so it never shifts off its anatomical pivot
            pb_jaw.location = mathutils.Vector((0.0, 0.0, 0.0))
            # Anatomical human rotation: strictly downwards (positive X) around TMJ hinge
            pb_jaw.rotation_euler[0] = max(0.0, min(0.55, smoothed_jaw * 1.5))
            pb_jaw.rotation_euler[1] = 0.0
            pb_jaw.rotation_euler[2] = 0.0
            
        # Drive Lip Controllers directly for subtle phonetic parting
        pb_lip_low = rig_obj.pose.bones.get("CTRL-lip.lower")
        if pb_lip_low:
            filter_lip_low = get_or_update_filter(smoothers, "lip_lower_loc", min_cut_jaw, beta_jaw)
            target_drop = mathutils.Vector((0.0, 0.0, -0.010 * norm_jaw * face_mult))
            pb_lip_low.location = filter_lip_low.filter(target_drop)
            
        pb_lip_up = rig_obj.pose.bones.get("CTRL-lip.upper")
        if pb_lip_up:
            filter_lip_up = get_or_update_filter(smoothers, "lip_upper_loc", min_cut_jaw, beta_jaw)
            target_up = mathutils.Vector((0.0, 0.0, 0.004 * norm_jaw * face_mult))
            pb_lip_up.location = filter_lip_up.filter(target_up)
            
        # B. Eye Blinking -> Mapped to hrg_eye_blink_l / hrg_eye_blink_r properties
        ear_l_w = math.sqrt((fl[33].x - fl[133].x)**2 + (fl[33].y - fl[133].y)**2)
        ear_l_h = math.sqrt((fl[159].x - fl[145].x)**2 + (fl[159].y - fl[145].y)**2)
        ear_l = ear_l_h / max(0.001, ear_l_w)
        
        ear_r_w = math.sqrt((fl[362].x - fl[263].x)**2 + (fl[362].y - fl[263].y)**2)
        ear_r_h = math.sqrt((fl[386].x - fl[374].x)**2 + (fl[386].y - fl[374].y)**2)
        ear_r = ear_r_h / max(0.001, ear_r_w)
        
        blink_mult = scene.hrg_mocap_blink_mult
        blink_l = min(1.0, max(0.0, (0.35 - ear_l) / 0.20)) * blink_mult
        blink_r = min(1.0, max(0.0, (0.35 - ear_r) / 0.20)) * blink_mult
        
        # Use a highly responsive/fast blink filter to eliminate lag and track fast blinks accurately
        min_cut_blink = max(0.05, 2.0 * (1.0 - ui_smooth))
        beta_blink = 0.3 * (1.0 - ui_smooth)
        
        filter_blink_l = get_or_update_filter(smoothers, "blink_l", min_cut_blink, beta_blink)
        filter_blink_r = get_or_update_filter(smoothers, "blink_r", min_cut_blink, beta_blink)
        smoothed_blink_l = filter_blink_l.filter(blink_l)
        smoothed_blink_r = filter_blink_r.filter(blink_r)
        
        try:
            rig_obj.hrg_eye_blink_l = smoothed_blink_l
            rig_obj.hrg_eye_blink_r = smoothed_blink_r
        except Exception:
            pass
            
        # Check if mesh has native blink blendshapes (e.g. CC4, Metahuman, ARKit)
        has_blink_keys = False
        for child in rig_obj.children:
            if child.type == 'MESH' and child.data.shape_keys:
                kb = child.data.shape_keys.key_blocks
                if "Eye_Blink_L" in kb or "eyeBlinkLeft" in kb or "EyeBlink_L" in kb or "A03_Eye_Blink_L" in kb:
                    has_blink_keys = True
                    break
                    
        # Drive the 3-bone curved eyelids rotation (only apply full bone rotation if no native shape keys exist)
        bone_rot_weight = 0.0 if has_blink_keys else 1.0
        for side, blink_val in [(".L", smoothed_blink_l), (".R", smoothed_blink_r)]:
            # Upper eyelids (01, 02, 03) - rotate downwards to meet lower lid
            for part, coeff in [("eyelid.upper.01", -0.26), ("eyelid.upper.02", -0.38), ("eyelid.upper.03", -0.30), ("eyelid.upper", -0.38)]:
                org_up = rig_obj.pose.bones.get(f"ORG-{part}{side}")
                if org_up:
                    if org_up.rotation_mode != 'XYZ':
                        org_up.rotation_mode = 'XYZ'
                    org_up.rotation_euler[0] = min(0.0, coeff * blink_val * bone_rot_weight)
                    
            # Lower eyelids (01, 02, 03) - rotate subtly UPWARDS
            for part, coeff in [("eyelid.lower.01", 0.07), ("eyelid.lower.02", 0.12), ("eyelid.lower.03", 0.08), ("eyelid.lower", 0.12)]:
                org_low = rig_obj.pose.bones.get(f"ORG-{part}{side}")
                if org_low:
                    if org_low.rotation_mode != 'XYZ':
                        org_low.rotation_mode = 'XYZ'
                    org_low.rotation_euler[0] = max(0.0, coeff * blink_val * bone_rot_weight)
        
        # C. Eyeballs tracking -> Move CTRL-eyes_look target
        pb_eyes_look = rig_obj.pose.bones.get("CTRL-eyes_look")
        if pb_eyes_look:
            left_center = (to_blender_vec(fl[33]) + to_blender_vec(fl[133])) * 0.5
            pupil_l_offset = to_blender_vec(fl[468]) - left_center
            
            right_center = (to_blender_vec(fl[362]) + to_blender_vec(fl[263])) * 0.5
            pupil_r_offset = to_blender_vec(fl[473]) - right_center
            
            avg_pupil_offset = (pupil_l_offset + pupil_r_offset) * 0.5
            
            target_look = mathutils.Vector((avg_pupil_offset.x * 2.0 * face_mult, 0.0, avg_pupil_offset.z * 2.0 * face_mult))
            filter_eyes_look = get_or_update_filter(smoothers, "eyes_look", min_cut_face, beta_face)
            pb_eyes_look.location = filter_eyes_look.filter(target_look)
            
            pb_eyes_look["eye_close.L"] = smoothed_blink_l
            pb_eyes_look["eye_close.R"] = smoothed_blink_r
            
        # D. Eyebrow raise calculations
        curr_dist_l = math.sqrt((fl[70].x - fl[159].x)**2 + (fl[70].y - fl[159].y)**2) / max(0.001, curr_face_size)
        curr_dist_r = math.sqrt((fl[300].x - fl[386].x)**2 + (fl[300].y - fl[386].y)**2) / max(0.001, curr_face_size)
        
        # Track dynamic baselines (running minimum of eyebrow distances) with sanity lower limit (0.08)
        if curr_dist_l < getattr(calibration_data, "min_brow_dist_l", 999.0) and curr_dist_l > 0.08:
            calibration_data.min_brow_dist_l = curr_dist_l
        if curr_dist_r < getattr(calibration_data, "min_brow_dist_r", 999.0) and curr_dist_r > 0.08:
            calibration_data.min_brow_dist_r = curr_dist_r
            
        ref_dist_l = getattr(calibration_data, "min_brow_dist_l", 0.15)
        ref_dist_r = getattr(calibration_data, "min_brow_dist_r", 0.15)
        
        brow_mult = scene.hrg_mocap_brow_mult
        brow_raise_l = (curr_dist_l - ref_dist_l) / 0.035 * face_mult * brow_mult
        brow_raise_r = (curr_dist_r - ref_dist_r) / 0.035 * face_mult * brow_mult
        
        # Clamp raise between 0.0 (relaxed) and 1.0 (maximum natural raise) to prevent excessive stretching
        brow_raise_l = max(0.0, min(1.0, brow_raise_l))
        brow_raise_r = max(0.0, min(1.0, brow_raise_r))
        
        filter_brow_l = get_or_update_filter(smoothers, "brow_raise_l", min_cut_face, beta_face)
        filter_brow_r = get_or_update_filter(smoothers, "brow_raise_r", min_cut_face, beta_face)
        
        try:
            rig_obj.hrg_brow_raise_l = filter_brow_l.filter(brow_raise_l)
            rig_obj.hrg_brow_raise_r = filter_brow_r.filter(brow_raise_r)
        except Exception:
            pass
            
        # E. Mouth Smile / Frown calculations
        curr_lc_local = R_inv @ (to_blender_vec(fl[291]) - p_origin)
        curr_rc_local = R_inv @ (to_blender_vec(fl[61]) - p_origin)
        
        disp_z_l = curr_lc_local.z - getattr(calibration_data, "ref_mouth_corner_z_l", 0.0)
        disp_z_r = curr_rc_local.z - getattr(calibration_data, "ref_mouth_corner_z_r", 0.0)
        
        norm_disp_z_l = disp_z_l / max(0.01, curr_face_size)
        norm_disp_z_r = disp_z_r / max(0.01, curr_face_size)
        
        mouth_mult = scene.hrg_mocap_mouth_mult
        smile_l = norm_disp_z_l / 0.035 * face_mult * mouth_mult
        smile_r = norm_disp_z_r / 0.035 * face_mult * mouth_mult
        
        smile_l = max(-1.0, min(1.0, smile_l))
        smile_r = max(-1.0, min(1.0, smile_r))
        
        filter_smile_l = get_or_update_filter(smoothers, "smile_l", min_cut_face, beta_face)
        filter_smile_r = get_or_update_filter(smoothers, "smile_r", min_cut_face, beta_face)
        
        try:
            rig_obj.hrg_mouth_smile_l = filter_smile_l.filter(smile_l)
            rig_obj.hrg_mouth_smile_r = filter_smile_r.filter(smile_r)
        except Exception:
            pass
            
        # Lip Pucker calculation (distance between mouth corners compared to neutral)
        curr_corner_dist = (curr_lc_local - curr_rc_local).length / max(0.01, curr_face_size)
        ref_corner_dist = getattr(calibration_data, "ref_mouth_width", 0.35)
        pucker_val = max(0.0, min(1.0, (ref_corner_dist - curr_corner_dist) / 0.08 * face_mult))
            
        # Drive child mesh shape keys for CC4, Metahuman, ARKit, ReadyPlayerMe, etc.
        jaw_norm = min(1.0, max(0.0, smoothed_jaw))
        smile_l_norm = min(1.0, max(0.0, smile_l))
        smile_r_norm = min(1.0, max(0.0, smile_r))
        blink_l_norm = min(1.0, max(0.0, smoothed_blink_l))
        blink_r_norm = min(1.0, max(0.0, smoothed_blink_r))
        pucker_norm = min(1.0, max(0.0, pucker_val))
        
        for child in rig_obj.children:
            if child.type == 'MESH' and child.data.shape_keys:
                kb = child.data.shape_keys.key_blocks
                # Mouth / Jaw Open shape keys
                for key_name in ["Mouth_Open", "Jaw_Open", "mouthOpen", "jawOpen", "MouthOpen", "JawOpen", "A01_Mouth_Open", "v_aa", "Mouth_Drop_Lower", "CC_Base_Body_Mouth_Open"]:
                    if key_name in kb:
                        kb[key_name].value = jaw_norm
                        
                # Smile shape keys
                for key_name in ["Mouth_Smile_L", "mouthSmileLeft", "MouthSmile_L", "A02_Mouth_Smile_L"]:
                    if key_name in kb:
                        kb[key_name].value = smile_l_norm
                for key_name in ["Mouth_Smile_R", "mouthSmileRight", "MouthSmile_R", "A02_Mouth_Smile_R"]:
                    if key_name in kb:
                        kb[key_name].value = smile_r_norm
                        
                # Blink shape keys
                for key_name in ["Eye_Blink_L", "eyeBlinkLeft", "EyeBlink_L", "A03_Eye_Blink_L"]:
                    if key_name in kb:
                        kb[key_name].value = blink_l_norm
                for key_name in ["Eye_Blink_R", "eyeBlinkRight", "EyeBlink_R", "A03_Eye_Blink_R"]:
                    if key_name in kb:
                        kb[key_name].value = blink_r_norm
 
        # F. Direct face bone offsets in face local coordinate space (using ORG- bones)
        if scene.hrg_mocap_detailed_face:
            for name, idx in FACE_BONE_LANDMARKS.items():
                pb_face = rig_obj.pose.bones.get(name)
                # Skip eyelids as they are driven exclusively by the rotation drivers
                if "eyelid" in name:
                    if pb_face:
                        pb_face.location = (0, 0, 0)
                    continue
                if pb_face and name in calibration_data.face_ref_landmarks:
                    p_lm = to_blender_vec(fl[idx])
                    curr_local = R_inv @ (p_lm - p_origin)
                    scaled_curr_local = curr_local * dynamic_face_scale
                    ref_local = calibration_data.face_ref_landmarks[name]
                    
                    disp = (scaled_curr_local - ref_local) * face_mult
                    
                    # For lip bones:
                    if "CTRL-lip" in name:
                        disp.x = 0.0  # Center lips only move vertically
                        if "upper" in name:
                            disp.z = max(0.0, min(0.004, disp.z))
                        else:
                            # Scale the lower lip drop based on how open the jaw is to prevent it dropping when mouth is closed
                            jaw_open_factor = getattr(rig_obj, "hrg_jaw_open", 0.0)
                            max_drop = -0.008 - 0.024 * jaw_open_factor
                            disp.z = max(max_drop, min(0.0, disp.z))
                    elif "ORG-lip" in name:
                        # Mute location drivers during live mocap to allow webcam tracking
                        if "lip.corner" in name:
                            if pb_face.animation_data:
                                for fc in pb_face.animation_data.drivers:
                                    if fc.data_path.startswith("location"):
                                        fc.mute = True
                        # Restrict inward horizontal movement to ZERO to completely prevent neutral shrinking
                        if name.endswith(".L"):
                            disp.x = max(0.0, min(0.015, disp.x))
                        else:
                            disp.x = min(0.0, max(-0.015, disp.x))
                        disp.z = max(-0.005, min(0.008, disp.z))
                    
                    # Zero out depth translation (Y axis) to eliminate in/out jitter mesh distortion
                    disp.y = 0.0
                    
                    # Apply safety clamps to prevent face bones from stretching unlimitedly
                    max_limit = 0.012  # default 1.2 cm safety limit
                    if "nose" in name:
                        max_limit = 0.001  # Nose is rigid
                    elif "eyebrow" in name:
                        max_limit = 0.018  # Eyebrows are more expressive (1.8 cm)
                        # Scale eyebrow displacement by brow sensitivity multiplier
                        disp.z *= brow_mult
                        disp.x *= brow_mult
                        # Restrict eyebrow Z displacement to prevent climbing too high or covering the eye (max 8 mm up, 3 mm down)
                        disp.z = max(-0.003, min(0.008, disp.z))
                        disp.x = max(-0.003, min(0.003, disp.x))
                    elif "eyelid" in name:
                        max_limit = 0.005
                    elif "lip" in name:
                        max_limit = 0.035
                    elif "cheek" in name:
                        max_limit = 0.006
                    elif "chin" in name:
                        max_limit = 0.010
 
                    disp.x = max(-max_limit, min(max_limit, disp.x))
                    disp.y = max(-max_limit, min(max_limit, disp.y))
                    disp.z = max(-max_limit, min(max_limit, disp.z))
 
                    # Transform face-local displacement into bone's local space using constant neutral face rotation
                    ref_R = getattr(calibration_data, "ref_face_R", None)
                    if ref_R is None:
                        ref_R = mathutils.Matrix.Identity(3)
                    disp_world = ref_R @ disp
                    disp_arm = R_world_inv @ disp_world
                    disp_local = pb_face.bone.matrix_local.to_3x3().inverted() @ disp_arm
                    
                    filter_face_bone = get_or_update_filter(smoothers, f"face_{name}", min_cut_face, beta_face)
                    pb_face.location = filter_face_bone.filter(disp_local)
        else:
            # Reset detailed skin bones to rest state (excluding lip controls which are driven by jaw)
            for name in FACE_BONE_LANDMARKS.keys():
                if "lip" in name:
                    continue
                pb_face = rig_obj.pose.bones.get(name)
                if pb_face:
                    pb_face.location = (0, 0, 0)
                    if pb_face.animation_data:
                        for fc in pb_face.animation_data.drivers:
                            if fc.data_path.startswith("location"):
                                fc.mute = False

    # ------------------
    # 3. Hand Fingers Mocap
    # ------------------
    if track_hands and hand_result and hand_result.hand_landmarks:
        for hand_idx, landmarks_list in enumerate(hand_result.hand_landmarks):
            handedness = hand_result.handedness[hand_idx][0].category_name
            is_left = (handedness == "Left")
            side = ".L" if is_left else ".R"
            
            pb_fingers = rig_obj.pose.bones.get(f"CTRL-fingers{side}")
            if pb_fingers:
                def dist(p1, p2):
                    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
                
                finger_joints = {
                    "thumb":  (2, 3, 4),
                    "index":  (5, 6, 7, 8),
                    "middle": (9, 10, 11, 12),
                    "ring":   (13, 14, 15, 16),
                    "pinky":  (17, 18, 19, 20)
                }
                
                curls = {}
                for name, joints in finger_joints.items():
                    mcp = landmarks_list[joints[0]]
                    tip = landmarks_list[joints[-1]]
                    
                    d_current = dist(mcp, tip)
                    d_max = 0.0
                    for i in range(len(joints)-1):
                        d_max += dist(landmarks_list[joints[i]], landmarks_list[joints[i+1]])
                        
                    curl = 1.0 - (d_current / max(0.01, d_max))
                    curl = min(1.0, max(0.0, curl))
                    curls[name] = curl
                
                # Apply finger curls with corrected smoothing direction
                alpha_val = max(0.01, 1.0 - ui_smooth)
                for name in ["thumb", "index", "middle", "ring", "pinky"]:
                    smooth_key = f"finger_{name}{side}"
                    if smooth_key not in smoothers:
                        smoothers[smooth_key] = ExponentialSmoother(alpha_val)
                    else:
                        smoothers[smooth_key].alpha = alpha_val
                    val_smoothed = smoothers[smooth_key].filter(curls[name])
                    
                    try:
                        setattr(pb_fingers, f"hrg_{name}", val_smoothed)
                    except:
                        pass
                    pb_fingers[f"hrg_{name}"] = val_smoothed
                
                # Grasp master is average of all fingers curl
                grasp_val = sum(curls.values()) / len(curls)
                smooth_grasp_key = f"finger_grasp{side}"
                if smooth_grasp_key not in smoothers:
                    smoothers[smooth_grasp_key] = ExponentialSmoother(alpha_val)
                else:
                    smoothers[smooth_grasp_key].alpha = alpha_val
                smoothed_grasp = smoothers[smooth_grasp_key].filter(grasp_val)
                try:
                    pb_fingers.hrg_grasp = smoothed_grasp
                except:
                    pass
                pb_fingers["hrg_grasp"] = smoothed_grasp

def keyframe_driven_bones(rig_obj, frame_idx):
    """Inserts keyframes on all the active motion-captured bones on the rig."""
    # List of controllers driven
    bones_to_key = [
        "CTRL-pelvis", "CTRL-spine", "CTRL-spine.003", "CTRL-neck", "CTRL-head", "CTRL-eyes_look", "CTRL-jaw",
        "CTRL-hand_IK.L", "CTRL-elbow_IK.L", "CTRL-hand_IK.R", "CTRL-elbow_IK.R",
        "CTRL-foot_IK.L", "CTRL-knee_IK.L", "CTRL-foot_IK.R", "CTRL-knee_IK.R"
    ] + list(FACE_BONE_LANDMARKS.keys())
    
    # Keyframe bones
    for bname in bones_to_key:
        pb = rig_obj.pose.bones.get(bname)
        if pb:
            pb.keyframe_insert(data_path="location", frame=frame_idx)
            if pb.rotation_mode == 'QUATERNION':
                pb.keyframe_insert(data_path="rotation_quaternion", frame=frame_idx)
            elif pb.rotation_mode == 'AXIS_ANGLE':
                pb.keyframe_insert(data_path="rotation_axis_angle", frame=frame_idx)
            else:
                pb.keyframe_insert(data_path="rotation_euler", frame=frame_idx)
            
    # Keyframe eye blink & jaw open properties on armature
    try:
        rig_obj.keyframe_insert(data_path="hrg_eye_blink_l", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_eye_blink_r", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_jaw_open", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_brow_raise_l", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_brow_raise_r", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_mouth_smile_l", frame=frame_idx)
        rig_obj.keyframe_insert(data_path="hrg_mouth_smile_r", frame=frame_idx)
    except:
        pass
        
    # Keyframe finger custom properties
    for side in [".L", ".R"]:
        pb_fingers = rig_obj.pose.bones.get(f"CTRL-fingers{side}")
        if pb_fingers:
            for prop in ["grasp", "thumb", "index", "middle", "ring", "pinky"]:
                try:
                    pb_fingers.keyframe_insert(data_path=f'["hrg_{prop}"]', frame=frame_idx)
                except:
                    pass
    rig_obj.keyframe_insert(data_path="hrg_eye_blink_r", frame=frame_idx)

# -------------------------------------------------------------
# Operator 1: Live Webcam Motion Capture (Modal Timer driven)
# -------------------------------------------------------------
class MOCAP_OT_live_capture(bpy.types.Operator):
    """Live camera motion capture stream directly driving the rig."""
    bl_idname = "mocap.live_capture"
    bl_label = "Live Mocap Stream"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    _cap = None
    _pose_landmarker = None
    _face_landmarker = None
    _hand_landmarker = None
    _smoothers = {}
    _fps_time = 0
    _window_initialized = False
    _frame_count = 0
    
    _is_external = False
    _backend_proc = None
    _sock = None
    
    def modal(self, context, event):
        scene = context.scene
        
        # Stop check via property or ESC key
        if not scene.hrg_mocap_active or event.type in {'ESC'}:
            self.cancel(context)
            return {'FINISHED'}
            
        if event.type == 'TIMER':
            try:
                rig_obj = context.active_object
                if not rig_obj or rig_obj.type != 'ARMATURE':
                    self.cancel(context)
                    return {'CANCELLED'}
                    
                if self._is_external:
                    # Non-blocking UDP packet retrieval
                    import json
                    last_packet = None
                    while True:
                        try:
                            data, addr = self._sock.recvfrom(65536)
                            last_packet = data
                        except BlockingIOError:
                            break
                        except Exception as e:
                            print("[Mocap Addon] Socket read error:", e)
                            break
                            
                    if last_packet is not None:
                        try:
                            payload = json.loads(last_packet.decode("utf-8"))
                        except Exception as parse_err:
                            print("[Mocap Addon] JSON parse error:", parse_err)
                            payload = None
                            
                        if payload:
                            # Reconstruct mock landmarks from JSON payload
                            class MockLandmark:
                                def __init__(self, x, y, z, visibility=1.0):
                                    self.x = x
                                    self.y = y
                                    self.z = z
                                    self.visibility = visibility
                                    
                            class MockLandmarkList:
                                def __init__(self, lms):
                                    self.landmark = lms
                                    
                            pose_lms = MockLandmarkList([MockLandmark(l["x"], l["y"], l["z"], l["visibility"]) for l in payload["pose_landmarks"]]) if payload["pose_landmarks"] else None
                            pose_wl_lms = MockLandmarkList([MockLandmark(l["x"], l["y"], l["z"], l["visibility"]) for l in payload["pose_world_landmarks"]]) if payload["pose_world_landmarks"] else None
                            face_lms = MockLandmarkList([MockLandmark(l["x"], l["y"], l["z"]) for l in payload["face_landmarks"]]) if payload["face_landmarks"] else None
                            l_hand_lms = MockLandmarkList([MockLandmark(l["x"], l["y"], l["z"]) for l in payload["left_hand_landmarks"]]) if payload.get("left_hand_landmarks") else None
                            r_hand_lms = MockLandmarkList([MockLandmark(l["x"], l["y"], l["z"]) for l in payload["right_hand_landmarks"]]) if payload.get("right_hand_landmarks") else None
                            
                            class UnifiedHolisticLandmarks:
                                def __init__(self, p_lms, p_wl_lms, f_lms, l_hand, r_hand):
                                    self.pose_landmarks = p_lms
                                    self.pose_world_landmarks = p_wl_lms
                                    self.face_landmarks = f_lms
                                    self.left_hand_landmarks = l_hand
                                    self.right_hand_landmarks = r_hand
                                    
                            results = UnifiedHolisticLandmarks(pose_lms, pose_wl_lms, face_lms, l_hand_lms, r_hand_lms)
                            
                            # Hands
                            class MockHandedness:
                                def __init__(self, category_name):
                                    self.category_name = category_name
                                    
                            class MockHandResult:
                                def __init__(self, hand_lms, handedness):
                                    self.hand_landmarks = hand_lms
                                    self.handedness = [[MockHandedness(h[0]["category_name"])] for h in handedness] if handedness else None
                                    
                            hand_lms = [[MockLandmark(l["x"], l["y"], l["z"]) for l in hand] for hand in payload["hand_landmarks"]] if payload.get("hand_landmarks") else None
                            hand_result = MockHandResult(hand_lms, payload.get("handedness"))
                            
                            # Apply to rig
                            apply_mocap_to_rig(results, hand_result, rig_obj, scene, self._smoothers)
                            
                            if scene.hrg_mocap_record:
                                curr_frame = scene.frame_current
                                keyframe_driven_bones(rig_obj, curr_frame)
                                scene.frame_set(curr_frame + 1)
                                
                            context.view_layer.update()
                            
                            # Update FPS counter
                            self._frame_count += 1
                            now = time.time()
                            if now - self._fps_time >= 1.0:
                                fps = self._frame_count / (now - self._fps_time)
                                context.workspace.status_text_set_internal(f"Mocap active: {fps:.1f} FPS (External Backend)")
                                scene.hrg_mocap_streaming_fps = fps
                                self._frame_count = 0
                                self._fps_time = now
                                
                else:
                    # Internal Mode setup
                    if not self._cap or not self._cap.isOpened():
                        self.report({'ERROR'}, "Webcam capture stream lost!")
                        self.cancel(context)
                        return {'CANCELLED'}
                        
                    ret, frame = self._cap.read()
                    if not ret:
                        return {'RUNNING_MODAL'}
                        
                    frame = cv2.flip(frame, 1)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    pose_result = self._pose_landmarker.detect(mp_image)
                    
                    has_pose = pose_result.pose_landmarks and len(pose_result.pose_landmarks) > 0
                    face_result = None
                    crop_params = None
                    
                    if has_pose:
                        pl = pose_result.pose_landmarks[0]
                        head_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                        xs = [pl[i].x for i in head_indices]
                        ys = [pl[i].y for i in head_indices]
                        xmin, xmax = min(xs), max(xs)
                        ymin, ymax = min(ys), max(ys)
                        
                        x_center = (xmin + xmax) / 2.0
                        y_center = (ymin + ymax) / 2.0
                        size = max(xmax - xmin, ymax - ymin) * 2.0
                        
                        H, W, _ = frame.shape
                        crop_xmin = max(0.0, x_center - size / 2.0)
                        crop_xmax = min(1.0, x_center + size / 2.0)
                        crop_ymin = max(0.0, y_center - size / 2.0)
                        crop_ymax = min(1.0, y_center + size / 2.0)
                        
                        left = int(crop_xmin * W)
                        right = int(crop_xmax * W)
                        top = int(crop_ymin * H)
                        bottom = int(crop_ymax * H)
                        
                        if (right - left) > 40 and (bottom - top) > 40:
                            try:
                                cropped_frame = frame[top:bottom, left:right]
                                cropped_rgb = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
                                mp_crop_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cropped_rgb)
                                crop_face_result = self._face_landmarker.detect(mp_crop_image)
                                
                                if crop_face_result.face_landmarks and len(crop_face_result.face_landmarks) > 0:
                                    face_result = crop_face_result
                                    crop_params = (crop_xmin, crop_xmax, crop_ymin, crop_ymax)
                            except Exception:
                                pass
                                
                    if face_result is None:
                        face_result = self._face_landmarker.detect(mp_image)
                        
                    hand_result = self._hand_landmarker.detect(mp_image)
                    
                    class MockLandmark:
                        def __init__(self, x, y, z):
                            self.x = x
                            self.y = y
                            self.z = z
                            
                    class MockLandmarkList:
                        def __init__(self, landmarks):
                            self.landmark = landmarks
                            
                    face_landmarks_mapped = None
                    if face_result and face_result.face_landmarks and len(face_result.face_landmarks) > 0:
                        raw_fl = face_result.face_landmarks[0]
                        if crop_params is not None:
                            c_xmin, c_xmax, c_ymin, c_ymax = crop_params
                            c_w = c_xmax - c_xmin
                            c_h = c_ymax - c_ymin
                            mapped = []
                            for lm in raw_fl:
                                mapped.append(MockLandmark(
                                    c_xmin + lm.x * c_w,
                                    c_ymin + lm.y * c_h,
                                    lm.z * c_w
                                ))
                            face_landmarks_mapped = MockLandmarkList(mapped)
                        else:
                            face_landmarks_mapped = MockLandmarkList(raw_fl)
                            
                    class UnifiedLandmarks:
                        def __init__(self, p_res, fl_mapped):
                            self.pose_landmarks = MockLandmarkList(p_res.pose_landmarks[0]) if p_res.pose_landmarks else None
                            self.pose_world_landmarks = MockLandmarkList(p_res.pose_world_landmarks[0]) if p_res.pose_world_landmarks else None
                            self.face_landmarks = fl_mapped
                            
                    results = UnifiedLandmarks(pose_result, face_landmarks_mapped)
                    
                    apply_mocap_to_rig(results, hand_result, rig_obj, scene, self._smoothers)
                    
                    if scene.hrg_mocap_record:
                        curr_frame = scene.frame_current
                        keyframe_driven_bones(rig_obj, curr_frame)
                        scene.frame_set(curr_frame + 1)
                        
                    context.view_layer.update()
                    
                    self._frame_count += 1
                    now = time.time()
                    if now - self._fps_time >= 1.0:
                        fps = self._frame_count / (now - self._fps_time)
                        context.workspace.status_text_set_internal(f"Mocap active: {fps:.1f} FPS (Webcam Live)")
                        scene.hrg_mocap_streaming_fps = fps
                        self._frame_count = 0
                        self._fps_time = now
                        
                    draw_custom_landmarks(frame, results.pose_landmarks, results.face_landmarks, hand_result)
                    cv2.putText(frame, "Blender Mocap Active", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, "Press ESC in Blender to Stop", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    if scene.hrg_mocap_record:
                        cv2.putText(frame, f"RECORDING - Frame {scene.frame_current}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        
                    if not hasattr(self, "_window_initialized") or not self._window_initialized:
                        cv2.namedWindow("Motion Capture Visualizer", cv2.WINDOW_NORMAL)
                        cv2.resizeWindow("Motion Capture Visualizer", 480, 270)
                        cv2.moveWindow("Motion Capture Visualizer", 10, 50)
                        self._window_initialized = True
                        
                    cv2.imshow("Motion Capture Visualizer", frame)
                    if cv2.getWindowProperty("Motion Capture Visualizer", cv2.WND_PROP_VISIBLE) < 1:
                        self.cancel(context)
                        return {'FINISHED'}
                    cv2.waitKey(1)
            except Exception as e:
                import traceback
                print("[Mocap Addon] Error in modal loop tick:", e)
                traceback.print_exc()
                try:
                    with open("f:/blenderaddon/mocap_debug.log", "a") as f_err:
                        f_err.write(f"MODAL_TICK_ERROR: {str(e)}\n")
                        traceback.print_exc(file=f_err)
                except:
                    pass
                
        return {'PASS_THROUGH'}
        
    def execute(self, context):
        if not dependencies_available:
            self.report({'ERROR'}, "Required dependencies missing! Install OpenCV & MediaPipe first.")
            return {'CANCELLED'}
            
        rig_obj = context.active_object
        if not rig_obj or rig_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the active Armature Rig generated by HumanRigGenerator!")
            return {'CANCELLED'}
            
        # Ensure Pose Mode is active
        if rig_obj.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
            
        # Set constraints switches to IK mode
        for side in [".L", ".R"]:
            # Arm
            pb_hand_ik = rig_obj.pose.bones.get(f"CTRL-hand_IK{side}")
            if pb_hand_ik:
                pb_hand_ik.hrg_ik_fk = 1.0
            # Leg
            pb_foot_ik = rig_obj.pose.bones.get(f"CTRL-foot_IK{side}")
            if pb_foot_ik:
                pb_foot_ik.hrg_ik_fk = 1.0
                
        # Reset calibration
        global calibration_data
        calibration_data = MocapCalibration()
        self._smoothers.clear()
        
        camera_idx = int(context.scene.hrg_mocap_camera_index)
        self._is_external = context.scene.hrg_mocap_backend_mode
        
        if self._is_external:
            import subprocess
            import socket
            import sys
            
            # Start standalone backend script in new console on Windows
            addon_dir = os.path.dirname(os.path.abspath(__file__))
            backend_script = os.path.join(addon_dir, "mocap_backend.py")
            python_exe = sys.executable
            if "blender" in os.path.basename(python_exe).lower():
                bin_python = os.path.join(sys.prefix, "bin", "python.exe")
                prefix_python = os.path.join(sys.prefix, "python.exe")
                if os.path.exists(bin_python):
                    python_exe = bin_python
                elif os.path.exists(prefix_python):
                    python_exe = prefix_python
            
            mocap_mode = getattr(context.scene, "hrg_mocap_capture_mode", "FULL")
            cmd = [python_exe, "-u", backend_script, "--camera", str(camera_idx), "--port", "5005", "--mode", mocap_mode]
            if not context.scene.hrg_mocap_show_visualizer:
                cmd.append("--no-preview")
            print("[Mocap Addon] Starting external backend:", cmd)
            
            try:
                log_path = "f:/blenderaddon/backend_debug.log"
                self._log_file = open(log_path, "w", encoding="utf-8")
                
                # Write diagnostic headers
                self._log_file.write(f"Blender sys.executable: {sys.executable}\n")
                self._log_file.write(f"Resolved python_exe: {python_exe}\n")
                self._log_file.write(f"Blender sys.path: {sys.path}\n")
                self._log_file.flush()
                
                # Copy current environment and inject Blender's sys.path as PYTHONPATH
                env = os.environ.copy()
                env["PYTHONPATH"] = os.path.pathsep.join(sys.path)
                
                self._backend_proc = subprocess.Popen(
                    cmd,
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
            except Exception as e:
                self.report({'ERROR'}, f"Failed to start external backend: {str(e)}")
                return {'CANCELLED'}
                
            # Set up non-blocking UDP receiver socket
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._sock.bind(("127.0.0.1", 5005))
                self._sock.setblocking(False)
            except Exception as socket_err:
                self.report({'ERROR'}, f"Failed to bind socket: {str(socket_err)}")
                if self._backend_proc:
                    self._backend_proc.terminate()
                return {'CANCELLED'}
                
            self._cap = None
            self._pose_landmarker = None
            self._face_landmarker = None
            self._hand_landmarker = None
        else:
            # Internal Mode setup
            # Start Webcam
            self._cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                self._cap = cv2.VideoCapture(camera_idx)
                
            if not self._cap.isOpened():
                self.report({'ERROR'}, f"Could not open webcam index {camera_idx} or webcam is already in use!")
                return {'CANCELLED'}
                
            # Set resolution to 720p for optimal virtual camera negotiation & processing speed
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Ensure models exist
            try:
                pose_model, face_model, hand_model = ensure_models_exist()
            except Exception as e:
                self.report({'ERROR'}, f"Failed to download MediaPipe models: {str(e)}")
                return {'CANCELLED'}
                
            # Initialize MediaPipe Tasks Pose, Face, and Hand Landmarkers
            try:
                base_options_pose = python.BaseOptions(model_asset_path=pose_model)
                options_pose = vision.PoseLandmarkerOptions(
                    base_options=base_options_pose,
                    running_mode=vision.RunningMode.IMAGE
                )
                self._pose_landmarker = vision.PoseLandmarker.create_from_options(options_pose)

                base_options_face = python.BaseOptions(model_asset_path=face_model)
                options_face = vision.FaceLandmarkerOptions(
                    base_options=base_options_face,
                    running_mode=vision.RunningMode.IMAGE
                )
                self._face_landmarker = vision.FaceLandmarker.create_from_options(options_face)

                base_options_hand = python.BaseOptions(model_asset_path=hand_model)
                options_hand = vision.HandLandmarkerOptions(
                    base_options=base_options_hand,
                    running_mode=vision.RunningMode.IMAGE,
                    num_hands=2
                )
                self._hand_landmarker = vision.HandLandmarker.create_from_options(options_hand)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initialize MediaPipe Landmarkers: {str(e)}")
                return {'CANCELLED'}
        
        self._fps_time = time.time()
        self._frame_count = 0
        self._window_initialized = False
        
        # Register high-speed timer (60 FPS target for instant UDP packet processing)
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.016, window=context.window)
        wm.modal_handler_add(self)
        
        context.scene.hrg_mocap_active = True
        self.report({'INFO'}, "Live Mocap started! Press ESC in Blender viewport to end stream.")
        return {'RUNNING_MODAL'}
        
    def cancel(self, context):
        context.scene.hrg_mocap_active = False
        context.workspace.status_text_set_internal(None)
        
        # Terminate external backend process cleanly
        if hasattr(self, "_backend_proc") and self._backend_proc:
            print("[Mocap Addon] Terminating external backend process...")
            try:
                self._backend_proc.terminate()
                self._backend_proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._backend_proc.kill()
                except:
                    pass
            self._backend_proc = None
            
        if hasattr(self, "_log_file") and self._log_file:
            try:
                self._log_file.close()
            except:
                pass
            self._log_file = None
            
        if hasattr(self, "_sock") and self._sock:
            try:
                self._sock.close()
            except:
                pass
            self._sock = None
            
        # Release internal resources
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        if self._cap:
            self._cap.release()
        if hasattr(self, "_pose_landmarker") and self._pose_landmarker:
            self._pose_landmarker.close()
        if hasattr(self, "_face_landmarker") and self._face_landmarker:
            self._face_landmarker.close()
        if hasattr(self, "_hand_landmarker") and self._hand_landmarker:
            self._hand_landmarker.close()
            
        cv2.destroyAllWindows()
        self.report({'INFO'}, "Live Mocap stream ended.")

# -------------------------------------------------------------
# Operator 2: Video File Motion Capture (Frame-by-Frame Parser)
# -------------------------------------------------------------
class MOCAP_OT_process_video_file(bpy.types.Operator):
    """Processes a pre-recorded video path and copies coordinates to the rig."""
    bl_idname = "mocap.process_video_file"
    bl_label = "Process Video Mocap"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    _cap = None
    _pose_landmarker = None
    _face_landmarker = None
    _hand_landmarker = None
    _smoothers = {}
    _curr_frame = 1
    _video_frame = 0
    _start_frame = 1
    _end_frame = 100
    
    def modal(self, context, event):
        scene = context.scene
        
        if event.type in {'ESC'} or not scene.hrg_mocap_active:
            self.cancel(context)
            return {'FINISHED'}
            
        if event.type == 'TIMER':
            try:
                if self._curr_frame > self._end_frame:
                    self.cancel(context)
                    self.report({'INFO'}, "Successfully processed and keyframed video file!")
                    return {'FINISHED'}
                    
                ret, frame = self._cap.read()
                if not ret:
                    # Finished parsing video early
                    self.cancel(context)
                    self.report({'INFO'}, "Completed parsing video file.")
                    return {'FINISHED'}
                    
                self._video_frame += 1
                
                # Feed to MediaPipe Tasks API
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pose_result = self._pose_landmarker.detect(mp_image)
                
                # Check if pose was detected to dynamically crop face region for distance-invariant tracking
                has_pose = pose_result.pose_landmarks and len(pose_result.pose_landmarks) > 0
                face_result = None
                crop_params = None
                
                if has_pose:
                    pl = pose_result.pose_landmarks[0]
                    # Get boundary of head landmarks (nose, eyes, ears, mouth)
                    head_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                    xs = [pl[i].x for i in head_indices]
                    ys = [pl[i].y for i in head_indices]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    
                    x_center = (xmin + xmax) / 2.0
                    y_center = (ymin + ymax) / 2.0
                    size = max(xmax - xmin, ymax - ymin) * 2.0 # padded square crop box
                    
                    H, W, _ = frame.shape
                    crop_xmin = max(0.0, x_center - size / 2.0)
                    crop_xmax = min(1.0, x_center + size / 2.0)
                    crop_ymin = max(0.0, y_center - size / 2.0)
                    crop_ymax = min(1.0, y_center + size / 2.0)
                    
                    left = int(crop_xmin * W)
                    right = int(crop_xmax * W)
                    top = int(crop_ymin * H)
                    bottom = int(crop_ymax * H)
                    
                    if (right - left) > 40 and (bottom - top) > 40:
                        try:
                            cropped_frame = frame[top:bottom, left:right]
                            cropped_rgb = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
                            mp_crop_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cropped_rgb)
                            crop_face_result = self._face_landmarker.detect(mp_crop_image)
                            
                            if crop_face_result.face_landmarks and len(crop_face_result.face_landmarks) > 0:
                                face_result = crop_face_result
                                crop_params = (crop_xmin, crop_xmax, crop_ymin, crop_ymax)
                        except Exception:
                            pass
                
                # Fallback to full frame detection if crop detection failed or pose was missing
                if face_result is None:
                    face_result = self._face_landmarker.detect(mp_image)
                    
                hand_result = self._hand_landmarker.detect(mp_image)
                
                # Create drop-in UnifiedLandmarks mock structure
                class MockLandmark:
                    def __init__(self, x, y, z):
                        self.x = x
                        self.y = y
                        self.z = z
                
                class MockLandmarkList:
                    def __init__(self, landmarks):
                        self.landmark = landmarks
                
                # Map face landmarks back to full frame space if they were cropped
                face_landmarks_mapped = None
                if face_result and face_result.face_landmarks and len(face_result.face_landmarks) > 0:
                    raw_fl = face_result.face_landmarks[0]
                    if crop_params is not None:
                        c_xmin, c_xmax, c_ymin, c_ymax = crop_params
                        c_w = c_xmax - c_xmin
                        c_h = c_ymax - c_ymin
                        mapped = []
                        for lm in raw_fl:
                            mapped.append(MockLandmark(
                                c_xmin + lm.x * c_w,
                                c_ymin + lm.y * c_h,
                                lm.z * c_w
                            ))
                        face_landmarks_mapped = MockLandmarkList(mapped)
                    else:
                        face_landmarks_mapped = MockLandmarkList(raw_fl)
                
                class UnifiedLandmarks:
                    def __init__(self, p_res, fl_mapped):
                        self.pose_landmarks = MockLandmarkList(p_res.pose_landmarks[0]) if p_res.pose_landmarks else None
                        self.pose_world_landmarks = MockLandmarkList(p_res.pose_world_landmarks[0]) if p_res.pose_world_landmarks else None
                        self.face_landmarks = fl_mapped
                
                results = UnifiedLandmarks(pose_result, face_landmarks_mapped)
                
                rig_obj = context.active_object
                if rig_obj and rig_obj.type == 'ARMATURE':
                    # Go to specific frame in timeline
                    scene.frame_set(self._curr_frame)
                    
                    # Apply landmarks
                    apply_mocap_to_rig(results, hand_result, rig_obj, scene, self._smoothers)
                    
                    # Record keys
                    keyframe_driven_bones(rig_obj, self._curr_frame)
                    
                    # Redraw viewports to see progress live
                    context.view_layer.update()
                    
                # Update Blender status progress
                percent = int((self._curr_frame - self._start_frame) / max(1, self._end_frame - self._start_frame) * 100)
                context.workspace.status_text_set_internal(f"Mocap Processing: {percent}% Frame {self._curr_frame}/{self._end_frame}")
                
                # Advance frame
                self._curr_frame += 1
            except Exception as e:
                print(f"[Mocap Video Modal Error] {str(e)}")
                import traceback
                traceback.print_exc()
                self.cancel(context)
                return {'FINISHED'}
            
        return {'PASS_THROUGH'}
        
    def execute(self, context):
        if not dependencies_available:
            self.report({'ERROR'}, "Required dependencies missing! Install OpenCV & MediaPipe first.")
            return {'CANCELLED'}
            
        scene = context.scene
        video_path = bpy.path.abspath(scene.hrg_mocap_video_path)
        
        if not video_path or not os.path.exists(video_path):
            self.report({'ERROR'}, f"Video file path is invalid or file does not exist: {video_path}")
            return {'CANCELLED'}
            
        rig_obj = context.active_object
        if not rig_obj or rig_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select the active Armature Rig generated by HumanRigGenerator!")
            return {'CANCELLED'}
            
        # Verify Pose mode
        if rig_obj.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
            
        # Ensure IK constraints active
        for side in [".L", ".R"]:
            pb_hand_ik = rig_obj.pose.bones.get(f"CTRL-hand_IK{side}")
            if pb_hand_ik:
                pb_hand_ik.hrg_ik_fk = 1.0
            pb_foot_ik = rig_obj.pose.bones.get(f"CTRL-foot_IK{side}")
            if pb_foot_ik:
                pb_foot_ik.hrg_ik_fk = 1.0
                
        # Start calibration
        global calibration_data
        calibration_data = MocapCalibration()
        self._smoothers.clear()
        
        # Load Video
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            self.report({'ERROR'}, f"Could not load video file: {video_path}")
            return {'CANCELLED'}
            
        total_video_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Adjust frame range based on settings
        self._start_frame = scene.hrg_mocap_start_frame
        self._end_frame = scene.hrg_mocap_end_frame
        if self._end_frame - self._start_frame > total_video_frames:
            self._end_frame = self._start_frame + total_video_frames - 1
            
        self._curr_frame = self._start_frame
        self._video_frame = 0
        
        # Fast-forward video to start frame position
        if self._start_frame > 1:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._start_frame - 1)
            
        # Ensure models exist
        try:
            pose_model, face_model, hand_model = ensure_models_exist()
        except Exception as e:
            self.report({'ERROR'}, f"Failed to download MediaPipe models: {str(e)}")
            return {'CANCELLED'}
            
        # Initialize MediaPipe Tasks Pose, Face, and Hand Landmarkers
        try:
            base_options_pose = python.BaseOptions(model_asset_path=pose_model)
            options_pose = vision.PoseLandmarkerOptions(
                base_options=base_options_pose,
                running_mode=vision.RunningMode.IMAGE
            )
            self._pose_landmarker = vision.PoseLandmarker.create_from_options(options_pose)

            base_options_face = python.BaseOptions(model_asset_path=face_model)
            options_face = vision.FaceLandmarkerOptions(
                base_options=base_options_face,
                running_mode=vision.RunningMode.IMAGE
            )
            self._face_landmarker = vision.FaceLandmarker.create_from_options(options_face)

            base_options_hand = python.BaseOptions(model_asset_path=hand_model)
            options_hand = vision.HandLandmarkerOptions(
                base_options=base_options_hand,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=2
            )
            self._hand_landmarker = vision.HandLandmarker.create_from_options(options_hand)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to initialize MediaPipe Landmarkers: {str(e)}")
            return {'CANCELLED'}
        
        # Launch modal loops
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.001, window=context.window) # Run as fast as possible
        wm.modal_handler_add(self)
        
        scene.hrg_mocap_active = True
        self.report({'INFO'}, f"Processing video file: {os.path.basename(video_path)}. Press ESC to stop.")
        return {'RUNNING_MODAL'}
        
    def cancel(self, context):
        context.scene.hrg_mocap_active = False
        context.workspace.status_text_set_internal(None)
        
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        if self._cap:
            self._cap.release()
        if hasattr(self, "_pose_landmarker") and self._pose_landmarker:
            self._pose_landmarker.close()
        if hasattr(self, "_face_landmarker") and self._face_landmarker:
            self._face_landmarker.close()
        if hasattr(self, "_hand_landmarker") and self._hand_landmarker:
            self._hand_landmarker.close()
            
        self.report({'INFO'}, "Video processing ended.")

# -------------------------------------------------------------
# Operator 3: Quick Manual T-Pose Calibration Helper
# -------------------------------------------------------------
class MOCAP_OT_force_calibrate(bpy.types.Operator):
    """Calibrates calibration scaling based on the current camera viewport frame."""
    bl_idname = "mocap.force_calibrate"
    bl_label = "Calibrate T-Pose"
    bl_description = "Resets and calibrates scaling factors using the next processed frame"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global calibration_data
        calibration_data = MocapCalibration() # Resets calibrated flag
        self.report({'INFO'}, "Calibration reset! Stand in T-Pose in front of the camera to calibrate.")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(MOCAP_OT_live_capture)
    bpy.utils.register_class(MOCAP_OT_process_video_file)
    bpy.utils.register_class(MOCAP_OT_force_calibrate)

def unregister():
    bpy.utils.unregister_class(MOCAP_OT_live_capture)
    bpy.utils.unregister_class(MOCAP_OT_process_video_file)
    bpy.utils.unregister_class(MOCAP_OT_force_calibrate)
