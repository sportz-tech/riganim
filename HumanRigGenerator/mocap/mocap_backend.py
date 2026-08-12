# mocap_backend.py
import argparse
import socket
import json
import time
import os
import math
import sys
import site
from concurrent.futures import ThreadPoolExecutor

# Print starting sys.path
print(f"Backend sys.path initially: {sys.path}")

# Ensure Blender/pip user site-packages is searched
user_site = site.getusersitepackages()
print(f"site.getusersitepackages(): {user_site}")
if user_site not in sys.path:
    sys.path.append(user_site)
    print(f"Appended user_site to sys.path")

# Ensure dependencies are loaded
try:
    import cv2
    print("Successfully imported cv2")
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("Successfully imported mediapipe and tasks")
except Exception as e:
    import traceback
    print(f"Error importing dependencies: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Setup paths relative to script
addon_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(addon_dir, "models")
pose_model = os.path.join(models_dir, "pose_landmarker_lite.task")
face_model = os.path.join(models_dir, "face_landmarker.task")
hand_model = os.path.join(models_dir, "hand_landmarker.task")

def ensure_models_exist():
    import urllib.request
    import zipfile
    os.makedirs(models_dir, exist_ok=True)
    urls = {
        pose_model: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        face_model: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        hand_model: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
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
            print(f"Downloading model: {url} to {path}...")
            try:
                if os.path.exists(path):
                    os.remove(path)
                tmp_path = path + ".tmp"
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                urllib.request.urlretrieve(url, tmp_path)
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100000:
                    os.replace(tmp_path, path)
                    print(f"Successfully verified and saved model: {path}")
                else:
                    raise RuntimeError("Incomplete download")
            except Exception as e:
                print(f"Failed to download {url}: {e}")
                sys.exit(1)

# Overlay Drawing helper constants
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
    # Upper lip outer outline
    [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291],
    # Lower lip outer outline
    [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291],
    # Upper lip inner outline
    [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308],
    # Lower lip inner outline
    [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308],
    # Nose contours
    [168, 6, 197, 195, 5, 4, 2, 97, 98, 326, 327],
    # Face silhouette / jawline
    [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
]

# Adaptive Landmark Stabilizer with deadband noise filtering
class LandmarkSmoother:
    def __init__(self, mincutoff=0.8, beta=0.03, deadband=0.0018):
        self.mincutoff = mincutoff
        self.beta = beta
        self.deadband = deadband # Completely ignores sub-millimeter webcam sensor grain when standing still
        self.prev_vals = {}
        self.prev_time = {}
        self.dx_prev = {}

    def smooth_list(self, landmarks, key_prefix, timestamp_s):
        if not landmarks:
            return landmarks
        smoothed = []
        for idx, lm in enumerate(landmarks):
            k = f"{key_prefix}_{idx}"
            raw_x, raw_y, raw_z = lm.x, lm.y, lm.z
            vis = getattr(lm, "visibility", 1.0)
            
            if k not in self.prev_vals:
                self.prev_vals[k] = [raw_x, raw_y, raw_z]
                self.prev_time[k] = timestamp_s
                self.dx_prev[k] = [0.0, 0.0, 0.0]
                smoothed.append(lm)
                continue
                
            dt = max(0.001, timestamp_s - self.prev_time[k])
            self.prev_time[k] = timestamp_s
            
            px, py, pz = self.prev_vals[k]
            dist = math.sqrt((raw_x - px)**2 + (raw_y - py)**2 + (raw_z - pz)**2)
            
            # Deadband: if noise is tiny (stationary), hold position 100% steady!
            if dist < self.deadband:
                class StabilizedLM:
                    pass
                slm = StabilizedLM()
                slm.x, slm.y, slm.z = px, py, pz
                slm.visibility = vis
                smoothed.append(slm)
                continue
                
            # One Euro Filter for smooth responsive movement
            dx = [(raw_x - px) / dt, (raw_y - py) / dt, (raw_z - pz) / dt]
            d_prev = self.dx_prev[k]
            alpha_d = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * 1.0)) / dt)
            dx_hat = [d_prev[i] + alpha_d * (dx[i] - d_prev[i]) for i in range(3)]
            self.dx_prev[k] = dx_hat
            
            speed = math.sqrt(dx_hat[0]**2 + dx_hat[1]**2 + dx_hat[2]**2)
            cutoff = self.mincutoff + self.beta * speed
            alpha = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * cutoff)) / dt)
            
            sx = px + alpha * (raw_x - px)
            sy = py + alpha * (raw_y - py)
            sz = pz + alpha * (raw_z - pz)
            self.prev_vals[k] = [sx, sy, sz]
            
            class StabilizedLM:
                pass
            slm = StabilizedLM()
            slm.x, slm.y, slm.z = sx, sy, sz
            slm.visibility = vis
            smoothed.append(slm)
            
        return smoothed

