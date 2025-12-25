import cv2
import tempfile
import os
import re
import gradio as gr
import numpy as np
from PIL import Image

# ===============================
# CONSTANTS
# ===============================
WIDTH, HEIGHT = 128, 64
ROW_BYTES = WIDTH // 8

BASE_IDLE = ["center", "blink", "look_left", "look_right", "look_up"]
BASE_EXPR = ["happy", "sad", "angry", "tired", "heart", "sleeping"]

# ===============================
# HELPERS
# ===============================
def sanitize(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    if name and name[0].isdigit():
        name = "_" + name
    return name

# ===============================
# IMAGE → XBM
# ===============================
def to_bw(img, threshold=128):
    img = img.resize((WIDTH, HEIGHT))
    g = np.array(img.convert("L"))
    bw = (g >= threshold).astype(np.uint8) * 255
    return Image.fromarray(bw, mode="L").convert("1")

def image_to_xbm(img):
    data = []
    for y in range(HEIGHT):
        for xb in range(ROW_BYTES):
            b = 0
            for bit in range(8):
                if img.getpixel((xb * 8 + bit, y)) == 255:
                    b |= (1 << bit)
            data.append(b)
    return data

def format_bitmap(name, idx, data):
    body = []
    for i in range(0, len(data), 16):
        body.append("  " + ", ".join(f"0x{b:02X}" for b in data[i:i+16]) + ",")
    return f"""
const unsigned char epd_{name}_{idx}[] PROGMEM = {{
{chr(10).join(body)}
}};
"""

def process_video(video_path, name):
    cap = cv2.VideoCapture(video_path)
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        bw = to_bw(img)
        frames.append(format_bitmap(name, idx, image_to_xbm(bw)))
        idx += 1
    cap.release()
    return frames, idx

# ===============================
# ARDUINO GENERATOR
# ===============================
def generate_code(intro_video, *all_inputs):
    idle_count = len(BASE_IDLE)
    expr_count = len(BASE_EXPR)

    idle_videos = all_inputs[:idle_count]
    expr_videos = all_inputs[idle_count:idle_count + expr_count]
    extra_idle = all_inputs[idle_count + expr_count]
    extra_expr = all_inputs[idle_count + expr_count + 1]

    bitmaps = []
    animations = []
    idle_names = []
    expr_names = []

    # ---------- INTRO ----------
    if intro_video:
        frames, count = process_video(intro_video, "intro")
        bitmaps += frames
        animations.append(f"""
const unsigned char* const ANIM_INTRO[] PROGMEM = {{
{", ".join(f"epd_intro_{i}" for i in range(count))}
}};
Animation anim_intro = {{ ANIM_INTRO, {count}, MS_DELAY }};
""")

    # ---------- BASE IDLE ----------
    for name, video in zip(BASE_IDLE, idle_videos):
        if video:
            frames, count = process_video(video, name)
            bitmaps += frames
            idle_names.append(name)
            animations.append(f"""
const unsigned char* const ANIM_{name.upper()}[] PROGMEM = {{
{", ".join(f"epd_{name}_{i}" for i in range(count))}
}};
Animation anim_{name} = {{ ANIM_{name.upper()}, {count}, MS_DELAY }};
""")

    # ---------- BASE EXPRESSIONS ----------
    for name, video in zip(BASE_EXPR, expr_videos):
        if video:
            frames, count = process_video(video, name)
            bitmaps += frames
            expr_names.append(name)
            animations.append(f"""
const unsigned char* const ANIM_{name.upper()}[] PROGMEM = {{
{", ".join(f"epd_{name}_{i}" for i in range(count))}
}};
Animation anim_{name} = {{ ANIM_{name.upper()}, {count}, MS_DELAY }};
""")

    # ---------- EXTRA IDLE ----------
    for name, video in extra_idle:
        if name and video:
            name = sanitize(name)
            frames, count = process_video(video, name)
            bitmaps += frames
            idle_names.append(name)
            animations.append(f"""
const unsigned char* const ANIM_{name.upper()}[] PROGMEM = {{
{", ".join(f"epd_{name}_{i}" for i in range(count))}
}};
Animation anim_{name} = {{ ANIM_{name.upper()}, {count}, MS_DELAY }};
""")

    # ---------- EXTRA EXPRESSIONS ----------
    for name, video in extra_expr:
        if name and video:
            name = sanitize(name)
            frames, count = process_video(video, name)
            bitmaps += frames
            expr_names.append(name)
            animations.append(f"""
const unsigned char* const ANIM_{name.upper()}[] PROGMEM = {{
{", ".join(f"epd_{name}_{i}" for i in range(count))}
}};
Animation anim_{name} = {{ ANIM_{name.upper()}, {count}, MS_DELAY }};
""")

    ino = f"""
#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

#define BTN_D1 D1
#define MS_DELAY 10

struct Animation {{
  const unsigned char* const* frames;
  uint8_t count;
  uint16_t delayMs;
}};

{''.join(bitmaps)}

{''.join(animations)}
"""

    path = os.path.join(tempfile.gettempdir(), "face.ino")
    with open(path, "w") as f:
        f.write(ino)

    return path

# ===============================
# UI
# ===============================
with gr.Blocks(title="Face → Arduino Generator") as demo:
    gr.Markdown("## 🚀 Power-on Intro")
    intro = gr.Video(label="Intro (optional)")

    gr.Markdown("## 💤 Idle (baseline)")
    idle_inputs = [gr.Video(label=n.replace("_", " ").title()) for n in BASE_IDLE]

    gr.Markdown("## 🎭 Expressions (baseline)")
    expr_inputs = [gr.Video(label=n.replace("_", " ").title()) for n in BASE_EXPR]

    gr.Markdown("## ➕ Extra Idle (optional)")
    extra_idle = gr.State([])
    idle_name = gr.Textbox(label="Idle name")
    idle_video = gr.Video(label="Idle video")
    gr.Button("Add Idle").click(
        lambda n, v, s: s + [(n, v)],
        [idle_name, idle_video, extra_idle],
        extra_idle,
    )

    gr.Markdown("## ➕ Extra Expressions (optional)")
    extra_expr = gr.State([])
    expr_name = gr.Textbox(label="Expression name")
    expr_video = gr.Video(label="Expression video")
    gr.Button("Add Expression").click(
        lambda n, v, s: s + [(n, v)],
        [expr_name, expr_video, extra_expr],
        extra_expr,
    )

    out = gr.File(label="Download face.ino")

    gr.Button("Generate Arduino").click(
        generate_code,
        [intro] + idle_inputs + expr_inputs + [extra_idle, extra_expr],
        out,
    )

demo.launch()

