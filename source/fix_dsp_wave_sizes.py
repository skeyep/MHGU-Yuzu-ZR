"""Correct undersized mono DSP-ADPCM wave headers for Yuzu 1734."""

import argparse
from pathlib import Path
from struct import pack_into, unpack_from
import sys


WAVE_ENTRY = 0x79C47B59
DSP_MONO = bytes.fromhex("02 00 00 00 01 00 00 01")
DSP_HEADER_SIZE = 120


def position_to_bytes(sample):
    frames, tail = divmod(sample, 14)
    return frames * 8 + (1 + (tail + 1) // 2 if tail else 0)


def fix_wave(wave, name):
    if not wave.startswith(DSP_MONO):
        return None
    declared, = unpack_from("<I", wave, 8)
    samples, _, _, start, end, _ = unpack_from("<6I", wave, 96)
    # The archive stores the last sample index. The renderer checks an
    # end-exclusive position and may need the rest of the last ADPCM byte.
    required = max(position_to_bytes(start), position_to_bytes(end + 1))
    if required <= declared:
        return None
    if start > end or end >= samples or DSP_HEADER_SIZE + required > len(wave):
        raise ValueError(f"{name}: sample positions exceed the encoded wave")
    patched = bytearray(wave)
    pack_into("<I", patched, 8, required)
    return bytes(patched)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_arc_root", type=Path)
    parser.add_argument("output_arc_root", type=Path)
    parser.add_argument("wilds_tools", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.wilds_tools.resolve()))
    from portkit import arc_replace, read_arc

    archives = [args.source_arc_root / "forge/world_audio.arc"]
    archives.extend(sorted((args.source_arc_root / "weapon/w07/snd").glob("*.arc")))
    affected_archives = affected_waves = 0
    for source in archives:
        _, entries = read_arc(source)
        replacements = {}
        for entry in entries:
            if entry.kind == WAVE_ENTRY:
                wave = fix_wave(entry.data(), entry.name)
                if wave is not None:
                    replacements[entry.name] = wave
        if replacements:
            relative_path = source.relative_to(args.source_arc_root)
            arc_replace(source, args.output_arc_root / relative_path, replacements)
            affected_archives += 1
            affected_waves += len(replacements)
            print(f"{relative_path.as_posix()} {len(replacements)}")
    print(f"{affected_waves} wave headers in {affected_archives} archives")


if __name__ == "__main__":
    main()
