# DASAI Mochi Expression Converter (u8g2 Bitmap Converter)

POV: I wanted my own **DASAI mochi expression converter** to make things easier.
With this tool you can **convert new expressions**, **compare with working ones**, and generally make the workflow smoother when drawing / iterating on expressions.

This app converts a **128×64** black/white image into an **Arduino `PROGMEM` bitmap array** that matches **`u8g2.drawXBMP`** byte packing.

Check my post to figure out more: https://marcellomorettoni.wordpress.com/2025/12/25/can-you-use-createstudio-for-arduino-projects/

---

## Repository tour

| File | What it’s for |
| --- | --- |
| `single_frame_converter.py` | Minimal single-frame converter. Upload one PNG/JPG (resized to 128×64), tweak the frame index, and copy the generated `const unsigned char ... PROGMEM` bitmap. Useful for quick “does this frame pack correctly?” checks. |
| `conv3.py` | Full-featured Gradio app with tabs for single frames **and** whole-video imports. Includes threshold and inversion controls, packing/preview options (so you can pick whether white or black is “on”), hex snippets, bit statistics, and a C-array renderer for pasted code. The “Video to Animation” tab exports every frame as PNG plus a `.c` file with all arrays. |
| `dasay-mochi-gen.py` | THIS IS THE MOST IMPORTANT ONE - Animation packager for Arduino. Upload intro, idle, and expression videos (or add your own named extras) and it emits a `face.ino` file containing bitmap arrays and animation tables. BUILT FOR XIAO RP2040 |
| `adrafruit-translator.py` | SSD1306 “emulator” that draws/animates eyes (blink, happy, sad, angry, tired, heart, gaze shifts, sleeping) and exports them as an MP4. Lets you preview motion without flashing a board. |
| `eye-generator.py` | Eye transition animator. Lets you design a start pose and an end pose (openness, lids, brow, tilt, gaze, spacing, roundness) and exports the interpolated MP4 so you can preview a custom eye movement before baking it into your Arduino assets. |
| `sad.png` | Example 128×64 expression you can load into the converters to verify alignment and contrast. |

---

## Example image (128×64 canvas)

Use this repo’s example as a reference for sizing and style:

![sad example](./sad.png)

> **Important:** The expression canvas is **128×64**. You *can* upload other sizes (it will resize), but you’ll get the best results if you draw on a true 128×64 canvas to avoid distortion.

---

## How the converters work

When you upload an image, the UI produces:

1. **Binarized (packed)** preview (thresholded to pure B/W)
2. **OLED preview** that mirrors how `u8g2.drawXBMP` will render it
3. **Arduino bitmap code** as a `const unsigned char ... PROGMEM` array

White pixels are treated as **ON**, black pixels as **OFF**.

- `conv.py` always packs **white = ON**.
- `conv3.py` lets you choose which color is ON for both packing and previewing (so you can mirror OLED behaviors that use inverted colors).

---

## Running the apps locally

> All scripts are standalone; run only the one you need. They all launch a Gradio UI in the browser (by default on `http://127.0.0.1:7860`).

Install requirements first:

```bash
pip install gradio numpy pillow opencv-python imageio
```

Then launch one of the tools:

- Single-frame converter (fastest path):  
  ```bash
  python conv.py
  ```

- Converter + debugger + video importer:  
  ```bash
  python conv3.py
  ```

- Arduino animation generator (`face.ino` builder):  
  ```bash
  python dasay-mochi-gen.py
  ```

- SSD1306 → MP4 eye animator:  
  ```bash
  python adrafruit-translator.py
  ```

- Eye transition animator (start/end pose to MP4):  
  ```bash
  python eye-generator.py
  ```

If you run into port conflicts, add `--server.port 7861` (or any free port) to the `python ...` command.

---

## Tips for best results

- Start with true **128×64** artwork to avoid rescaling artifacts.
- Use high-contrast black/white images; avoid mid-gray edges that might wobble across a threshold.
- In `conv3.py`, toggle **Invert** or **Packing: WHITE = ON** if your OLED uses opposite polarity.
- For animations, keep frame counts modest—Arduino flash fills up quickly. Use the hex snippet + bit stats panels to spot heavy frames.

---
