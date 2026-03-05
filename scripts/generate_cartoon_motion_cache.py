from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


REQUIRED_EMOTIONS: tuple[str, ...] = ("neutral", "energetic", "tense", "warm", "inspiring")
REQUIRED_VISEMES: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "X")

MOUTH_OPEN: dict[str, float] = {
    "A": 0.24,
    "B": 0.12,
    "C": 0.18,
    "D": 0.10,
    "E": 0.20,
    "F": 0.09,
    "G": 0.18,
    "H": 0.13,
    "X": 0.04,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate demo multi-frame cartoon cache variants from manifest.")
    parser.add_argument("--pack-root", type=str, default="main_app/assets/cartoon_packs/default")
    parser.add_argument("--frames", type=int, default=12, help="Frame count per variant (recommended >= 8).")
    parser.add_argument("--size", type=int, default=512, help="Sprite canvas size in pixels.")
    parser.add_argument("--characters", type=str, default="", help="Comma-separated character ids (default: all manifest characters).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing frame files.")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    manifest_path = pack_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object.")

    characters_raw = manifest.get("characters", [])
    if not isinstance(characters_raw, list):
        raise ValueError("Manifest characters must be an array.")
    selected = {
        clean(item).lower()
        for item in str(args.characters or "").split(",")
        if clean(item)
    }
    frames = max(1, int(args.frames))
    size = max(128, int(args.size))
    generated = 0

    for item in characters_raw:
        if not isinstance(item, dict):
            continue
        char_id = clean(item.get("id")).lower()
        if not char_id:
            continue
        if selected and char_id not in selected:
            continue
        rgb = hex_to_rgb(clean(item.get("color_hex"))) or (95, 140, 210)
        cache_root_hint = clean(item.get("cache_root")) or f"characters/{char_id}/cache"
        cache_root = resolve_path(pack_root=pack_root, hint=cache_root_hint)

        for state in ("idle", "blink"):
            for emotion in REQUIRED_EMOTIONS:
                generated += write_variant(
                    cache_root=cache_root,
                    state=state,
                    variant=emotion,
                    base_rgb=rgb,
                    frames=frames,
                    size=size,
                    overwrite=bool(args.overwrite),
                )
        for emotion in REQUIRED_EMOTIONS:
            for viseme in REQUIRED_VISEMES:
                generated += write_variant(
                    cache_root=cache_root,
                    state="talk",
                    variant=f"{emotion}_{viseme}",
                    base_rgb=rgb,
                    frames=frames,
                    size=size,
                    overwrite=bool(args.overwrite),
                )

    print(f"Generated/updated {generated} frame files under {pack_root}.")


def write_variant(
    *,
    cache_root: Path,
    state: str,
    variant: str,
    base_rgb: tuple[int, int, int],
    frames: int,
    size: int,
    overwrite: bool,
) -> int:
    folder = cache_root / state / variant
    folder.mkdir(parents=True, exist_ok=True)
    emotion, viseme = parse_variant(state=state, variant=variant)
    created = 0
    for index in range(frames):
        file_name = f"f{index + 1:04d}.png"
        path = folder / file_name
        if path.exists() and not overwrite:
            continue
        image = render_sprite_frame(
            size=size,
            base_rgb=base_rgb,
            state=state,
            emotion=emotion,
            viseme=viseme,
            frame_idx=index,
            frame_count=frames,
        )
        image.save(path, optimize=True)
        created += 1
    return created


def render_sprite_frame(
    *,
    size: int,
    base_rgb: tuple[int, int, int],
    state: str,
    emotion: str,
    viseme: str,
    frame_idx: int,
    frame_count: int,
) -> Image.Image:
    upscale = 2
    canvas = size * upscale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    t = 0.0 if frame_count <= 1 else frame_idx / float(frame_count - 1)
    wave = math.sin(t * math.pi * 2.0)
    wave2 = math.sin((t * math.pi * 2.0) + 1.1)

    mood = clean(emotion).lower()
    viseme_key = clean(viseme).upper() or "X"
    talking = clean(state).lower() == "talk"
    blinking = clean(state).lower() == "blink" or (not talking and (frame_idx % max(3, frame_count // 3) == 0))

    skin = tint((239, 206, 165), emotion=mood, amount=0.08)
    skin_shadow = mix_rgb(skin, (145, 112, 95), 0.36)
    shirt = tint(base_rgb, emotion=mood, amount=0.16)
    shirt_shadow = mix_rgb(shirt, (28, 34, 44), 0.38)
    shirt_highlight = mix_rgb(shirt, (245, 250, 255), 0.20)
    pants = mix_rgb(shirt, (24, 30, 40), 0.64)
    hair = mix_rgb((58, 46, 38), base_rgb, 0.18)
    outline = (22, 27, 34, 255)

    cx = int((canvas * 0.50) + (wave2 * canvas * 0.005))
    foot_y = int(canvas * 0.93)
    bob = int(round((wave * canvas * 0.007) + (wave2 * canvas * 0.0035)))

    shadow_w = int(canvas * 0.34)
    shadow_h = int(canvas * 0.052)
    draw.ellipse(
        (cx - shadow_w // 2, foot_y - shadow_h // 2, cx + shadow_w // 2, foot_y + shadow_h // 2),
        fill=(8, 10, 14, 62),
    )

    body_h = int(canvas * 0.62)
    body_w = int(canvas * 0.36)
    torso_top = foot_y - int(body_h * 0.66) + bob
    torso_bottom = foot_y - int(body_h * 0.12) + bob
    torso_left = cx - body_w // 2
    torso_right = cx + body_w // 2
    torso_radius = int(canvas * 0.07)

    leg_w = int(body_w * 0.28)
    leg_h = int(body_h * 0.22)
    leg_y = torso_bottom
    draw.rounded_rectangle(
        (cx - leg_w - int(canvas * 0.018), leg_y, cx - int(canvas * 0.01), leg_y + leg_h),
        radius=int(canvas * 0.02),
        fill=(*pants, 255),
        outline=outline,
        width=max(2, canvas // 300),
    )
    draw.rounded_rectangle(
        (cx + int(canvas * 0.01), leg_y, cx + leg_w + int(canvas * 0.018), leg_y + leg_h),
        radius=int(canvas * 0.02),
        fill=(*pants, 255),
        outline=outline,
        width=max(2, canvas // 300),
    )
    shoe_h = int(canvas * 0.022)
    draw.rounded_rectangle(
        (
            cx - leg_w - int(canvas * 0.028),
            leg_y + leg_h - shoe_h // 2,
            cx - int(canvas * 0.004),
            leg_y + leg_h + shoe_h,
        ),
        radius=int(canvas * 0.012),
        fill=(26, 30, 38, 255),
    )
    draw.rounded_rectangle(
        (
            cx + int(canvas * 0.004),
            leg_y + leg_h - shoe_h // 2,
            cx + leg_w + int(canvas * 0.028),
            leg_y + leg_h + shoe_h,
        ),
        radius=int(canvas * 0.012),
        fill=(26, 30, 38, 255),
    )

    draw.rounded_rectangle(
        (torso_left, torso_top, torso_right, torso_bottom),
        radius=torso_radius,
        fill=(*shirt_shadow, 255),
        outline=outline,
        width=max(2, canvas // 280),
    )
    draw.rounded_rectangle(
        (torso_left + int(canvas * 0.012), torso_top + int(canvas * 0.012), torso_right - int(canvas * 0.012), torso_bottom),
        radius=max(2, torso_radius - int(canvas * 0.01)),
        fill=(*shirt, 255),
    )
    draw.polygon(
        [
            (torso_left + int(canvas * 0.045), torso_top + int(canvas * 0.06)),
            (torso_right - int(canvas * 0.045), torso_top + int(canvas * 0.03)),
            (torso_right - int(canvas * 0.07), torso_top + int(canvas * 0.18)),
            (torso_left + int(canvas * 0.07), torso_top + int(canvas * 0.22)),
        ],
        fill=(*shirt_highlight, 120),
    )
    draw.line(
        (cx, torso_top + int(canvas * 0.04), cx, torso_bottom - int(canvas * 0.03)),
        fill=(*mix_rgb(shirt, (18, 22, 28), 0.42), 178),
        width=max(2, canvas // 320),
    )

    shoulder_y = torso_top + int((torso_bottom - torso_top) * 0.22)
    arm_len = int(canvas * 0.17)
    gesture = 1.0
    if mood in {"energetic", "inspiring"}:
        gesture += 0.18
    if mood == "tense":
        gesture -= 0.12
    if talking:
        gesture += 0.12
    arm_sway = wave * canvas * 0.016
    left_hand_x = int(torso_left - (arm_len * 0.52) - arm_sway)
    left_hand_y = int(shoulder_y + (arm_len * (0.78 - (0.12 * gesture))) + (wave2 * canvas * 0.008))
    right_hand_x = int(torso_right + (arm_len * 0.52) + arm_sway)
    right_hand_y = int(shoulder_y + (arm_len * (0.62 - (0.10 * gesture))) - (wave2 * canvas * 0.008))
    if talking and viseme_key in {"A", "E", "G", "H"}:
        right_hand_y -= int(canvas * 0.032)
    draw_limb(
        draw=draw,
        start=(torso_left + int(canvas * 0.012), shoulder_y),
        end=(left_hand_x, left_hand_y),
        color=shirt,
        outline=outline,
        width=max(9, canvas // 52),
    )
    draw_limb(
        draw=draw,
        start=(torso_right - int(canvas * 0.012), shoulder_y),
        end=(right_hand_x, right_hand_y),
        color=shirt,
        outline=outline,
        width=max(9, canvas // 52),
    )
    hand_r = int(canvas * 0.028)
    draw.ellipse(
        (left_hand_x - hand_r, left_hand_y - hand_r, left_hand_x + hand_r, left_hand_y + hand_r),
        fill=(*skin, 255),
        outline=outline,
        width=max(2, canvas // 300),
    )
    draw.ellipse(
        (right_hand_x - hand_r, right_hand_y - hand_r, right_hand_x + hand_r, right_hand_y + hand_r),
        fill=(*skin, 255),
        outline=outline,
        width=max(2, canvas // 300),
    )

    neck_w = int(body_w * 0.22)
    neck_h = int(canvas * 0.044)
    draw.rounded_rectangle(
        (cx - neck_w // 2, torso_top - int(canvas * 0.012), cx + neck_w // 2, torso_top + neck_h),
        radius=int(canvas * 0.012),
        fill=(*skin_shadow, 255),
    )

    head_r = int(canvas * 0.17)
    head_cy = torso_top - int(head_r * 0.84) + int(round(wave * canvas * 0.005))
    head_bbox = (cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r)

    ear_r = int(head_r * 0.17)
    draw.ellipse((cx - head_r - ear_r, head_cy - ear_r, cx - head_r + ear_r, head_cy + ear_r), fill=(*skin, 255), outline=outline, width=max(2, canvas // 320))
    draw.ellipse((cx + head_r - ear_r, head_cy - ear_r, cx + head_r + ear_r, head_cy + ear_r), fill=(*skin, 255), outline=outline, width=max(2, canvas // 320))

    draw.ellipse(head_bbox, fill=(*skin_shadow, 255), outline=outline, width=max(2, canvas // 280))
    draw.ellipse(
        (
            head_bbox[0] + int(canvas * 0.012),
            head_bbox[1] + int(canvas * 0.01),
            head_bbox[2] - int(canvas * 0.01),
            head_bbox[3] - int(canvas * 0.006),
        ),
        fill=(*skin, 255),
    )
    draw.ellipse(
        (
            cx - int(head_r * 0.7),
            head_cy - int(head_r * 0.88),
            cx + int(head_r * 0.18),
            head_cy - int(head_r * 0.2),
        ),
        fill=(255, 255, 255, 42),
    )

    hair_top = head_cy - int(head_r * 1.02)
    hair_bottom = head_cy - int(head_r * 0.12)
    draw.ellipse(
        (cx - int(head_r * 0.96), hair_top, cx + int(head_r * 0.96), hair_bottom),
        fill=(*hair, 255),
        outline=outline,
        width=max(2, canvas // 300),
    )
    fringe_shift = int(wave2 * canvas * 0.004)
    draw.polygon(
        [
            (cx - int(head_r * 0.82), head_cy - int(head_r * 0.52)),
            (cx - int(head_r * 0.35), head_cy - int(head_r * 0.06) + fringe_shift),
            (cx + int(head_r * 0.12), head_cy - int(head_r * 0.38)),
            (cx + int(head_r * 0.58), head_cy - int(head_r * 0.06) - fringe_shift),
            (cx + int(head_r * 0.84), head_cy - int(head_r * 0.45)),
            (cx + int(head_r * 0.84), head_cy - int(head_r * 0.78)),
            (cx - int(head_r * 0.84), head_cy - int(head_r * 0.78)),
        ],
        fill=(*mix_rgb(hair, (16, 20, 26), 0.18), 255),
    )

    eye_y = head_cy - int(head_r * 0.13)
    eye_dx = int(head_r * 0.44)
    eye_w = int(head_r * 0.2)
    eye_h = int(head_r * 0.14)
    pupil_r = int(head_r * 0.06)
    gaze_offset_x = 0
    if mood == "tense":
        gaze_offset_x = -int(head_r * 0.04)
    elif mood in {"energetic", "inspiring"}:
        gaze_offset_x = int(head_r * 0.03)

    if blinking:
        lid_w = max(3, canvas // 260)
        draw.line((cx - eye_dx - eye_w, eye_y, cx - eye_dx + eye_w, eye_y), fill=(20, 24, 30, 255), width=lid_w)
        draw.line((cx + eye_dx - eye_w, eye_y, cx + eye_dx + eye_w, eye_y), fill=(20, 24, 30, 255), width=lid_w)
    else:
        left_eye = (cx - eye_dx - eye_w, eye_y - eye_h, cx - eye_dx + eye_w, eye_y + eye_h)
        right_eye = (cx + eye_dx - eye_w, eye_y - eye_h, cx + eye_dx + eye_w, eye_y + eye_h)
        draw.ellipse(left_eye, fill=(248, 252, 255, 255), outline=(26, 30, 38, 220), width=max(1, canvas // 420))
        draw.ellipse(right_eye, fill=(248, 252, 255, 255), outline=(26, 30, 38, 220), width=max(1, canvas // 420))
        draw.ellipse(
            (
                cx - eye_dx - pupil_r + gaze_offset_x,
                eye_y - pupil_r,
                cx - eye_dx + pupil_r + gaze_offset_x,
                eye_y + pupil_r,
            ),
            fill=(25, 30, 36, 255),
        )
        draw.ellipse(
            (
                cx + eye_dx - pupil_r + gaze_offset_x,
                eye_y - pupil_r,
                cx + eye_dx + pupil_r + gaze_offset_x,
                eye_y + pupil_r,
            ),
            fill=(25, 30, 36, 255),
        )
        spark = max(1, pupil_r // 3)
        draw.ellipse((cx - eye_dx - spark + gaze_offset_x, eye_y - spark, cx - eye_dx + gaze_offset_x, eye_y), fill=(255, 255, 255, 210))
        draw.ellipse((cx + eye_dx - spark + gaze_offset_x, eye_y - spark, cx + eye_dx + gaze_offset_x, eye_y), fill=(255, 255, 255, 210))

    brow_y = eye_y - int(head_r * 0.32)
    brow_tilt = 0
    if mood == "tense":
        brow_tilt = -int(canvas * 0.01)
    elif mood in {"energetic", "inspiring"}:
        brow_tilt = int(canvas * 0.009)
    brow_w = max(2, canvas // 300)
    draw.line((cx - eye_dx - eye_w, brow_y, cx - eye_dx + eye_w, brow_y + brow_tilt), fill=(28, 30, 36, 255), width=brow_w)
    draw.line((cx + eye_dx - eye_w, brow_y + brow_tilt, cx + eye_dx + eye_w, brow_y), fill=(28, 30, 36, 255), width=brow_w)

    nose_y = head_cy + int(head_r * 0.16)
    draw.line((cx, nose_y - int(head_r * 0.12), cx, nose_y + int(head_r * 0.05)), fill=(128, 98, 82, 122), width=max(1, canvas // 500))

    blush_alpha = 0
    if mood in {"warm", "inspiring"}:
        blush_alpha = 52
    if blush_alpha > 0:
        blush_r = int(head_r * 0.16)
        draw.ellipse(
            (cx - eye_dx - blush_r, head_cy + int(head_r * 0.15), cx - eye_dx + blush_r, head_cy + int(head_r * 0.47)),
            fill=(242, 128, 142, blush_alpha),
        )
        draw.ellipse(
            (cx + eye_dx - blush_r, head_cy + int(head_r * 0.15), cx + eye_dx + blush_r, head_cy + int(head_r * 0.47)),
            fill=(242, 128, 142, blush_alpha),
        )

    mouth_y = head_cy + int(head_r * 0.38)
    mouth_w = int(head_r * 0.58)
    if talking:
        openness = MOUTH_OPEN.get(viseme_key, 0.1)
        talk_pulse = 0.86 + (0.30 * abs(math.sin((t * math.pi * 2.0) + 0.4)))
        mouth_h = max(int(canvas * 0.012), int(canvas * openness * talk_pulse))
        outer = (cx - mouth_w // 2, mouth_y - mouth_h // 2, cx + mouth_w // 2, mouth_y + mouth_h // 2)
        inner = (
            cx - int(mouth_w * 0.42),
            mouth_y - int(mouth_h * 0.34),
            cx + int(mouth_w * 0.42),
            mouth_y + int(mouth_h * 0.46),
        )
        draw.ellipse(outer, fill=(122, 52, 62, 255), outline=(30, 24, 28, 255), width=max(1, canvas // 420))
        draw.ellipse(inner, fill=(34, 12, 16, 255))
        if mouth_h > int(canvas * 0.02):
            draw.rounded_rectangle(
                (
                    cx - int(mouth_w * 0.33),
                    mouth_y - int(mouth_h * 0.32),
                    cx + int(mouth_w * 0.33),
                    mouth_y - int(mouth_h * 0.1),
                ),
                radius=max(1, canvas // 560),
                fill=(245, 242, 236, 220),
            )
        if mouth_h > int(canvas * 0.03):
            draw.ellipse(
                (
                    cx - int(mouth_w * 0.22),
                    mouth_y + int(mouth_h * 0.05),
                    cx + int(mouth_w * 0.22),
                    mouth_y + int(mouth_h * 0.42),
                ),
                fill=(178, 72, 92, 210),
            )
    else:
        smile_depth = {
            "neutral": 0,
            "energetic": int(canvas * 0.007),
            "tense": -int(canvas * 0.006),
            "warm": int(canvas * 0.012),
            "inspiring": int(canvas * 0.014),
        }.get(mood, 0)
        mouth_box = (
            cx - mouth_w // 2,
            mouth_y - int(canvas * 0.018),
            cx + mouth_w // 2,
            mouth_y + int(canvas * 0.026) + smile_depth,
        )
        draw.arc(mouth_box, start=12, end=168, fill=(34, 36, 42, 255), width=max(2, canvas // 280))
        if mood in {"warm", "inspiring"}:
            draw.line(
                (cx - int(mouth_w * 0.2), mouth_y + int(canvas * 0.006), cx + int(mouth_w * 0.2), mouth_y + int(canvas * 0.01)),
                fill=(252, 242, 242, 120),
                width=max(1, canvas // 500),
            )

    resampling = getattr(Image, "Resampling", None)
    if resampling is not None and hasattr(resampling, "LANCZOS"):
        resample = resampling.LANCZOS
    else:
        resample = getattr(Image, "LANCZOS", 1)
    return image.resize((size, size), resample=resample)


def draw_limb(
    *,
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    outline: tuple[int, int, int, int],
    width: int,
) -> None:
    draw.line((start[0], start[1], end[0], end[1]), fill=(*mix_rgb(color, (24, 28, 36), 0.3), 255), width=max(2, width))
    draw.line((start[0], start[1], end[0], end[1]), fill=outline, width=max(1, width // 3))


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    safe = max(0.0, min(1.0, float(ratio)))
    inv = 1.0 - safe
    return (
        clip_channel((a[0] * inv) + (b[0] * safe)),
        clip_channel((a[1] * inv) + (b[1] * safe)),
        clip_channel((a[2] * inv) + (b[2] * safe)),
    )


def parse_variant(*, state: str, variant: str) -> tuple[str, str]:
    if state == "talk":
        parts = clean(variant).split("_")
        if len(parts) >= 2:
            return parts[0].lower() or "neutral", parts[-1].upper() or "X"
        return "neutral", "X"
    return clean(variant).lower() or "neutral", "X"


def resolve_path(*, pack_root: Path, hint: str) -> Path:
    raw = Path(hint)
    if raw.is_absolute():
        return raw
    return (pack_root / raw).resolve()


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
    raw = clean(hex_color).lstrip("#")
    if len(raw) != 6:
        return None
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return None


def tint(rgb: tuple[int, int, int], *, emotion: str, amount: float) -> tuple[int, int, int]:
    mood = clean(emotion).lower()
    shift = {
        "neutral": (0.0, 0.0, 0.0),
        "energetic": (1.0, -0.2, 0.4),
        "tense": (0.6, -0.5, -0.3),
        "warm": (0.9, 0.25, -0.4),
        "inspiring": (-0.15, 0.25, 0.9),
    }.get(mood, (0.0, 0.0, 0.0))
    return (
        clip_channel(rgb[0] + (255.0 * shift[0] * amount)),
        clip_channel(rgb[1] + (255.0 * shift[1] * amount)),
        clip_channel(rgb[2] + (255.0 * shift[2] * amount)),
    )


def clip_channel(value: float) -> int:
    return int(max(0, min(255, round(value))))


if __name__ == "__main__":
    main()
