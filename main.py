"""
Hand Gesture Popup System — Super Enhanced
==========================================
All logic lives in this single file.
"""

import cv2
import mediapipe as mp
import tkinter as tk
import threading
import time
import math
import winsound
import collections
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# ──────────── CONSTANTS ────────────

WINDOW_TITLE = "Hand Gesture Popup System"

# Camera
CAM_WIDTH = 960
CAM_HEIGHT = 720

# MediaPipe
MP_MAX_HANDS = 2
MP_DETECTION_CONF = 0.55
MP_TRACKING_CONF = 0.55

# Gesture confirmation
CONFIRM_FRAMES = 5

# Heart detection thresholds
HEART_INDEX_GAP = 0.12
HEART_THUMB_GAP = 0.16

# OK sign: thumb tip ↔ index tip proximity
OK_TOUCH_THRESHOLD = 0.07

# Vector-based finger extension thresholds
FINGER_DOT_THRESHOLD = 0.5
FINGER_MAG_RATIO = 0.8

# Thumb angle threshold (degrees) for extension
THUMB_ANGLE_THRESHOLD = 45.0

# FPS rolling window size
FPS_WINDOW = 30

# No-hand timeout (seconds)
NO_HAND_TIMEOUT = 3.0

# Popup dimensions and timing
POPUP_WIDTH = 320
POPUP_HEIGHT = 200
POPUP_MARGIN = 20
POPUP_SLIDE_MS = 200      # total slide-in duration
POPUP_SLIDE_STEPS = 20    # number of animation steps
POPUP_HOLD_MS = 2500      # how long popup stays visible
POPUP_FADE_STEPS = 20     # fade-out steps
POPUP_FADE_MS = 300       # total fade-out duration

# Confidence bar colors (BGR)
COLOR_BAR_LOW = (0, 0, 200)
COLOR_BAR_MID = (0, 200, 200)
COLOR_BAR_HIGH = (0, 200, 0)

# Gesture history
HISTORY_MAX = 5

# Stats: top-N display
STATS_TOP_N = 3

# No-hand pulse: alternating every N frames
PULSE_PERIOD = 30

# Sound settings per gesture family
SOUND_HAPPY = (880, 120)
SOUND_POWER = (440, 100)
SOUND_NEUTRAL = (660, 110)

# Border / family colors (hex) for popup
BORDER_COLORS: Dict[str, str] = {
    "PEACE":          "#00b4d8",
    "OK":             "#00b4d8",
    "FIST":           "#e63946",
    "ROCK":           "#e63946",
    "HEART":          "#ff6b9d",
    "OPEN PALM":      "#4361ee",
    "THUMBS UP":      "#f4a261",
    "SHAKA":          "#f4a261",
    "ONE":            "#9b5de5",
    "THREE":          "#9b5de5",
    "FOUR":           "#9b5de5",
    # New gestures
    "PINKY":          "#c77dff",
    "ILY":            "#ff6b9d",
    "VULCAN":         "#00b4d8",
    "POINT DOWN":     "#9b5de5",
    "CROSSED FINGERS":"#f4a261",
    "WAVE":           "#4361ee",
    "FINGER GUN":     "#f77f00",
    "PINCH":          "#ff6b9d",
}

DARK_BG = "#1a1a2e"

# ──────────── GESTURE DEFINITIONS ────────────

GESTURES: Dict[str, tuple] = {
    "OPEN PALM":       ("(palm)",   "OPEN PALM"),
    "FIST":            ("(fist)",   "FIST"),
    "THUMBS UP":       ("(+1)",     "THUMBS UP"),
    "PEACE":           ("(peace)",  "PEACE SIGN"),
    "ONE":             ("(1)",      "ONE FINGER"),
    "HEART":           "(<3)",
    "OK":              ("(ok)",     "OK SIGN"),
    "ROCK":            ("(rock)",   "ROCK ON"),
    "SHAKA":           ("(shaka)",  "CALL ME"),
    "THREE":           ("(3)",      "THREE FINGERS"),
    "FOUR":            ("(4)",      "FOUR FINGERS"),
    # New gestures
    "PINKY":           ("(pinky)",  "PINKY"),
    "ILY":             ("(ily)",    "I LOVE YOU"),
    "VULCAN":          ("(llap)",   "VULCAN SALUTE"),
    "POINT DOWN":      ("(down)",   "POINT DOWN"),
    "CROSSED FINGERS": ("(cross)",  "CROSSED FINGERS"),
    "WAVE":            ("(wave)",   "WAVE"),
    "FINGER GUN":      ("(gun)",    "FINGER GUN"),
    "PINCH":           ("(pinch)",  "PINCH"),
}

