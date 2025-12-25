# DASAI Mochi Expression Converter (u8g2 Bitmap Converter)

POV: I wanted my own **DASAI mochi expression converter** to make things easier.
With this tool you can **convert new expressions**, **compare with working ones**, and generally make the workflow smoother when drawing / iterating on expressions.

This app converts a **128×64** black/white image into an **Arduino `PROGMEM` bitmap array** that matches **`u8g2.drawXBMP`** byte packing.

---

## Example image (128×64 canvas)

Use this repo’s example as a reference for sizing and style:

![sad example](./sad.png)

> **Important:** The expression canvas is **128×64**. You *can* upload other sizes (it will resize), but you’ll get the best results if you draw on a true 128×64 canvas to avoid distortion.

---

## What it does

When you upload an image, the UI produces:

1. **Binarized (packed)** preview (thresholded to pure B/W)
2. **OLED preview** that mirrors how `u8g2.drawXBMP` will render it
3. **Arduino bitmap code** as a `const unsigned char ... PROGMEM` array

White pixels are treated as **ON**, black pixels as **OFF**.

---

## Requirements

- Python 3.x
- Dependencies:
  - `gradio`
  - `numpy`
  - `Pillow`

Install them with:

```bash
pip install gradio numpy pillow opencv-python
```
