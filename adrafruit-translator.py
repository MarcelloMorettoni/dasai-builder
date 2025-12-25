import numpy as np
import cv2
import imageio.v2 as imageio
import gradio as gr

# ===============================
# SSD1306 EMULATOR
# ===============================

WHITE = 255
BLACK = 0
W, H = 128, 64

class OLED:
    def __init__(self):
        self.clearDisplay()

    def clearDisplay(self):
        self.img = np.zeros((H, W), dtype=np.uint8)

    def display(self):
        return self.img.copy()

    def fillRoundRect(self, x, y, w, h, r, color):
        cv2.rectangle(self.img, (x+r, y), (x+w-r, y+h), color, -1)
        cv2.rectangle(self.img, (x, y+r), (x+w, y+h-r), color, -1)
        cv2.circle(self.img, (x+r, y+r), r, color, -1)
        cv2.circle(self.img, (x+w-r, y+r), r, color, -1)
        cv2.circle(self.img, (x+r, y+h-r), r, color, -1)
        cv2.circle(self.img, (x+w-r, y+h-r), r, color, -1)

    def fillTriangle(self, pts, color):
        cv2.fillPoly(self.img, [np.array(pts)], color)

    def fillRect(self, x, y, w, h, color):
        cv2.rectangle(self.img, (x,y), (x+w, y+h), color, -1)

    def drawLine(self, x1,y1,x2,y2,color):
        cv2.line(self.img, (x1,y1), (x2,y2), color, 1)

    def fillCircle(self, x, y, r, color):
        cv2.circle(self.img, (x, y), r, color, -1)

# ===============================
# EYE GEOMETRY (from Arduino)
# ===============================

ref_w, ref_h = 40, 40
space = 10
corner = 10

