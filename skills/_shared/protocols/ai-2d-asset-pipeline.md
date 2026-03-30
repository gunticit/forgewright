# Automated 2D AI Art Protocol (Nano Banana Pattern)

This protocol governs how the AI Orchestrator, specifically the `game-asset-vfx` skill, should generate prompts and metadata for automated 2D asset creation (e.g., using Nano Banana, Midjourney, DALL-E) to guarantee deterministic engine integration.

## 1. The Core Problem
When AI generates game assets iteratively:
- Sprite bounding boxes wobble (unstable origin point).
- Animations fail due to missing or extra frames.
- Backgrounds blend into the character, breaking auto-slicing code.

## 2. Structured Prompt Generation Rules
Whenever you generate a prompt for an AI Image Generator for a 2D Game Asset, you MUST adhere to the following strict constraints:

### Rule 1: Solid Contrast Backgrounds
**NEVER** use "transparent background", "white background", or "black background".
**ALWAYS** specify a strict #333333 (dark charcoal) or #FF00FF (magenta) background. This ensures Python scripts can reliably use chroma-keying to extract the sprite without culling shadows or highlights.
*Example Prompt Injection:* `"Background: Solid #333333"`

### Rule 2: Grid Layout Definition
**NEVER** let the AI guess the layout.
**ALWAYS** define a strict mathematical grid in the prompt.
*Example Prompt Injection:* `"Layout: Sprite sheet, exactly 4 rows by 6 columns"`

### Rule 3: Fixed Seed Consistency
**ALWAYS** instruct the user (or the prompt payload) to use the SAME base **Seed** for all characters and tilesets within the same faction or biome to preserve Art Style consistency.

### Rule 4: "Programmatic Animation" Focus
AI struggles with frame-by-frame animation (like walk cycles). For 2D games generated via this pipeline, prioritize **Static Props** or **Single-frame characters**, and instruct the Engine Engineer (Godot/Unity) to use programmatic tweening (stretch, squash, rotation) for animation logic.
If you MUST generate animations, specify exactly what each row does implicitly in standard industry jargon (e.g., "Top row: walk down, Second row: walk left, Third row: walk right, Bottom row: walk up").

## 3. Metadata Generation Requirement
Alongside the visual prompt, the `game-asset-vfx` role MUST output an `assets-manifest.json` snippet. This snippet will be read by the Python Image Slicing script.

**Mandatory JSON Schema:**
```json
{
  "asset_id": "player_hero",
  "grid_columns": 6,
  "grid_rows": 4,
  "background_color": "#333333",
  "is_spritesheet": true
}
```

## 4. Pipeline Execution Flow
1. **Prompt Creation:** `game-asset-vfx` creates the raw Nano Banana prompt + the `assets-manifest.json`.
2. **Generation:** The user (or MCP) runs the prompt via Nano Banana and saves the image to `assets/raw/player_hero.png`.
3. **Processing:** The system runs `scripts/asset-slice-processor.py`, targeting the JSON. The script chroma-keys `#333333` to Alpha=0, slices the image into `grid_columns` x `grid_rows` equal rectangles, and saves them to `assets/processed/`.
4. **Engine Parsing:** The Engine Engineer (Godot/Unity) points their code to `assets/processed/`, confident that all frames are exact, mathematically precise rectangles.
