"""Add empty native GU event records to the integrated private Long Sword motions."""

import argparse
from pathlib import Path
from struct import pack_into, unpack_from
import sys


def add_empty_events(bank):
    if bank[:8] != b"LMT\0\x43\0\0\x01":
        raise ValueError("Expected the 256-slot GU Long Sword motion bank")

    result = bytearray(bank)
    added = 0
    # Imported Wilds slots plus the private World move bank. A descriptor
    # with native events already attached keeps them.
    for slot in (*range(84, 93), 98, 99, *range(208, 221), *range(224, 256)):
        descriptor, = unpack_from("<I", bank, 8 + 4 * slot)
        if not descriptor:
            continue
        frames, = unpack_from("<I", bank, descriptor + 8)
        events, = unpack_from("<I", bank, descriptor + 52)
        if events:
            continue

        result.extend(bytes(-len(result) % 16))
        events = len(result)
        result.extend(bytes(4 * 72 + 8))
        key = events + 4 * 72
        pack_into("<2I", result, key, 0, frames)
        for channel in range(4):
            pack_into("<2I", result, events + channel * 72 + 64, 1, key)
        pack_into("<I", result, descriptor + 52, events)
        added += 1
    return bytes(result), added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("wilds_tools", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.wilds_tools.resolve()))
    from portkit import ANIM_ENTRY, arc_replace, read_arc

    _, entries = read_arc(args.archive)
    bank = next(entry.data() for entry in entries if entry.name == ANIM_ENTRY)
    repaired, count = add_empty_events(bank)
    arc_replace(args.archive, args.output, {ANIM_ENTRY: repaired})
    print(f"Initialized GU event records for {count} private motions")


if __name__ == "__main__":
    main()
