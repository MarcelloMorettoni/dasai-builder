import re
import os
import shutil
import tempfile
import cv2
import gradio as gr
import numpy as np
from PIL import Image

WIDTH = 128
HEIGHT = 64
BYTES_EXPECTED = (WIDTH * HEIGHT) // 8  # 1024
ROW_BYTES = WIDTH // 8  # 16


# ----------------------------
# Helpers
# ----------------------------
def to_bw(img: Image.Image, threshold: int, invert: bool) -> Image.Image:
    """Return a 1-bit image (mode '1') used for packing."""
    # Ensure resize happens before conversion to preserve detail
    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    g = img.convert("L")
    arr = np.array(g, dtype=np.uint8)

    if invert:
        arr = 255 - arr

    bw = (arr >= threshold).astype(np.uint8) * 255  # white=255, black=0
    return Image.fromarray(bw, mode="L").convert("1")


def image_to_xbm_bytes(img: Image.Image, white_is_on: bool = True) -> list[int]:
    """
    Pack to XBM format as expected by u8g2.drawXBMP():
    - Row-major: for each y row, for each byte across X
    - Bit order: LSB is leftmost pixel (standard XBM)
    - If white_is_on=True: white pixels -> 1 bits, else black pixels -> 1 bits
    """
    # Force resize/convert just in case, though to_bw usually handles it
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT)).convert("1")

    data = []
    for y in range(HEIGHT):
        for xb in range(ROW_BYTES):
            byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                px = img.getpixel((x, y))  # 0 or 255
                is_white = (px == 255)
                on = is_white if white_is_on else (not is_white)
                if on:
                    byte |= (1 << bit)  # LSB = leftmost
            data.append(byte)

    return data


def xbm_bytes_to_image(data: list[int], on_is_white: bool = True) -> Image.Image:
    """
    Decode XBM row-major bytes back to an image (u8g2.drawXBMP accurate).
    """
    if len(data) != BYTES_EXPECTED:
        raise ValueError(f"Expected {BYTES_EXPECTED} bytes, got {len(data)}")

    arr = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

    idx = 0
    for y in range(HEIGHT):
        for xb in range(ROW_BYTES):
            byte = data[idx]
            idx += 1
            for bit in range(8):
                x = xb * 8 + bit
                is_on = (byte & (1 << bit)) != 0
                if on_is_white:
                    arr[y, x] = 255 if is_on else 0
                else:
                    arr[y, x] = 0 if is_on else 255

    return Image.fromarray(arr, mode="L")


def format_c_array(data: list[int], frame_index: int) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        lines.append("\t" + ", ".join(f"0x{b:02X}" for b in chunk) + ",")
    return (
        f"const unsigned char epd_bitmap_{frame_index} [] PROGMEM = {{\n"
        + "\n".join(lines)
        + "\n};"
    )


def hex_snippet(data: list[int], n: int = 256) -> str:
    n = max(16, min(n, len(data)))
    out = []
    for i in range(0, n, 16):
        chunk = data[i:i + 16]
        out.append(" ".join(f"{b:02X}" for b in chunk))
    return "\n".join(out)


def bit_stats(data: list[int]) -> str:
    # Count ON bits per 8-row band for easier debugging
    bands = HEIGHT // 8
    counts = [0] * bands

    idx = 0
    for y in range(HEIGHT):
        band = y // 8
        for _ in range(ROW_BYTES):
            b = data[idx]
            idx += 1
            counts[band] += int(bin(b).count("1"))

    total = sum(counts)
    lines = [f"Total ON bits: {total} (out of {WIDTH*HEIGHT})"]
    for b, c in enumerate(counts):
        lines.append(f"Band {b:02d} (rows {b*8:02d}-{b*8+7:02d}): {c} bits ON")
    return "\n".join(lines)


def parse_c_array(text: str) -> list[int]:
    hex_bytes = re.findall(r"0x[0-9a-fA-F]{1,2}", text)
    if hex_bytes:
        data = [int(h, 16) for h in hex_bytes]
    else:
        nums = re.findall(r"\b\d+\b", text)
        data = [int(n) & 0xFF for n in nums]

    if len(data) != BYTES_EXPECTED:
        raise ValueError(f"Expected {BYTES_EXPECTED} bytes, got {len(data)}")
    return data


# ----------------------------
# Video Processing Logic
# ----------------------------
def process_video_file(video_path, threshold, invert, white_is_on):
    if not video_path:
        return None, None, "No video uploaded."

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None, "Could not open video file."

    # Create a temporary directory for frames
    temp_dir = tempfile.mkdtemp()
    
    all_code = []
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert BGR (OpenCV) to RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            
            # Use existing helpers
            bw_img = to_bw(pil_img, int(threshold), invert)
            data = image_to_xbm_bytes(bw_img, white_is_on)
            
            # Generate Code
            c_code = format_c_array(data, frame_count)
            all_code.append(c_code)
            
            # Save PNG Frame
            filename = os.path.join(temp_dir, f"frame_{frame_count:04d}.png")
            bw_img.save(filename)
            
            frame_count += 1
        
        cap.release()
        
        # Create Zip of PNGs
        zip_filename = os.path.join(tempfile.gettempdir(), "mochi_frames")
        shutil.make_archive(zip_filename, 'zip', temp_dir)
        zip_output_path = zip_filename + ".zip"
        
        # Create Text file of Code
        code_output_path = os.path.join(tempfile.gettempdir(), "animation_code.c")
        with open(code_output_path, "w") as f:
            f.write(f"// Generated {frame_count} frames\n")
            f.write(f"// Size: {WIDTH}x{HEIGHT}\n\n")
            f.write("\n\n".join(all_code))
            
        status = f"Success! Processed {frame_count} frames."
        
        return code_output_path, zip_output_path, status

    except Exception as e:
        return None, None, f"Error processing video: {str(e)}"
    finally:
        # Cleanup temp directory containing individual pngs
        shutil.rmtree(temp_dir)