left_eye  = {"x": 64 - ref_w//2 - space//2, "y": 32, "w": ref_w, "h": ref_h}
right_eye = {"x": 64 + ref_w//2 + space//2, "y": 32, "w": ref_w, "h": ref_h}

# ===============================
# DRAWING FUNCTIONS
# ===============================

def drawEyes(oled, frames):
    oled.clearDisplay()
    for eye in (left_eye, right_eye):
        x = eye["x"] - eye["w"]//2
        y = eye["y"] - eye["h"]//2
        oled.fillRoundRect(x, y, eye["w"], eye["h"], corner, WHITE)
    frames.append(oled.display())

def centerEyes():
    for eye in (left_eye, right_eye):
        eye["w"] = ref_w
        eye["h"] = ref_h
        eye["y"] = 32

def blink(oled, frames, speed=8):
    centerEyes()
    for _ in range(3):
        left_eye["h"] -= speed
        right_eye["h"] -= speed
        drawEyes(oled, frames)
    for _ in range(3):
        left_eye["h"] += speed
        right_eye["h"] += speed
        drawEyes(oled, frames)

def happyEye(oled, frames):
    centerEyes()
    drawEyes(oled, frames)
    offset = ref_h // 2
    for _ in range(10):
        oled.fillTriangle([
            (left_eye["x"]-ref_w//2, left_eye["y"]+offset),
            (left_eye["x"]+ref_w//2, left_eye["y"]+offset+6),
            (left_eye["x"]-ref_w//2, left_eye["y"]+ref_h+offset)
        ], BLACK)

        oled.fillTriangle([
            (right_eye["x"]+ref_w//2, right_eye["y"]+offset),
            (right_eye["x"]-ref_w//2, right_eye["y"]+offset+6),
            (right_eye["x"]+ref_w//2, right_eye["y"]+ref_h+offset)
        ], BLACK)

        frames.append(oled.display())
        offset -= 2

def sadEye(oled, frames):
    centerEyes()
    drawEyes(oled, frames)

    offset = ref_h // 2

    for _ in range(10):
        # Left eye eyebrow
        oled.fillTriangle([
            (left_eye["x"] - left_eye["w"]//2 - 1, left_eye["y"] - offset),
            (left_eye["x"] + left_eye["w"]//2 + 1, left_eye["y"] - 5 - offset),
            (left_eye["x"] - left_eye["w"]//2 - 1, left_eye["y"] - 10 - offset)
        ], BLACK)

        # Right eye eyebrow
        oled.fillTriangle([
            (right_eye["x"] + right_eye["w"]//2 + 1, right_eye["y"] - offset),
            (right_eye["x"] - right_eye["w"]//2 - 1, right_eye["y"] - 5 - offset),
            (right_eye["x"] + right_eye["w"]//2 + 1, right_eye["y"] - 10 - offset)
        ], BLACK)

        # Bottom eyelids
        oled.drawLine(
            left_eye["x"] - left_eye["w"]//2 + 2,
            left_eye["y"] + left_eye["h"]//2,
            left_eye["x"] + left_eye["w"]//2 - 2,
            left_eye["y"] + left_eye["h"]//2,
            BLACK
        )

        oled.drawLine(
            right_eye["x"] - right_eye["w"]//2 + 2,
            right_eye["y"] + right_eye["h"]//2,
            right_eye["x"] + right_eye["w"]//2 - 2,
            right_eye["y"] + right_eye["h"]//2,
            BLACK
        )

        frames.append(oled.display())
        offset -= 1

    # Hold final pose (~1000ms)
    for _ in range(30):
        frames.append(oled.display())

def angryEye(oled, frames):
    centerEyes()
    drawEyes(oled, frames)

    offset = ref_h // 2

    for _ in range(10):
        # Left angry brow
        oled.fillTriangle([
            (left_eye["x"] - left_eye["w"]//2 - 1, left_eye["y"] - 10 - offset),
            (left_eye["x"] + left_eye["w"]//2 + 1, left_eye["y"] - offset),
            (left_eye["x"] + left_eye["w"]//2 + 1, left_eye["y"] - 10 - offset)
        ], BLACK)

        # Right angry brow
        oled.fillTriangle([
            (right_eye["x"] + right_eye["w"]//2 + 1, right_eye["y"] - 10 - offset),
            (right_eye["x"] - right_eye["w"]//2 - 1, right_eye["y"] - offset),
            (right_eye["x"] - right_eye["w"]//2 - 1, right_eye["y"] - 10 - offset)
        ], BLACK)

        frames.append(oled.display())
        offset -= 1

    # Hold pose (~1000 ms)
    for _ in range(30):
        frames.append(oled.display())


def tiredEye(oled, frames):
    centerEyes()
    drawEyes(oled, frames)

    offset = ref_h // 2

    for _ in range(10):
        # Upper eyelids
        oled.fillRect(
            left_eye["x"] - left_eye["w"]//2 - 1,
            left_eye["y"] - offset,
            left_eye["w"] + 2,
            left_eye["h"] // 3,
            BLACK
        )

        oled.fillRect(
            right_eye["x"] - right_eye["w"]//2 - 1,
            right_eye["y"] - offset,
            right_eye["w"] + 2,
            right_eye["h"] // 3,
            BLACK
        )

        # Lower sleepy lines
        oled.drawLine(
            left_eye["x"] - left_eye["w"]//2 + 2,
            left_eye["y"] + left_eye["h"]//2 + 2,
            left_eye["x"] - left_eye["w"]//2 + 8,
            left_eye["y"] + left_eye["h"]//2 + 2,
            BLACK
        )

        oled.drawLine(
            right_eye["x"] - right_eye["w"]//2 + 2,
            right_eye["y"] + right_eye["h"]//2 + 2,
            right_eye["x"] - right_eye["w"]//2 + 8,
            right_eye["y"] + right_eye["h"]//2 + 2,
            BLACK
        )

        frames.append(oled.display())
        offset -= 1

    # Hold pose (~1000 ms)
    for _ in range(30):
        frames.append(oled.display())

def saccade(oled, frames, direction_x, direction_y):
    dx_amp = 8
    dy_amp = 6
    blink_amp = 8

    # First micro-movement + blink
    left_eye["x"]  += dx_amp * direction_x
    right_eye["x"] += dx_amp * direction_x
    left_eye["y"]  += dy_amp * direction_y
    right_eye["y"] += dy_amp * direction_y

    left_eye["h"]  -= blink_amp
    right_eye["h"] -= blink_amp

    drawEyes(oled, frames)

    # Hold ~40ms
    for _ in range(2):
        frames.append(oled.display())

    # Second micro-movement + open
    left_eye["x"]  += dx_amp * direction_x
    right_eye["x"] += dx_amp * direction_x
    left_eye["y"]  += dy_amp * direction_y
    right_eye["y"] += dy_amp * direction_y

    left_eye["h"]  += blink_amp
    right_eye["h"] += blink_amp

    drawEyes(oled, frames)

    # Hold ~60ms
    for _ in range(3):
        frames.append(oled.display())

def glance(oled, frames, dx, dy):
    saccade(oled, frames, dx, dy)
    centerEyes()
    drawEyes(oled, frames)

def lookAround(oled, frames):
    # emulate Arduino performRandomGlances(2–3)
    directions = [(-1,0), (1,0), (0,-1)]
    np.random.shuffle(directions)

    for dx, dy in directions[:np.random.randint(2,4)]:
        glance(oled, frames, dx, dy)

def heart_eye(oled, frames):
    centerEyes()
    size = 6      # heart size
    steps = 5     # animation smoothness

    # Clear old eye shapes (exactly like Arduino)
    oled.clearDisplay()
    frames.append(oled.display())

    for grow in range(steps):
        # LEFT HEART
        lx = left_eye["x"]
        ly = left_eye["y"]

        oled.fillCircle(
            lx - size//2 - grow,
            ly - size//2 - grow,
            size//2 + grow,
            WHITE
        )
        oled.fillCircle(
            lx + size//2 + grow,
            ly - size//2 - grow,
            size//2 + grow,
            WHITE
        )
        oled.fillTriangle([
            (lx - size - 1 - grow, ly - size//4 - grow),
            (lx + size + 1 + grow, ly - size//4 - grow),
            (lx, ly + size + 2 + grow)
        ], WHITE)

        # RIGHT HEART
        rx = right_eye["x"]
        ry = right_eye["y"]

        oled.fillCircle(
            rx - size//2 - grow,
            ry - size//2 - grow,
            size//2 + grow,
            WHITE
        )
        oled.fillCircle(
            rx + size//2 + grow,
            ry - size//2 - grow,
            size//2 + grow,
            WHITE
        )
        oled.fillTriangle([
            (rx - size - 1 - grow, ry - size//4 - grow),
            (rx + size + 1 + grow, ry - size//4 - grow),
            (rx, ry + size + 2 + grow)
        ], WHITE)

        frames.append(oled.display())

    # Hold hearts visible (~1200 ms)
    for _ in range(36):  # ~1.2s @ 30fps
        frames.append(oled.display())

def sleepingEye(oled, frames):
    centerEyes()

    # Step 1: slowly close eyes
    steps = 10
    for i in range(steps):
        left_eye["h"]  = ref_h - i * (ref_h // steps)
        right_eye["h"] = ref_h - i * (ref_h // steps)
        drawEyes(oled, frames)

    # Step 2: hold closed eyes
    for _ in range(30):  # ~1 second @ 30 fps
        frames.append(oled.display())

    # Step 3: subtle breathing blink loop
    for _ in range(3):  # number of micro-blinks
        # micro open
        left_eye["h"]  += 4
        right_eye["h"] += 4
        drawEyes(oled, frames)

        for _ in range(6):
            frames.append(oled.display())

        # micro close
        left_eye["h"]  -= 4
        right_eye["h"] -= 4
        drawEyes(oled, frames)

        for _ in range(12):
            frames.append(oled.display())

    # Step 4: end fully closed (important!)
    left_eye["h"]  = ref_h // 6
    right_eye["h"] = ref_h // 6
    drawEyes(oled, frames)

# ===============================
# FRAMES → MP4
# ===============================

def frames_to_mp4(frames, path="oled.mp4", fps=30):
    frames_rgb = [
        cv2.cvtColor(f, cv2.COLOR_GRAY2RGB)
        for f in frames
    ]
    imageio.mimsave(path, frames_rgb, fps=fps)
    return path

# ===============================
# GRADIO APP
# ===============================

# ===============================
# GRADIO APP
# ===============================

def run(expr):
    oled = OLED()
    frames = []

    if expr == "center":
        centerEyes()
        drawEyes(oled, frames)

    elif expr == "blink":
        drawEyes(oled, frames)
        blink(oled, frames)

    elif expr == "happy":
        happyEye(oled, frames)

    elif expr == "sad":
        sadEye(oled, frames)

    elif expr == "angry":
        angryEye(oled, frames)

    elif expr == "tired":
        tiredEye(oled, frames)

    elif expr == "heart_eye":
        heart_eye(oled, frames)

    elif expr == "look_left":
        glance(oled, frames, -1, 0)

    elif expr == "look_right":
        glance(oled, frames, 1, 0)

    elif expr == "look_up":
        glance(oled, frames, 0, -1)

    elif expr == "look_around":
        lookAround(oled, frames)

    elif expr == "sleeping":
        sleepingEye(oled, frames)


    return frames_to_mp4(frames)



gr.Interface(
    fn=run,
    inputs=gr.Dropdown(
        [
            "center",
            "blink",
            "happy",
            "sad",
            "angry",
            "tired",
            "heart_eye",
            "look_left",
            "look_right",
            "look_up",
            "look_around",
            "sleeping"
        ],
        label="Expression / Gaze"
    ),
    outputs=gr.Video(),
    title="Adafruit SSD1306 → MP4 Emulator"
).launch()
