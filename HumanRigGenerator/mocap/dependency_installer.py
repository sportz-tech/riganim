import sys
import subprocess
import os
import site
import bpy

# Ensure Blender searches user site-packages where pip --user installs files
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.append(user_site)

def log_to_file(message):
    """Writes a message to hrg_mocap_install_debug.log in the IDE scratch directory."""
    log_file_path = "C:/Users/aispv/.gemini/antigravity-ide/scratch/hrg_mocap_install_debug.log"
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"[{os.getpid()}] {message}\n")
    except Exception as e:
        print("[Mocap Addon Log Error]", str(e))

def check_dependencies():
    """Checks if cv2 (OpenCV) and mediapipe are installed in the current Python environment."""
    cv2_installed = False
    mp_installed = False
    
    import traceback
    
    try:
        import cv2
        cv2_installed = True
    except Exception as e:
        log_to_file(f"cv2 import failed: {str(e)}")
        log_to_file(traceback.format_exc())
        
    try:
        import mediapipe
        mp_installed = True
    except Exception as e:
        log_to_file(f"mediapipe import failed: {str(e)}")
        log_to_file(traceback.format_exc())
        
    return cv2_installed, mp_installed

class MOCAP_OT_install_dependencies(bpy.types.Operator):
    """Installs required Python packages (opencv-python and mediapipe) for Motion Capture."""
    bl_idname = "mocap.install_dependencies"
    bl_label = "Install Mocap Dependencies"
    bl_description = "Downloads and installs opencv-python and mediapipe via pip inside Blender's Python environment"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        # Reset and create log file
        log_file_path = "C:/Users/aispv/.gemini/antigravity-ide/scratch/hrg_mocap_install_debug.log"
        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write("=== Mocap Installation Debug Log ===\n")
        except Exception as e:
            print("[Mocap Addon Log Error]", str(e))
            
        log_to_file(f"System sys.executable: {sys.executable}")
        log_to_file(f"System sys.prefix: {sys.prefix}")
        log_to_file(f"System sys.exec_prefix: {sys.exec_prefix}")
        log_to_file(f"Current mode: {bpy.context.mode if hasattr(bpy.context, 'mode') else 'Unknown'}")
        
        cv2_ok, mp_ok = check_dependencies()
        if cv2_ok and mp_ok:
            log_to_file("Dependencies are already installed. Exiting.")
            self.report({'INFO'}, "Dependencies are already installed!")
            return {'FINISHED'}
            
        self.report({'INFO'}, "Installing dependencies... Blender might freeze for a moment.")
        
        # Determine Python path robustly inside Blender
        python_exe = sys.executable
        if "blender" in os.path.basename(python_exe).lower():
            bin_python = os.path.join(sys.prefix, "bin", "python.exe")
            prefix_python = os.path.join(sys.prefix, "python.exe")
            log_to_file(f"Checking bin_python path: {bin_python} (exists: {os.path.exists(bin_python)})")
            log_to_file(f"Checking prefix_python path: {prefix_python} (exists: {os.path.exists(prefix_python)})")
            if os.path.exists(bin_python):
                python_exe = bin_python
            elif os.path.exists(prefix_python):
                python_exe = prefix_python
                
        self.report({'INFO'}, f"Using Python: {os.path.basename(python_exe)}")
        log_to_file(f"Resolved Python executable to use: {python_exe}")
        
        # Verify pip is available
        try:
            log_to_file("Running ensurepip...")
            r = subprocess.run([python_exe, "-m", "ensurepip", "--user"], capture_output=True, text=True)
            log_to_file(f"Ensurepip code: {r.returncode}")
            log_to_file(f"Ensurepip stdout: {r.stdout}")
            log_to_file(f"Ensurepip stderr: {r.stderr}")
        except Exception as e:
            log_to_file(f"Ensurepip exception: {str(e)}")
            
        # Upgrade pip
        try:
            log_to_file("Upgrading pip...")
            r = subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "--user"], capture_output=True, text=True)
            log_to_file(f"Pip upgrade code: {r.returncode}")
            log_to_file(f"Pip upgrade stdout: {r.stdout}")
            log_to_file(f"Pip upgrade stderr: {r.stderr}")
        except Exception as e:
            log_to_file(f"Pip upgrade exception: {str(e)}")
            
        # Install packages
        packages = []
        if not cv2_ok:
            packages.append("opencv-python")
        if not mp_ok:
            packages.append("mediapipe")
            
        if packages:
            cmd = [python_exe, "-m", "pip", "install"] + packages + ["--user"]
            self.report({'INFO'}, f"Installing packages: {', '.join(packages)}")
            log_to_file(f"Running pip install command: {' '.join(cmd)}")
            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
                log_to_file(f"Pip install return code: {result.returncode}")
                log_to_file(f"Pip install stdout: {result.stdout}")
                log_to_file(f"Pip install stderr: {result.stderr}")
                
                if result.returncode == 0:
                    self.report({'INFO'}, f"Successfully installed: {', '.join(packages)}")
                else:
                    self.report({'ERROR'}, f"Failed to install. Check install_debug.log in addon folder.")
                    return {'CANCELLED'}
            except Exception as e:
                log_to_file(f"Pip install exception: {str(e)}")
                self.report({'ERROR'}, f"Error running pip: {str(e)}")
                return {'CANCELLED'}
                
        # Re-check to verify installation
        cv2_ok, mp_ok = check_dependencies()
        log_to_file(f"Final check: cv2={cv2_ok}, mediapipe={mp_ok}")
        if cv2_ok and mp_ok:
            self.report({'INFO'}, "All dependencies successfully verified!")
            # Force redraw of area
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return {'FINISHED'}
        else:
            missing = []
            if not cv2_ok: missing.append("opencv-python")
            if not mp_ok: missing.append("mediapipe")
            self.report({'ERROR'}, f"Verification failed for: {', '.join(missing)}")
            return {'CANCELLED'}
                


def register():
    bpy.utils.register_class(MOCAP_OT_install_dependencies)

def unregister():
    bpy.utils.unregister_class(MOCAP_OT_install_dependencies)