def draw_landmarks(image, pose_lms, face_lms, hand_lms_list):
    # Draw Face outlines
    if face_lms:
        h, w, _ = image.shape
        face_pts = {}
        for idx, lm in enumerate(face_lms):
            cx, cy = int(lm.x * w), int(lm.y * h)
            face_pts[idx] = (cx, cy)
            
        # Draw outline mesh lines
        for loop in FACE_CONTOURS:
            for i in range(len(loop)):
                p1 = loop[i]
                p2 = loop[(i + 1) % len(loop)]
                if p1 in face_pts and p2 in face_pts:
                    cv2.line(image, face_pts[p1], face_pts[p2], (255, 255, 0), 1)
                    
        # Draw sparse yellow dots
        for idx in range(0, len(face_lms), 5):
            if idx in face_pts:
                cv2.circle(image, face_pts[idx], 1, (0, 255, 255), -1)
            
    # Draw Pose
    if pose_lms:
        h, w, _ = image.shape
        points = {}
        for idx, lm in enumerate(pose_lms):
            cx, cy = int(lm.x * w), int(lm.y * h)
            points[idx] = (cx, cy)
            cv2.circle(image, (cx, cy), 3, (0, 255, 0), -1)
        for connection in POSE_CONNECTIONS:
            p1, p2 = connection
            if p1 in points and p2 in points:
                cv2.line(image, points[p1], points[p2], (0, 255, 0), 2)
                
    # Draw Hands
    if hand_lms_list:
        h, w, _ = image.shape
        for hand in hand_lms_list:
            points = {}
            for idx, lm in enumerate(hand):
                cx, cy = int(lm.x * w), int(lm.y * h)
                points[idx] = (cx, cy)
                cv2.circle(image, (cx, cy), 3, (255, 0, 0), -1)
            for connection in HAND_CONNECTIONS:
                p1, p2 = connection
                if p1 in points and p2 in points:
                    cv2.line(image, points[p1], points[p2], (255, 0, 0), 2)

