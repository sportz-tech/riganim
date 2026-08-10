# RigAnim - Blender Animation & Rigging Suite

A suite of Blender 4.x / 5.x addons and toolsets designed for rapid 3D character rigging, AI/Webcam motion capture transfer, multi-actor filmmaking, and cinematic camera directing.

---

## Included Addons

### 1. 🦴 HumanRigGenerator
A procedural, 1-click human & creature auto-rigging and animation toolkit.
- **Interactive Alignment Markers**: 1-click interactive bone placement with symmetry mirroring.
- **Auto-Skinning**: Automatic vertex weight calculation and mesh deformation binding.
- **Multi-Actor Manager**: 1-click character cloner with independent materials, actions, and dedicated Outliner collections.
- **Surface Spawn Points & Keyframe Travel**: Mark spawn locations directly on 3D ground planes and animate character travel across timeline frames.
- **Prop & Tool Attacher**: 1-click snap & attach props (ropes, dogs, phones, tools) to hands/body with automated finger grasp and keyframed grab/drop.
- **Cinematic Camera Controller**: Automated framing (Wide, Medium, Close-up, OTS), dynamic orbit/zoom, multi-camera switching, and viewport name tags.
- **Pose Mixer & Expression Library**: Sliders for facial expressions (mouth, eyes, brows) and body poses.
- **Animation Presets & Timing Scaling**: Built-in walk/run/jump cycles, speed rescalers (2x faster / 0.5x slower), and F-curve jitter smoothing.

### 2. 📹 MotionCaptureTransfer
Real-time webcam and video AI motion capture transfer for Blender armatures.
- **Live AI Tracking**: MediaPipe pose, face mesh, and hand tracking streamed directly into Blender over low-latency UDP sockets.
- **Armature Retargeting**: Auto-maps tracking landmarks to standard Blender bone hierarchies.
- **Keyframe Baking**: Records and bakes live motion capture performances directly onto the timeline action editor.

---

## Guides & Storyboards
- **`3D_Animation_Framing_and_Timing_Guide.txt`**: Complete teaching and reference guide for 24 vs 30 FPS timing, shot sizes, camera angles, and keyframe spacing.
- **`Canal_Rescue_10Sec_Assignment_Plan.txt`**: 300-frame storyboard, pacing blueprint, and animator instructions for multi-character rescue animations.

---

## Installation
1. Download or clone this repository.
2. Zip the `HumanRigGenerator` or `MotionCaptureTransfer` folder.
3. In Blender, go to **Edit** ➔ **Preferences** ➔ **Add-ons** ➔ **Install...**
4. Select the `.zip` file and enable the checkbox.
5. Open the 3D Viewport sidebar (`N`) to access the tools.

---

## License
MIT License
