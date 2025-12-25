import gradio as gr
import numpy as np
from PIL import Image

WIDTH = 128
HEIGHT = 64
ROW_BYTES = WIDTH // 8


# ----------------------------
# Bitmap logic (u8g2.drawXBMP)
# ----------------------------

def to_bw(img: Image.Image) -> Image.Image:
    img = img.resize((WIDTH, HEIGHT))
    img = img.convert("L")
    arr = np.array(img)
    bw = (arr > 128).astype(np.uint8) * 255
    return Image.fromarray(bw, mode="L").convert("1")


def image_to_xbm_bytes(img: Image.Image):
    img = img.resize((WIDTH, HEIGHT)).convert("1")
    data = []

    for y in range(HEIGHT):
        for xb in range(ROW_BYTES):
            byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                if img.getpixel((x, y)) == 255:
                    byte |= (1 << bit)   # LSB = leftmost
            data.append(byte)

    return data


def xbm_bytes_to_image(data):
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    idx = 0

    for y in range(HEIGHT):
        for xb in range(ROW_BYTES):
            b = data[idx]
            idx += 1
            for bit in range(8):
                x = xb * 8 + bit
                arr[y, x] = 255 if (b & (1 << bit)) else 0

    return Image.fromarray(arr, mode="L")


def format_c_array(data, frame):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        lines.append("\t" + ", ".join(f"0x{b:02X}" for b in chunk) + ",")
    return (
        f"const unsigned char epd_bitmap_{frame} [] PROGMEM = {{\n"
        + "\n".join(lines)
        + "\n};"
    )


# ----------------------------
# Gradio callback
# ----------------------------

def generate(img, frame_index):
    if img is None:
        return None, None, ""

    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)

    bw = to_bw(img)
    data = image_to_xbm_bytes(bw)
    decoded = xbm_bytes_to_image(data)
    code = format_c_array(data, int(frame_index))

    return bw, decoded, code


# ----------------------------
# UI (guaranteed compatible)
# ----------------------------

demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Image(type="pil", label="Upload expression (128×64 PNG recommended)"),
        gr.Number(value=0, precision=0, label="Frame index"),
    ],
    outputs=[
        gr.Image(label="Binarized (packed)"),
        gr.Image(label="OLED preview (u8g2 accurate)"),
        gr.Textbox(lines=20, label="Arduino bitmap"),
    ],
    title="u8g2 Bitmap Converter (SOLID)",
    description=(
        "Upload a black/white image.\n"
        "White = ON, Black = OFF.\n"
        "Output matches u8g2.drawXBMP exactly."
    ),
)

demo.launch()