def main():
    parser = argparse.ArgumentParser(description="MediaPipe Standalone Mocap Backend")
    parser.add_argument("--camera", type=int, default=0, help="Webcam camera index")
    parser.add_argument("--port", type=int, default=5005, help="UDP transmission port")
    parser.add_argument("--mode", type=str, default="FULL", choices=["FULL", "BODY", "FACE", "HANDS"], help="Mocap detection mode (FULL, BODY, FACE, HANDS)")
    parser.add_argument("--no-preview", action="store_true", help="Hide visualizer preview window for higher FPS")
    args = parser.parse_args()

    ensure_models_exist()

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("127.0.0.1", args.port)

    # Initialize Landmarkers based on selected mode
    print(f"Initializing MediaPipe models for mode: {args.mode}...")
    pose_landmarker = None
    face_landmarker = None
    hand_landmarker = None

    if args.mode in ["FULL", "BODY"]:
        base_options_pose = python.BaseOptions(model_asset_path=pose_model)
        options_pose = vision.PoseLandmarkerOptions(
            base_options=base_options_pose,
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        pose_landmarker = vision.PoseLandmarker.create_from_options(options_pose)

    if args.mode in ["FULL", "FACE"]:
        base_options_face = python.BaseOptions(model_asset_path=face_model)
        options_face = vision.FaceLandmarkerOptions(
            base_options=base_options_face,
            running_mode=vision.RunningMode.VIDEO,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        face_landmarker = vision.FaceLandmarker.create_from_options(options_face)

    if args.mode in ["FULL", "BODY", "HANDS"]:
        base_options_hand = python.BaseOptions(model_asset_path=hand_model)
        options_hand = vision.HandLandmarkerOptions(
            base_options=base_options_hand,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        hand_landmarker = vision.HandLandmarker.create_from_options(options_hand)

    # Start Camera capture
    print(f"Opening camera index {args.camera}...")
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Could not open camera {args.camera}.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 60)

    print("Mocap Backend started successfully! Sending data on UDP port", args.port)
    print("Press ESC in the video preview window or close it to stop the backend.")

    if not args.no_preview:
        cv2.namedWindow("Motion Capture Backend Visualizer", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Motion Capture Backend Visualizer", 480, 270)
        cv2.moveWindow("Motion Capture Backend Visualizer", 10, 50)

    fps_time = time.time()
    frame_count = 0
    last_timestamp_ms = 0
    smoother = LandmarkSmoother(mincutoff=0.8, beta=0.03, deadband=0.0018)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror frame
            frame = cv2.flip(frame, 1)
            
            # Force resize frame to 480x270 for ultra-fast AI processing
            H, W, _ = frame.shape
            if W != 480 or H != 270:
                frame = cv2.resize(frame, (480, 270))
                H, W, _ = frame.shape

            # Convert to MediaPipe format
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Calculate monotonic timestamp in ms
            t_now = time.time()
            timestamp_ms = int(t_now * 1000) * 10
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 10
            last_timestamp_ms = timestamp_ms

            # Run models directly (fast, stable, and zero thread-locking contention)
            pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms) if pose_landmarker else None
            face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms + 1) if face_landmarker else None
            hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms + 2) if hand_landmarker else None

            # Stabilize landmarks with deadband filter to eliminate stationary fluctuation/jitter
            raw_pose_lms = pose_result.pose_landmarks[0] if (pose_result and pose_result.pose_landmarks and len(pose_result.pose_landmarks) > 0) else None
            raw_pose_wl = pose_result.pose_world_landmarks[0] if (pose_result and pose_result.pose_world_landmarks and len(pose_result.pose_world_landmarks) > 0) else None
            raw_face_lms = face_result.face_landmarks[0] if (face_result and face_result.face_landmarks and len(face_result.face_landmarks) > 0) else None
            
            stab_pose_lms = smoother.smooth_list(raw_pose_lms, "pose", t_now) if raw_pose_lms else None
            stab_pose_wl = smoother.smooth_list(raw_pose_wl, "pose_wl", t_now) if raw_pose_wl else None
            stab_face_lms = smoother.smooth_list(raw_face_lms, "face", t_now) if raw_face_lms else None
            
            # Extract Holistic left and right hands
            stab_left_hand = None
            stab_right_hand = None
            stab_hand_lms = []
            
            if hand_result and hand_result.hand_landmarks and hand_result.handedness:
                for h_idx, h_list in enumerate(hand_result.hand_landmarks):
                    cat_name = hand_result.handedness[h_idx][0].category_name
                    # In mirrored webcam, "Left" category from MediaPipe corresponds to user's left hand
                    if cat_name == "Left":
                        stab_left_hand = smoother.smooth_list(h_list, "left_hand", t_now)
                        stab_hand_lms.append(stab_left_hand)
                    else:
                        stab_right_hand = smoother.smooth_list(h_list, "right_hand", t_now)
                        stab_hand_lms.append(stab_right_hand)

            # Package JSON payload with unified Holistic data architecture
            payload = {
                "pose_landmarks": [{"x": l.x, "y": l.y, "z": l.z, "visibility": getattr(l, "visibility", 1.0)} for l in stab_pose_lms] if stab_pose_lms else None,
                "pose_world_landmarks": [{"x": l.x, "y": l.y, "z": l.z, "visibility": getattr(l, "visibility", 1.0)} for l in stab_pose_wl] if stab_pose_wl else None,
                "face_landmarks": [{"x": l.x, "y": l.y, "z": l.z} for l in stab_face_lms] if stab_face_lms else None,
                "left_hand_landmarks": [{"x": l.x, "y": l.y, "z": l.z} for l in stab_left_hand] if stab_left_hand else None,
                "right_hand_landmarks": [{"x": l.x, "y": l.y, "z": l.z} for l in stab_right_hand] if stab_right_hand else None,
                "hand_landmarks": [[{"x": l.x, "y": l.y, "z": l.z} for l in hand] for hand in stab_hand_lms] if stab_hand_lms else None,
                "handedness": [[{"category_name": h[0].category_name}] for h in hand_result.handedness] if (hand_result and hand_result.handedness and len(hand_result.handedness) > 0) else None
            }

            # Send over UDP
            try:
                data_str = json.dumps(payload)
                sock.sendto(data_str.encode("utf-8"), server_address)
            except Exception as socket_err:
                print("Socket transmit error:", socket_err)

            if not args.no_preview:
                # Draw rock-solid stabilized visualization overlay (zero stationary jitter/fluctuation)
                draw_landmarks(frame, stab_pose_lms, stab_face_lms, stab_hand_lms)

                # Calculate FPS
                frame_count += 1
                now = time.time()
                if now - fps_time >= 1.0:
                    fps = frame_count / (now - fps_time)
                    cv2.setWindowTitle("Motion Capture Backend Visualizer", f"Mocap Backend ({args.mode}): {fps:.1f} FPS")
                    frame_count = 0
                    fps_time = now

                cv2.putText(frame, f"Mocap Backend [{args.mode}]", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Motion Capture Backend Visualizer", frame)

                # Escape key stops loop
                if cv2.waitKey(1) & 0xFF == 27:
                    break

                # Handle window close button check
                if cv2.getWindowProperty("Motion Capture Backend Visualizer", cv2.WND_PROP_VISIBLE) < 1:
                    break
            else:
                # Process CV events but do not draw window
                if cv2.waitKey(1) & 0xFF == 27:
                    break
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
    finally:
        print("Cleaning up resources...")
        try:
            if 'cap' in locals() and cap is not None:
                cap.release()
        except:
            pass
        try:
            cv2.destroyAllWindows()
        except:
            pass
        try:
            if 'pose_landmarker' in locals() and pose_landmarker:
                pose_landmarker.close()
        except:
            pass
        try:
            if 'face_landmarker' in locals() and face_landmarker:
                face_landmarker.close()
        except:
            pass
        try:
            if 'hand_landmarker' in locals() and hand_landmarker:
                hand_landmarker.close()
        except:
            pass
        try:
            if 'sock' in locals() and sock:
                sock.close()
        except:
            pass
        print("Backend closed successfully.")
        sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
