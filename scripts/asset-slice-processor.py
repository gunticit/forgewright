#!/usr/bin/env python3
"""
Automated 2D AI Art Processor for Forgewright
Removes solid backgrounds (e.g., #333333) and slices AI-generated sprite sheets based on assets-manifest.json.
Requirements: pip install Pillow
"""

import sys
import json
import os
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow library required. Run 'pip install Pillow' before executing this script.", file=sys.stderr)
    sys.exit(1)

def hex_to_rgba(hex_code, alpha=255):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 6:
        # Standard RGB, convert to RGBA
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return (r, g, b, alpha)
    return None

def process_asset(manifest_path):
    print(f"Processing manifest: {manifest_path}")
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest {manifest_path} not found.", file=sys.stderr)
        return False

    with open(manifest_path, 'r') as f:
        meta = json.load(f)

    asset_id = meta.get("asset_id")
    cols = meta.get("grid_columns", 1)
    rows = meta.get("grid_rows", 1)
    bg_color_hex = meta.get("background_color", "#333333")
    
    # Locate raw image
    root_dir = Path(manifest_path).parent.parent
    raw_path = root_dir / "raw" / f"{asset_id}.png"
    out_dir = root_dir / "processed" / asset_id
    
    if not raw_path.exists():
        print(f"Error: Raw image {raw_path} not found.", file=sys.stderr)
        return False

    os.makedirs(out_dir, exist_ok=True)
    
    bg_rgba = hex_to_rgba(bg_color_hex, 255)

    img = Image.open(raw_path).convert("RGBA")
    datas = img.getdata()

    # Pass 1: Remove Background (Chroma-key)
    # We use a slight tolerance since AI generation sometimes artifacts near edges
    new_data = []
    tolerance = 15
    for item in datas:
        if abs(item[0] - bg_rgba[0]) < tolerance and \
           abs(item[1] - bg_rgba[1]) < tolerance and \
           abs(item[2] - bg_rgba[2]) < tolerance:
            new_data.append((255, 255, 255, 0)) # Transparent
        else:
            new_data.append(item)

    img.putdata(new_data)

    img_w, img_h = img.size
    frame_w = img_w // cols
    frame_h = img_h // rows
    
    print(f"Slicing {asset_id} into {cols}x{rows} grid (Frame Size: {frame_w}x{frame_h})")

    # Pass 2: Slice and Export
    frame_idx = 0
    for row in range(rows):
        for col in range(cols):
            left = col * frame_w
            top = row * frame_h
            right = left + frame_w
            bottom = top + frame_h
            frame = img.crop((left, top, right, bottom))
            frame_path = out_dir / f"{asset_id}_{frame_idx:03d}.png"
            frame.save(frame_path, "PNG")
            frame_idx += 1

    print(f"✅ Successfully processed {asset_id}. Output saved to {out_dir}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python asset-slice-processor.py <path_to_assets-manifest.json>")
        sys.exit(1)
    
    manifest_arg = sys.argv[1]
    process_asset(manifest_arg)
