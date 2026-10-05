#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_turnaround_strip.py -- compose a 4-view turnaround strip that matches the
ComfyUI template `3d_pixal3d_multi_views` hardcoded crop regions.

The template crops ONE sheet at fixed pixel boxes (left->right: front, back,
left, right), so the sheet MUST be exactly 6336x2688 with each view inside its
box. Each input view is contain-fitted (scaled by box width, centered on white).

Usage:
  python make_turnaround_strip.py --front F.png --back B.png --left L.png --right R.png --out sheet.png

Generate the views with the sibling comfyui-headless-image21 skill: keep the
original art as `--front`, then for back/left/right run its `edit` command with
the original as reference (identity anchor). The back view needs an explicit
"face NOT visible / head turned away" instruction or the model draws a front.
"""
import argparse
from PIL import Image

CANVAS = (6336, 2688)
# (x, width) per panel, height = full 2688. Panel ORDER verified from the template graph
# (SaveImageAdvanced titles trace back through ImageCropToMask to ImageCropV2 boxes):
# x=0 front, x=1652 LEFT, x=3182 BACK, x=4728 right. NOT front/back/left/right.
BOXES = [(0, 1669), (1652, 1492), (3182, 1476), (4728, 1608)]  # front, left, back, right


def load_white(path):
    im = Image.open(path)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        return bg
    return im.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", required=True)
    ap.add_argument("--back", required=True)
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    canvas = Image.new("RGB", CANVAS, (255, 255, 255))
    for (x, w), path in zip(BOXES, [a.front, a.left, a.back, a.right]):
        im = load_white(path)
        scale = min(w / im.width, CANVAS[1] / im.height)
        nw, nh = round(im.width * scale), round(im.height * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        canvas.paste(im, (x + (w - nw) // 2, (CANVAS[1] - nh) // 2))
    canvas.save(a.out)
    print("saved", a.out, canvas.size)


if __name__ == "__main__":
    main()