# Short ASCII labels for history sidebar
GESTURE_LABELS: Dict[str, str] = {
    "OPEN PALM":       "[Palm]",
    "FIST":            "[Fist]",
    "THUMBS UP":       "[ThmbUp]",
    "PEACE":           "[Peace]",
    "ONE":             "[One]",
    "HEART":           "[Heart]",
    "OK":              "[OK]",
    "ROCK":            "[Rock]",
    "SHAKA":           "[Shaka]",
    "THREE":           "[Three]",
    "FOUR":            "[Four]",
    # New gestures
    "PINKY":           "[Pinky]",
    "ILY":             "[ILY]",
    "VULCAN":          "[Vulcan]",
    "POINT DOWN":      "[PtDown]",
    "CROSSED FINGERS": "[Cross]",
    "WAVE":            "[Wave]",
    "FINGER GUN":      "[FGun]",
    "PINCH":           "[Pinch]",
}

# ──────────── APP STATE ────────────

@dataclass
class AppState:
    # Gesture tracking
    last_gesture: Optional[str] = None
    stable_gesture: Optional[str] = None
    candidate: Optional[str] = None
    candidate_count: int = 0

    # Toggles
    show_skeleton: bool = True
    show_history: bool = True
    sound_on: bool = True
    fullscreen: bool = False

    # FPS tracking
    frame_times: collections.deque = field(default_factory=lambda: collections.deque(maxlen=FPS_WINDOW))

    # No-hand tracking
    last_hand_time: float = field(default_factory=time.time)
    frame_count: int = 0

    # Gesture history: list of (label_str, time_str)
    history: List[tuple] = field(default_factory=list)

    # Gesture stats: gesture_name -> count
    stats: Dict[str, int] = field(default_factory=dict)


# ──────────── GESTURE RECOGNITION ────────────

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def _vec(a, b):
    """2D vector from landmark a to landmark b."""
    return (b.x - a.x, b.y - a.y)


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1]


