"""Relabel MHGU's shared button font and HUD sheets without changing input."""

import argparse
import io
from pathlib import Path
from struct import pack_into, unpack_from
import sys

from PIL import Image, ImageDraw, ImageFont


SHEETS = {
    "button_festa_00_id": (24, (
        (0, 0, "X"), (24, 0, "Y"), (48, 0, "A"), (72, 0, "B"),
        (96, 0, "LB"), (0, 24, "RB"), (120, 24, "LT"), (144, 24, "RT"),
        (0, 72, "Menu"), (24, 72, "View"), (168, 24, "LS"), (192, 24, "RS"),
    )),
    "hd_custom_pnl2_bm_nomip": (32, (
        (0, 244, "LB"), (32, 244, "X"), (64, 244, "Y"), (96, 244, "A"),
        (128, 244, "B"), (160, 244, "RB"), (192, 244, "LT"), (224, 244, "RT"),
        # Keep GU's native right-stick push pictogram for target lock.
        (384, 244, "View"), (416, 244, "Menu"), (352, 180, "LS"),
    )),
    "hd_hud00_bm_nomip": (32, (
        (0, 408, "LB"), (32, 408, "X"), (64, 408, "Y"),
        (96, 408, "A"), (128, 408, "B"), (160, 408, "RB"),
    )),
    "hd_window_bm_mq_nomip": (32, (
        (48, 80, "LB"), (80, 80, "RB"), (0, 192, "LT"), (32, 192, "RT"),
    )),
}
FACE_COLOR = {"A": "#6dc447", "B": "#e25359", "X": "#4aa3ee", "Y": "#f3d165"}


def update_hunter_art_panel(data, xbox=False):
    if data[:8] != b"GUI\0\x15\x27\x02\0":
        raise ValueError("Unexpected MHGU 1.4.0 Hunter Art panel layout")
    result = bytearray(data)
    # The stock rectangles start four pixels into the Xbox atlas cells.
    # Align their sampling to the full cell so small badges stay centered.
    rectangles = ((0x38120, 132, 32 if xbox else 36),)
    if xbox:
        rectangles += ((0x38080, 68, 64), (0x38100, 196, 192), (0x382E0, 100, 96))
    for offset, original, left in rectangles:
        if unpack_from("<4f", data, offset) != (original, 244, original + 32, 276):
            raise ValueError(f"Unexpected Hunter Art rectangle {offset:#x}")
        pack_into("<4f", result, offset, left, 244, left + 32, 276)
    return bytes(result)


