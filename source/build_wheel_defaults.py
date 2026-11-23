"""Write the standard Quick Wheel v0.51 SD-card records for a fresh profile."""

from pathlib import Path
import struct
import zlib


def write_default(folder, name, *words):
    payload = struct.pack(f"<{len(words)}I", *words)
    # The wheel journal stores the running CRC before its final complement.
    record = payload + struct.pack("<I", zlib.crc32(payload) ^ 0xFFFFFFFF)
    (folder / f"{name}_b.bin").write_bytes(record)


def main():
    folder = Path(__file__).resolve().parents[1] / "wheel-defaults"
    folder.mkdir(exist_ok=True)
    # Mega Potion, Whetstone, Antidote, Paintball, Well-done Steak,
    # Flash Bomb, Shock Trap and Tranq Bomb, clockwise from the top.
    # The wheel serializes N, E, S, W, NE, SE, SW, NW.
    slots = (10, 13, 50, 84, 56, 70, 71, 73)
    write_default(folder, "gu_wheel_loadouts", 0x314C5747, 1, 1, 0, *slots, *([0] * 24), *slots)
    # Keep the lower edge above the expanded native item bar on the 720p canvas.
    write_default(folder, "gu_wheel_position", 0x32505747, 1, 1113, 468)
    write_default(folder, "gu_wheel_mode", 0x314D5747, 1, 1)
    # Xbox icons, full opacity, LB opener. Leave the preset shortcut disabled.
    write_default(folder, "gu_wheel_settings", 0x31535747, 1, 0, 3 << 1, (7 << 4) | 9)


if __name__ == "__main__":
    main()