def _mag(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _normalize(v):
    m = _mag(v)
    if m < 1e-9:
        return (0.0, 0.0)
    return (v[0] / m, v[1] / m)


def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _finger_extended_vec(lm, mcp_idx, tip_idx):
    """
    Vector-based finger extension check (handles tilted hands).
    mcp_idx: landmark index of the MCP (knuckle base) joint.
    tip_idx: landmark index of the fingertip.
    """
    wrist = lm[0]
    mcp = lm[mcp_idx]
    tip = lm[tip_idx]

    base_vec = _vec(wrist, mcp)
    tip_vec = _vec(wrist, tip)

    dot_val = _dot(_normalize(base_vec), _normalize(tip_vec))
    tip_mag = _mag(tip_vec)
    base_mag = _mag(base_vec)

    return dot_val > FINGER_DOT_THRESHOLD and tip_mag > base_mag * FINGER_MAG_RATIO


def _thumb_extended(lm):
    """
    Thumb extension: angle at MCP (lm[2]) between lm[1]→lm[2] and lm[2]→lm[4].
    If angle > threshold, thumb is extended.
    Fallback to distance approach if degenerate.
    """
    v1 = _vec(lm[2], lm[1])
    v2 = _vec(lm[2], lm[4])
    m1, m2 = _mag(v1), _mag(v2)
    if m1 < 1e-9 or m2 < 1e-9:
        # fallback
        return distance(lm[4], lm[2]) > distance(lm[3], lm[2]) * 1.15
    cos_a = _dot(v1, v2) / (m1 * m2)
    cos_a = max(-1.0, min(1.0, cos_a))
    angle_deg = math.degrees(math.acos(cos_a))
    return angle_deg > THUMB_ANGLE_THRESHOLD


def _is_vulcan_split(lm):
    """Vulcan salute: gap between middle tip (lm[12]) and ring tip (lm[16]) > 0.10."""
    return abs(lm[12].x - lm[16].x) > 0.10


def finger_states(lm):
    """Return (thumb, index, middle, ring, pinky) as booleans."""
    thumb  = _thumb_extended(lm)
    index  = _finger_extended_vec(lm, 5, 8)
    middle = _finger_extended_vec(lm, 9, 12)
    ring   = _finger_extended_vec(lm, 13, 16)
    pinky  = _finger_extended_vec(lm, 17, 20)
    return thumb, index, middle, ring, pinky


def recognize_gesture(lm):
    """Classify a single-hand gesture from landmarks."""
    thumb, index, middle, ring, pinky = finger_states(lm)

    # ── PINCH: thumb tip and index tip very close, rest curled (before OK) ──
    pinch_dist = distance(lm[4], lm[8])
    if pinch_dist < 0.05 and not middle and not ring and not pinky:
        return "PINCH"

    # ── OK sign: thumb tip and index tip touching, others extended ──
    ok_dist = distance(lm[4], lm[8])
    if ok_dist < OK_TOUCH_THRESHOLD and middle and ring and pinky:
        return "OK"

    # ── CROSSED FINGERS: index+middle, not ring/pinky/thumb, tips close (before PEACE) ──
    if not thumb and index and middle and not ring and not pinky:
        if abs(lm[8].x - lm[12].x) < 0.05:
            return "CROSSED FINGERS"

    # ── WAVE: all 5 fingers extended including thumb (before OPEN PALM) ──
    if thumb and index and middle and ring and pinky:
        return "WAVE"

    # ── VULCAN: index+middle+ring+pinky extended, thumb curled, middle/ring split (before FOUR) ──
    if not thumb and index and middle and ring and pinky and _is_vulcan_split(lm):
        return "VULCAN"

    # ── SHAKA / Call me: thumb AND pinky, rest curled ──
    if thumb and pinky and not index and not middle and not ring:
        return "SHAKA"

    # ── ILY (I Love You): thumb + index + pinky, middle + ring curled (after SHAKA) ──
    if thumb and index and pinky and not middle and not ring:
        return "ILY"

    # ── THUMBS UP: thumb only ──
    if thumb and not index and not middle and not ring and not pinky:
        return "THUMBS UP"

    # ── FINGER GUN: thumb + index, rest curled (after THUMBS UP) ──
    if thumb and index and not middle and not ring and not pinky:
        return "FINGER GUN"

    # ── POINT DOWN: index pointing down (tip below PIP), others curled (before ONE) ──
    if not thumb and index and not middle and not ring and not pinky:
        if lm[8].y > lm[6].y:
            return "POINT DOWN"

    # ── ONE finger: index only ──
    if not thumb and index and not middle and not ring and not pinky:
        return "ONE"

    # ── PEACE: index + middle ──
    if not thumb and index and middle and not ring and not pinky:
        return "PEACE"

    # ── ROCK ON: index + pinky, middle + ring curled ──
    if index and pinky and not middle and not ring:
        return "ROCK"

    # ── THREE: index + middle + ring ──
    if not thumb and index and middle and ring and not pinky:
        return "THREE"

    # ── FOUR: index + middle + ring + pinky ──
    if not thumb and index and middle and ring and pinky:
        return "FOUR"

    # ── OPEN PALM: all four fingers ──
    if index and middle and ring and pinky:
        return "OPEN PALM"

    # ── PINKY: pinky only, all others curled (before FIST) ──
    if not thumb and not index and not middle and not ring and pinky:
        return "PINKY"

    # ── FIST: all fingers curled ──
    if not index and not middle and not ring and not pinky:
        return "FIST"

    return "UNKNOWN"


def is_heart(hand1, hand2):
    """Two-hand heart: index tips and thumbs close together."""
    i1, t1 = hand1[8], hand1[4]
    i2, t2 = hand2[8], hand2[4]
    return distance(i1, i2) < HEART_INDEX_GAP and distance(t1, t2) < HEART_THUMB_GAP


# ──────────── SOUND FEEDBACK ────────────

def _gesture_sound_params(gesture: str):
    happy = {"PEACE", "OK", "HEART", "SHAKA", "WAVE", "CROSSED FINGERS", "VULCAN", "ILY"}
    power = {"FIST", "ROCK", "FINGER GUN"}
    if gesture in happy:
        return SOUND_HAPPY
    if gesture in power:
        return SOUND_POWER
    return SOUND_NEUTRAL


def play_sound(gesture: str):
    """Play a non-blocking beep in a daemon thread."""
    freq, duration = _gesture_sound_params(gesture)
    t = threading.Thread(target=winsound.Beep, args=(freq, duration), daemon=True)
    t.start()


# ──────────── TKINTER POPUP ────────────

class PopupManager:
    """
    Manages a single borderless Tkinter popup window that slides in from
    the bottom-right corner and fades out after a hold period.
    Runs the Tk mainloop in a dedicated daemon thread.
    """

    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._outer: Optional[tk.Frame] = None
        self._emoji_lbl: Optional[tk.Label] = None
        self._name_lbl: Optional[tk.Label] = None
        self._pending_after: List[str] = []  # after() ids to cancel
        self._lock = threading.Lock()
        self._ready = threading.Event()

    # ── called from background thread ──

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        self._ready.wait(timeout=5.0)

    def _run(self):
        root = tk.Tk()
        self._root = root

        root.withdraw()
        root.wm_overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-alpha", 0.0)
        root.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}")

        # Outer frame = border colour
        outer = tk.Frame(root, bg="#00b4d8", padx=3, pady=3)
        outer.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._outer = outer

        # Inner dark frame
        inner = tk.Frame(outer, bg=DARK_BG)
        inner.pack(fill="both", expand=True)

        self._emoji_lbl = tk.Label(
            inner, text="", font=("Segoe UI Emoji", 64),
            fg="white", bg=DARK_BG
        )
        self._emoji_lbl.pack(expand=True)

        self._name_lbl = tk.Label(
            inner, text="", font=("Segoe UI", 18, "bold"),
            fg="white", bg=DARK_BG
        )
        self._name_lbl.pack(pady=(0, 10))

        self._ready.set()
        root.mainloop()

    # ── public API: called from main thread / any thread via after ──

    def show(self, gesture: str):
        """Thread-safe: schedule a popup update on the Tk thread."""
        if self._root is None:
            return
        self._root.after(0, lambda: self._show_gesture(gesture))

    def _cancel_pending(self):
        for aid in self._pending_after:
            try:
                self._root.after_cancel(aid)
            except Exception:
                pass
        self._pending_after.clear()

    def _show_gesture(self, gesture: str):
        root = self._root
        if root is None:
            return

        # Resolve display info
        info = GESTURES.get(gesture, ("(?)", gesture))
        if isinstance(info, tuple):
            ascii_icon, name = info
        else:
            ascii_icon, name = info, gesture

        # Map gesture to an emoji character for the large label
        _emoji_map = {
            "OPEN PALM":       "🖐",
            "FIST":            "✊",
            "THUMBS UP":       "👍",
            "PEACE":           "✌",
            "ONE":             "☝",
            "HEART":           "❤",
            "OK":              "👌",
            "ROCK":            "🤘",
            "SHAKA":           "🤙",
            "THREE":           "3️⃣",
            "FOUR":            "4️⃣",
            # New gestures
            "PINKY":           "🌸",
            "ILY":             "🤟",
            "VULCAN":          "🖖",
            "POINT DOWN":      "👇",
            "CROSSED FINGERS": "🤞",
            "WAVE":            "👋",
            "FINGER GUN":      "👉",
            "PINCH":           "🤌",
        }
        emoji_char = _emoji_map.get(gesture, "?")

        border_color = BORDER_COLORS.get(gesture, "#ffffff")

        self._cancel_pending()

        # Update labels + border color
        self._emoji_lbl.config(text=emoji_char)
        self._name_lbl.config(text=name)
        self._outer.config(bg=border_color)

        # Position: bottom-right corner
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = sw - POPUP_WIDTH - POPUP_MARGIN
        y_target = sh - POPUP_HEIGHT - POPUP_MARGIN
        y_start = sh  # starts below screen

        root.wm_attributes("-alpha", 1.0)
        root.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{y_start}")
        root.deiconify()

        # Slide-in animation
        step_delay = POPUP_SLIDE_MS // POPUP_SLIDE_STEPS
        y_range = y_start - y_target

        def slide_step(step):
            if step > POPUP_SLIDE_STEPS:
                # Hold, then fade
                aid = root.after(POPUP_HOLD_MS, lambda: fade_step(0))
                self._pending_after.append(aid)
                return
            progress = step / POPUP_SLIDE_STEPS
            # ease-out: progress^0.5
            eased = math.sqrt(progress)
            current_y = int(y_start - y_range * eased)
            root.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+{x}+{current_y}")
            aid = root.after(step_delay, lambda s=step + 1: slide_step(s))
            self._pending_after.append(aid)

        def fade_step(step):
            if step > POPUP_FADE_STEPS:
                root.withdraw()
                return
            alpha = 1.0 - step / POPUP_FADE_STEPS
            root.wm_attributes("-alpha", max(0.0, alpha))
            delay = POPUP_FADE_MS // POPUP_FADE_STEPS
            aid = root.after(delay, lambda s=step + 1: fade_step(s))
            self._pending_after.append(aid)

        slide_step(0)


