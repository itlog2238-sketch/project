HAND GESTURE POPUP SYSTEM
==========================

This project uses your webcam to recognize hand gestures in real time.
When the recognized gesture changes, an animated popup appears on your screen.

SUPPORTED GESTURES
------------------
 1. Open palm          -> 🖐️
 2. Fist               -> ✊
 3. Thumbs up          -> 👍
 4. Peace sign         -> ✌️
 5. One finger         -> ☝️
 6. Two-hand heart     -> ❤️
 7. OK sign            -> 👌
 8. Rock on            -> 🤘
 9. Call me / Shaka    -> 🤙
10. Three fingers      -> 3️⃣
11. Four fingers       -> 4️⃣
12. Pinky              -> 🌸
13. Spider-Man         -> 🕷️
14. Vulcan salute      -> 🖖
15. Point down         -> 👇
16. Crossed fingers    -> 🤞
17. Wave               -> 👋
18. Finger gun         -> 👉
19. Pinch              -> 🤌

REQUIREMENTS
------------
- Windows
- Python 3.10 or 3.11 recommended
- Working webcam
- Internet connection for the first package installation

HOW TO INSTALL
--------------
1. Extract this ZIP.
2. Open the extracted folder.
3. Double-click install.bat.
4. The installer automatically checks for Python.
5. If Python is missing, the installer explains exactly how to install it.
6. Wait for installation to finish.

HOW TO RUN
----------
1. Double-click run.bat.
2. Allow camera access if Windows asks.
3. Put your hand in front of the camera.
4. Change your gesture.
5. An animated popup will slide in from the bottom-right when a new gesture is detected.
6. Press Q or ESC to close the camera.

KEYBOARD SHORTCUTS
------------------
S  - Toggle skeleton (landmark) drawing
H  - Toggle gesture history sidebar
M  - Toggle sound on/off
R  - Reset session stats
F  - Toggle fullscreen
Q / ESC - Quit

IMPORTANT: HEART GESTURE
------------------------
The heart gesture uses TWO hands.

Bring your two index fingertips close together and your two thumbs
close together to form the top/inside shape of a heart.

TROUBLESHOOTING
---------------
CAMERA DOES NOT OPEN:
- Close Zoom, Discord, Teams, OBS, or other apps using the camera.
- Check Windows Settings > Privacy & security > Camera.
- Make sure camera access is enabled for desktop apps.

MEDIAPIPE INSTALLATION ERROR:
- Use Python 3.10 or 3.11.
- Create the virtual environment again by deleting the .venv folder,
  then run install.bat.

GESTURE IS NOT DETECTED:
- Use good lighting.
- Keep your entire hand visible.
- Hold the gesture for about half a second.
- For the heart, make sure both hands are visible.

HOW IT WORKS
------------
OpenCV reads frames from your webcam.
MediaPipe detects the hand landmarks.
The program uses vector-based analysis of the landmarks to identify the gesture.
Tkinter displays an animated, color-coded popup.
Sound feedback (winsound) plays a tone when a gesture is confirmed.

FEATURES
--------
- 19 gesture types including Pinky, Spider-Man, Vulcan, Wave, Pinch, and more
- Animated slide-in popup from the bottom-right corner
- Confidence meter bar showing gesture detection progress
- FPS counter in the top-right corner
- Gesture history sidebar (last 5 gestures with timestamps)
- Per-session gesture stats panel (top 3 most used)
- Sound feedback (different pitches per gesture family)
- Keyboard shortcuts for all settings
- "No hand detected" pulsing overlay after 3 seconds with no hand
- Vector-based recognition that handles tilted/rotated hands

PYTHON CHECK
------------
The updated install.bat automatically checks:
- whether Python is available
- whether the Python Launcher (py.exe) is available
- whether Python can actually start
- whether the virtual environment can be created
- whether the required packages can be installed

If Python is missing, it does NOT silently fail. It shows instructions
for installing Python and for disabling the Windows Microsoft Store
python.exe/python3.exe app aliases if necessary.


INSTALLER UPDATE
----------------
If Windows says "Found Python:" but the version appears as "was",
you are probably hitting the Microsoft Store Python alias instead
of a real Python installation.

The updated installer does not trust the "python" command just
because Windows can find it. It actually runs Python with a small
test command first. It also tries the "py -3" launcher first.

If no working Python is found, the installer explains how to:
- install Python 3.11 from python.org
- enable "Add python.exe to PATH"
- disable the Microsoft Store python.exe/python3.exe aliases


MEDIAPIPE COMPATIBILITY FIX
---------------------------
This version pins MediaPipe to 0.10.21 because the hand tracking code
uses the classic "mediapipe.solutions.hands" API.

If you already installed the previous ZIP, you do NOT need to reinstall
everything. Run repair_mediapipe.bat once, then run run.bat.