def block_offset(width, height, x, y):
    # Tegra block-linear layout for the game's BC3 mip 0.
    gob_height = min(16, 1 << ((height + 31) // 32 - 1).bit_length())
    x_bytes = x * 16
    gob_x, in_x = divmod(x_bytes, 64)
    gob_y, in_y = divmod(y, 8)
    block_y, within_block = divmod(gob_y, gob_height)
    return (
        (block_y * ((width + 63) // 64) + gob_x) * gob_height * 512
        + within_block * 512 + (in_x // 32) * 256 + (in_y // 2) * 64
        + ((in_x // 16) & 1) * 32 + (in_y & 1) * 16 + (in_x & 15)
    )


def button(size, label, font_file, hud=False):
    scale = 4
    side = size * scale
    image = Image.new("RGBA", (side, side))
    draw = ImageDraw.Draw(image)
    if hud and (len(label) == 1 or label in ("LT", "RT", "LB", "RB")):
        margin = round(side * 0.13)
        inset = round(side * 0.04)
        edge = (margin, margin, side - margin - 1, side - margin - 1)
        inner = tuple(value + inset if index < 2 else value - inset
                      for index, value in enumerate(edge))
        if len(label) == 1:
            draw.ellipse(edge, fill="#17212a")
            draw.ellipse(inner, fill="#faf8ef", outline="#7c868e", width=scale)
        else:
            draw.rounded_rectangle(edge, radius=4 * scale, fill="#17212a")
            draw.rounded_rectangle(inner, radius=3 * scale, fill="#faf8ef",
                                   outline="#7c868e", width=scale)
        fill, font_size = "#18232d", size * (0.46 if len(label) == 1 else 0.38)
    elif len(label) == 1:
        pad = 2 * scale
        draw.ellipse((pad, pad, side-pad-1, side-pad-1), fill="#161b20",
                     outline="#e9edf0", width=scale)
        fill, font_size = FACE_COLOR[label], size * 0.61
    else:
        pad = scale
        top = round(side * 0.19)
        draw.rounded_rectangle((pad, top, side-pad-1, side-top-1), radius=4*scale,
                               fill="#20262c", outline="#e9edf0", width=scale)
        fill, font_size = "#f3f5f7", size * (0.48 if len(label) <= 2 else 0.3)
    font = ImageFont.truetype(str(font_file), round(font_size * scale))
    box = draw.textbbox((0, 0), label, font=font)
    draw.text(((side - box[2] - box[0])/2, (side - box[3] - box[1])/2),
              label, font=font, fill=fill)
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    compressed = io.BytesIO()
    image.save(compressed, "DDS", pixel_format="DXT5")
    return compressed.getvalue()[128:]


def update_texture(data, key, font_file):
    if data[:5] != b"TEX\0\xa0" or data[13] != 0x17:
        raise ValueError(f"Unsupported texture {key}")
    dims, = unpack_from("<I", data, 8)
    width, height = (dims >> 6) & 0x1FFF, dims >> 19
    pixels_at = 20 + 4 * (dims & 63) + unpack_from("<I", data, 20)[0]
    standard = 256 if key.startswith("button_festa") else 512
    factor = width // standard
    if width != height or width != standard * factor or factor not in (1, 2, 4):
        raise ValueError(f"Unexpected dimensions for {key}: {width} x {height}")
    size, placements = SHEETS[key]
    size *= factor
    result = bytearray(data)
    for x, y, label in placements:
        blocks = button(size, label, font_file, hud=key == "hd_custom_pnl2_bm_nomip")
        for by in range(size // 4):
            for bx in range(size // 4):
                start = (by * (size // 4) + bx) * 16
                dest = pixels_at + block_offset(width, height, x*factor//4 + bx, y*factor//4 + by)
                result[dest:dest+16] = blocks[start:start+16]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romfs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("wilds_tools", type=Path)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/segoeuib.ttf"))
    parser.add_argument("--switch-output", type=Path,
                        help="Write the remapped Hunter Art HUD with stock Switch glyphs")
    args = parser.parse_args()
    sys.path.insert(0, str(args.wilds_tools.resolve()))
    from portkit import arc_replace, read_arc

    for path in sorted(args.romfs.rglob("*")):
        out = args.output / path.relative_to(args.romfs)
        if path.suffix.lower() == ".arc":
            _, entries = read_arc(path)
            replacements = {}
            for entry in entries:
                key = entry.name.rsplit("\\", 1)[-1].lower()
                if key in SHEETS:
                    replacements[entry.name] = update_texture(entry.data(), key, args.font)
                elif key == "custom_panel" and path.name.lower().startswith("quest_"):
                    panel = update_hunter_art_panel(entry.data(), xbox=True)
                    replacements[entry.name] = panel
                    if args.switch_output:
                        arc_replace(path, args.switch_output / path.relative_to(args.romfs),
                                    {entry.name: update_hunter_art_panel(entry.data())})
            if replacements:
                arc_replace(path, out, replacements)
                print(path.relative_to(args.romfs), len(replacements))
        elif path.suffix.lower() == ".tex" and path.stem.lower() in SHEETS:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(update_texture(path.read_bytes(), path.stem.lower(), args.font))


if __name__ == "__main__":
    main()