# ──────────── DRAWING HELPERS ────────────

def _draw_text_with_bg(frame, text, org, font_scale, color, thickness,
                        bg_color=(20, 20, 20), padding=6):
    """Draw text with a filled rectangle background."""
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    x, y = org
    cv2.rectangle(
        frame,
        (x - padding, y - th - padding),
        (x + tw + padding, y + baseline + padding),
        bg_color, -1
    )
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, color, thickness, cv2.LINE_AA)


def draw_gesture_info(frame, gesture: Optional[str], candidate_count: int):
    """Main gesture info panel + confidence bar (Enhancement 3)."""
    h, w = frame.shape[:2]

    panel_x1, panel_y1 = 10, 10
    panel_x2, panel_y2 = 420, 85

    cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (20, 20, 20), -1)

    display = gesture if gesture else "NO GESTURE"
    if display == "HEART":
        display = "HEART  <3"

    cv2.putText(
        frame, f"Gesture: {display}",
        (25, 48),
        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA
    )

    # Confidence bar
    bar_x1, bar_y1 = panel_x1 + 5, panel_y1 + 55
    bar_x2, bar_y2 = panel_x2 - 5, panel_y1 + 72
    bar_width = bar_x2 - bar_x1

    cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (50, 50, 50), -1)

    ratio = min(candidate_count / CONFIRM_FRAMES, 1.0)
    filled = int(bar_width * ratio)

    if candidate_count <= 1:
        bar_color = COLOR_BAR_LOW
    elif candidate_count <= 3:
        bar_color = COLOR_BAR_MID
    else:
        bar_color = COLOR_BAR_HIGH

    if filled > 0:
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x1 + filled, bar_y2), bar_color, -1)

    cv2.putText(frame, "Confidence", (bar_x1, bar_y1 - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)


def draw_fps(frame, fps: float):
    """FPS counter in the top-right corner (Enhancement 6)."""
    h, w = frame.shape[:2]
    text = f"FPS: {fps:.1f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = w - tw - 20
    y = 30
    cv2.rectangle(frame, (x - 6, y - th - 6), (x + tw + 6, y + 6), (20, 20, 20), -1)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 2, cv2.LINE_AA)


