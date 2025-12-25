import gradio as gr
import numpy as np
import cv2
import tempfile
from PIL import Image, ImageDraw

# ===============================
# CONSTANTS
# ===============================
WIDTH, HEIGHT = 128, 64
BG = 0
FG = 255

# ===============================
# DRAWING
# ===============================
def draw_eye_frame(p):
    img = Image.new("L", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)

    cx, cy = WIDTH // 2, HEIGHT // 2
    ew = int(p["eye_width"] * 18)
    eh = int(p["eye_height"] * 10)
    spacing = int(p["eye_spacing"] * 20)

    def draw_one(xc, tilt):
        bbox = [xc - ew, cy - eh, xc + ew, cy + eh]
        r = int(p["bevel"] * min(ew, eh))

        # Eye body (filled robotic eye)
        if p["roundness"] > 0.95:
            d.ellipse(bbox, fill=FG)
        else:
            d.rounded_rectangle(bbox, radius=r, fill=FG)

        # Upper lid
        ul = int((1 - p["openness"] + p["upper_lid"]) * eh * 2)
        if ul > 0:
            d.rectangle([xc - ew, cy - eh, xc + ew, cy - eh + ul], fill=BG)

        # Lower lid
        ll = int(p["lower_lid"] * eh * 2)
        if ll > 0:
            d.rectangle([xc - ew, cy + eh - ll, xc + ew, cy + eh], fill=BG)

        # Eyebrow
        by = cy - eh - int(p["brow_height"] * 12)
        d.line(
            [xc - ew, by + tilt * 8, xc + ew, by - tilt * 8],
            fill=FG,
            width=2
        )

    draw_one(cx - spacing, p["tilt_left"])
    draw_one(cx + spacing, p["tilt_right"])

    return img

# ===============================
# INTERPOLATION
# ===============================
def lerp(a, b, t):
    return a + (b - a) * t

def interpolate_params(a, b, t):
    return {k: lerp(a[k], b[k], t) for k in a}

# ===============================
# VIDEO GENERATION (EXACT TIMING + PINGPONG)
# ===============================
def generate_animation(start, end, duration_sec, fps, pingpong):
    total_frames = max(2, int(duration_sec * fps))

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)

    writer = cv2.VideoWriter(
        tmp.name,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (WIDTH, HEIGHT),
        True
    )

    for i in range(total_frames):
        t = i / (total_frames - 1)

        if pingpong:
            if t <= 0.5:
                tt = t * 2
            else:
                tt = 2 - t * 2
        else:
            tt = t

        p = interpolate_params(start, end, tt)
        frame = draw_eye_frame(p).convert("RGB")
        writer.write(np.array(frame))

    writer.release()
    return tmp.name

# ===============================
# GRADIO CALLBACK
# ===============================
def build_all(duration, fps, pingpong, *vals):
    keys = [
        "openness", "upper_lid", "lower_lid",
        "gaze_x", "gaze_y",
        "tilt_left", "tilt_right",
        "brow_height",
        "roundness", "bevel",
        "eye_spacing", "eye_width", "eye_height"
    ]

    mid = len(keys)
    start = dict(zip(keys, vals[:mid]))
    end = dict(zip(keys, vals[mid:]))

    start_img = draw_eye_frame(start)
    end_img = draw_eye_frame(end)

    video = generate_animation(
        start=start,
        end=end,
        duration_sec=duration,
        fps=fps,
        pingpong=pingpong
    )

    return start_img, end_img, video

# COPY END → START
def copy_end_to_start(*end_vals):
    return list(end_vals)

# ===============================
# UI
# ===============================
with gr.Blocks(title="🧠 Eye Transition Designer") as demo:
    gr.Markdown("## 👁️ Eye Transition Animator")

    with gr.Row():
        duration = gr.Slider(0.5, 10, 2.0, step=0.1, label="Duration (seconds)")
        fps = gr.Slider(12, 60, 24, step=1, label="FPS")

    pingpong = gr.Checkbox(
        label="🔁 Ping-Pong (Start → End → Start)",
        value=False
    )

    def controls(title):
        with gr.Column():
            gr.Markdown(f"### {title}")
            return [
                gr.Slider(0, 1, 0.8, label="Openness"),
                gr.Slider(0, 1, 0.0, label="Upper Lid"),
                gr.Slider(0, 1, 0.0, label="Lower Lid"),
                gr.Slider(-1, 1, 0.0, label="Gaze X"),
                gr.Slider(-1, 1, 0.0, label="Gaze Y"),
                gr.Slider(-1, 1, 0.0, label="Tilt Left"),
                gr.Slider(-1, 1, 0.0, label="Tilt Right"),
                gr.Slider(0, 1, 0.4, label="Brow Height"),
                gr.Slider(0, 1, 0.3, label="Roundness"),
                gr.Slider(0, 1, 0.25, label="Bevel"),
                gr.Slider(0.6, 1.4, 1.0, label="Eye Spacing"),
                gr.Slider(0.6, 1.4, 1.0, label="Eye Width"),
                gr.Slider(0.6, 1.4, 1.0, label="Eye Height"),
            ]

    with gr.Row():
        start_controls = controls("START (Current Pose)")
        end_controls = controls("END (Target Pose)")

    with gr.Row():
        copy_btn = gr.Button("⬅️ Use END as START")
        gen_btn = gr.Button("🎬 Generate Animation")

    with gr.Row():
        start_preview = gr.Image(label="Start Frame", image_mode="L")
        end_preview = gr.Image(label="End Frame", image_mode="L")

    video = gr.Video(label="Generated Animation")

    copy_btn.click(
        copy_end_to_start,
        inputs=end_controls,
        outputs=start_controls
    )

    gen_btn.click(
        build_all,
        inputs=[duration, fps, pingpong] + start_controls + end_controls,
        outputs=[start_preview, end_preview, video]
    )

demo.launch()