# ----------------------------
# Gradio callbacks
# ----------------------------
def convert_with_debug(image, frame_index, threshold, invert_input, white_is_on, preview_on_is_white, snippet_len):
    if image is None:
        return None, None, "", "", "Upload an image."

    bw = to_bw(image, threshold=int(threshold), invert=bool(invert_input))
    data = image_to_xbm_bytes(bw, white_is_on=bool(white_is_on))
    decoded = xbm_bytes_to_image(data, on_is_white=bool(preview_on_is_white))

    code = format_c_array(data, int(frame_index))
    snippet = hex_snippet(data, int(snippet_len))
    stats = bit_stats(data)

    return bw, decoded, code, snippet, stats


def render_pasted_array(c_array_text, preview_on_is_white):
    if not c_array_text.strip():
        return None, "Paste a C array first."
    try:
        data = parse_c_array(c_array_text)
        img = xbm_bytes_to_image(data, on_is_white=bool(preview_on_is_white))
        return img, "OK"
    except Exception as e:
        return None, f"Error: {e}"


# ----------------------------
# UI
# ----------------------------
with gr.Blocks(title="Dasai Mochi Converter") as demo:
    gr.Markdown("# u8g2 Animation & Bitmap Converter")
    
    with gr.Tabs():
        # ----------------------------
        # TAB 1: Single Frame (Original)
        # ----------------------------
        with gr.Tab("Single Frame"):
            with gr.Row():
                image_input = gr.Image(type="pil", label="Upload frame (PNG/JPG)")
                frame_index = gr.Number(value=0, precision=0, label="Frame number")

            with gr.Row():
                threshold = gr.Slider(0, 255, value=128, step=1, label="B/W threshold")
                invert_input = gr.Checkbox(value=False, label="Invert input image before threshold")
                white_is_on = gr.Checkbox(value=True, label="Packing: WHITE pixels become ON bits")
                preview_on_is_white = gr.Checkbox(value=True, label="Preview: ON bits shown as WHITE")

            snippet_len = gr.Slider(64, 1024, value=256, step=16, label="Hex snippet length (bytes)")

            convert_btn = gr.Button("Convert + Debug")

            with gr.Row():
                bw_preview = gr.Image(label="Binarized image (what gets packed)")
                decoded_preview = gr.Image(label="Decoded from bytes (u8g2 drawXBMP preview)")

            code_output = gr.Textbox(lines=18, label="Arduino output (copy/paste)")
            hex_output = gr.Textbox(lines=10, label="First bytes (hex snippet)")
            stats_output = gr.Textbox(lines=10, label="Bit statistics (per 8-row band)")

            convert_btn.click(
                convert_with_debug,
                inputs=[image_input, frame_index, threshold, invert_input, white_is_on, preview_on_is_white, snippet_len],
                outputs=[bw_preview, decoded_preview, code_output, hex_output, stats_output],
            )

            gr.Markdown("---\n## Compare against an existing C array")
            pasted = gr.Textbox(lines=12, label="Paste C array here")
            render_btn = gr.Button("Render pasted array")
            pasted_preview = gr.Image(label="Preview of pasted array (decoded)")
            pasted_status = gr.Textbox(lines=1, label="Status")

            render_btn.click(render_pasted_array, inputs=[pasted, preview_on_is_white], outputs=[pasted_preview, pasted_status])

        # ----------------------------
        # TAB 2: Video Import (New)
        # ----------------------------
        with gr.Tab("Video to Animation"):
            gr.Markdown("Upload a video to generate a zip of 128x64 PNGs and a text file containing all C arrays.")
            
            with gr.Row():
                video_input = gr.Video(label="Upload Video", sources=["upload"])
                with gr.Column():
                    v_threshold = gr.Slider(0, 255, value=128, step=1, label="B/W Threshold")
                    v_invert = gr.Checkbox(value=False, label="Invert Colors")
                    v_white_is_on = gr.Checkbox(value=True, label="Packing: WHITE = ON")
                    v_convert_btn = gr.Button("Process Video", variant="primary")
            
            with gr.Row():
                file_code_output = gr.File(label="Download C Code (.c)")
                file_zip_output = gr.File(label="Download Frames (.zip)")
            
            v_status_output = gr.Textbox(label="Status")
            
            v_convert_btn.click(
                process_video_file,
                inputs=[video_input, v_threshold, v_invert, v_white_is_on],
                outputs=[file_code_output, file_zip_output, v_status_output]
            )

demo.launch()