def draw_history(frame, history: List[tuple]):
    """Gesture history sidebar on the right (Enhancement 2)."""
    h, w = frame.shape[:2]
    panel_w = 185
    panel_x = w - panel_w - 5
    panel_y = 50
    line_h = 28
    panel_h = 10 + len(history) * line_h + 10

    cv2.rectangle(frame, (panel_x, panel_y), (w - 5, panel_y + panel_h), (20, 20, 20), -1)
    cv2.putText(frame, "History", (panel_x + 8, panel_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

    for i, (label, ts) in enumerate(reversed(history)):
        y = panel_y + 28 + i * line_h
        color = (100, 255, 100) if i == 0 else (200, 200, 200)
        cv2.putText(frame, f"{label} {ts}", (panel_x + 8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)


def draw_stats(frame, stats: Dict[str, int]):
    """Bottom stats panel showing top-N gestures (Enhancement 7)."""
    h, w = frame.shape[:2]
    if not stats:
        return

    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:STATS_TOP_N]
    parts = [f"[{i+1}] {g}:{c}" for i, (g, c) in enumerate(sorted_stats)]
    text = "  ".join(parts)

    panel_y = h - 50
    cv2.rectangle(frame, (10, panel_y - 4), (w - 10, panel_y + 28), (20, 20, 20), -1)
    cv2.putText(frame, "Stats: " + text, (18, panel_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1, cv2.LINE_AA)


def draw_hud(frame, state: AppState):
    """Settings HUD in the bottom-left (Enhancement 8)."""
    h, w = frame.shape[:2]
    skel  = "ON " if state.show_skeleton else "OFF"
    hist  = "ON " if state.show_history  else "OFF"
    mute  = "OFF" if state.sound_on      else "ON "
    full  = "ON " if state.fullscreen    else "OFF"

    line1 = f"[S]keleton:{skel}  [H]istory:{hist}"
    line2 = f"[M]ute:{mute}      [F]ullscreen:{full}  [R]eset"

    y1 = h - 45
    y2 = h - 22
    cv2.rectangle(frame, (10, y1 - 16), (480, h - 8), (20, 20, 20), -1)
    cv2.putText(frame, line1, (18, y1), cv2.FONT_HERSHEY_SIMPLEX,
                0.48, (220, 220, 100), 1, cv2.LINE_AA)
    cv2.putText(frame, line2, (18, y2), cv2.FONT_HERSHEY_SIMPLEX,
                0.48, (220, 220, 100), 1, cv2.LINE_AA)


def draw_no_hand_overlay(frame, frame_count: int):
    """Pulsing 'No hand detected' text (Enhancement 9)."""
    h, w = frame.shape[:2]
    text = "No hand detected"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.1
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x = (w - tw) // 2
    y = h // 2

    # Alternate colour every PULSE_PERIOD frames
    if (frame_count // PULSE_PERIOD) % 2 == 0:
        color = (120, 120, 120)   # dim
    else:
        color = (220, 220, 220)   # bright

    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def draw_ily_rainbow(frame, frame_count: int):
    """Draw animated rainbow 'I LOVE YOU' text overlay when ILY gesture is active."""
    h, w = frame.shape[:2]
    text = "I LOVE YOU"
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 2.8
    thickness = 5

    # Rainbow palette (BGR): red, orange, yellow, green, cyan, blue, violet, pink, hot pink
    colors = [
        (0,   0,   255),   # red
        (0,   80,  255),   # orange
        (0,   200, 255),   # yellow
        (0,   255,   0),   # green
        (255, 200,   0),   # cyan
        (255,  80,   0),   # blue
        (255,   0, 180),   # violet
        (180,   0, 255),   # pink
        (80,    0, 255),   # hot pink
    ]

    # Measure total width of all printable characters
    total_width = 0
    char_widths = []
    space_advance = 0
    for ch in text:
        if ch == ' ':
            # Use 'O' width as a reasonable space width
            (sw, _), _ = cv2.getTextSize('O', font, scale, thickness)
            char_widths.append(sw)
            space_advance = sw
        else:
            (cw, _), _ = cv2.getTextSize(ch, font, scale, thickness)
            char_widths.append(cw)
        total_width += char_widths[-1]

    # Get height from a representative character
    (_, ch_h), baseline = cv2.getTextSize('A', font, scale, thickness)

    # Center position
    x_start = (w - total_width) // 2
    y_center = h // 2 + ch_h // 2

    # Semi-transparent dark background
    pad_x, pad_y = 20, 18
    bg_x1 = x_start - pad_x
    bg_y1 = y_center - ch_h - pad_y
    bg_x2 = x_start + total_width + pad_x
    bg_y2 = y_center + baseline + pad_y
    # Clamp to frame
    bg_x1 = max(0, bg_x1)
    bg_y1 = max(0, bg_y1)
    bg_x2 = min(w, bg_x2)
    bg_y2 = min(h, bg_y2)
    overlay = frame.copy()
    cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    # Draw each character with its own cycling color
    color_offset = frame_count % len(colors)
    x = x_start
    for i, ch in enumerate(text):
        color = colors[(i + color_offset) % len(colors)]
        if ch != ' ':
            cv2.putText(frame, ch, (x, y_center), font, scale, color, thickness, cv2.LINE_AA)
        x += char_widths[i]


# ──────────── MAIN ────────────

def main():
    state = AppState()
    popup_mgr = PopupManager()
    popup_mgr.start()

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("=" * 55)
        print("ERROR: Could not open your webcam.")
        print("Try closing Zoom, Teams, OBS, or any app using it.")
        print("Check Windows Settings > Privacy > Camera.")
        print("=" * 55)
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=MP_MAX_HANDS,
        min_detection_confidence=MP_DETECTION_CONF,
        min_tracking_confidence=MP_TRACKING_CONF,
    ) as hands:

        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: Could not read frame from webcam.")
                break

            frame = cv2.flip(frame, 1)
            state.frame_count += 1

            # ── FPS tracking ──
            now = time.time()
            state.frame_times.append(now)
            if len(state.frame_times) >= 2:
                elapsed = state.frame_times[-1] - state.frame_times[0]
                fps = (len(state.frame_times) - 1) / elapsed if elapsed > 0 else 0.0
            else:
                fps = 0.0

            # ── MediaPipe processing ──
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            detected = "UNKNOWN"
            hand_landmarks = []

            if result.multi_hand_landmarks:
                hand_landmarks = result.multi_hand_landmarks
                state.last_hand_time = now

                if state.show_skeleton:
                    for hand in hand_landmarks:
                        mp_draw.draw_landmarks(
                            frame, hand, mp_hands.HAND_CONNECTIONS
                        )

                # Two-hand heart
                if len(hand_landmarks) >= 2:
                    if is_heart(hand_landmarks[0].landmark, hand_landmarks[1].landmark):
                        detected = "HEART"

                # Single-hand recognition
                if detected == "UNKNOWN" and hand_landmarks:
                    detected = recognize_gesture(hand_landmarks[0].landmark)

            # ── Gesture confirmation ──
            if detected == state.candidate:
                state.candidate_count += 1
            else:
                state.candidate = detected
                state.candidate_count = 1

            if state.candidate_count >= CONFIRM_FRAMES and state.candidate != state.stable_gesture:
                state.stable_gesture = state.candidate

                if state.stable_gesture in GESTURES:
                    # Popup
                    popup_mgr.show(state.stable_gesture)

                    # Sound
                    if state.sound_on:
                        play_sound(state.stable_gesture)

                    # History
                    ts = time.strftime("%H:%M:%S")
                    label = GESTURE_LABELS.get(state.stable_gesture, state.stable_gesture)
                    state.history.append((label, ts))
                    if len(state.history) > HISTORY_MAX:
                        state.history.pop(0)

                    # Stats
                    state.stats[state.stable_gesture] = state.stats.get(state.stable_gesture, 0) + 1

            # ── Drawing ──
            draw_gesture_info(frame, state.stable_gesture, state.candidate_count)
            if state.stable_gesture == "ILY":
                draw_ily_rainbow(frame, state.frame_count)
            draw_fps(frame, fps)

            if state.show_history and state.history:
                draw_history(frame, state.history)

            draw_stats(frame, state.stats)
            draw_hud(frame, state)

            # No-hand timeout overlay
            if now - state.last_hand_time >= NO_HAND_TIMEOUT:
                draw_no_hand_overlay(frame, state.frame_count)

            cv2.imshow(WINDOW_TITLE, frame)

            # ── Keyboard shortcuts ──
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break
            elif key == ord("s") or key == ord("S"):
                state.show_skeleton = not state.show_skeleton
            elif key == ord("h") or key == ord("H"):
                state.show_history = not state.show_history
            elif key == ord("m") or key == ord("M"):
                state.sound_on = not state.sound_on
            elif key == ord("r") or key == ord("R"):
                state.stats.clear()
                state.history.clear()
                state.stable_gesture = None
                state.candidate = None
                state.candidate_count = 0
            elif key == ord("f") or key == ord("F"):
                state.fullscreen = not state.fullscreen
                prop = (cv2.WND_PROP_FULLSCREEN
                        if state.fullscreen else cv2.WINDOW_NORMAL)
                cv2.setWindowProperty(
                    WINDOW_TITLE,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN if state.fullscreen else cv2.WINDOW_NORMAL
                )

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
