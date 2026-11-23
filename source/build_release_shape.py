"""Append a native central contact to the four posed Spirit Release spheres."""

import argparse
from pathlib import Path
from struct import pack_into, unpack_from
import sys


def add_release_shape(data):
    if data[:4] != b"HTS\x00":
        raise ValueError("Expected GU hitsize data")
    count, = unpack_from("<I", data, 8)
    if count not in (17, 18):
        raise ValueError("Expected the Wilds blade and attached follow-up shapes")

    groups = []
    for i in range(count):
        size, offset = unpack_from("<2I", data, 16 + i * 8)
        groups.append(data[offset:offset + size * 48])

    blade, root = groups[15:17]
    if len(blade) != 4 * 48 or len(root) != 48:
        raise ValueError("Unexpected Wilds collider layout")
    body = bytearray(root)
    # DYSMANTLE uses an 80-unit disk at torso height with a 49-unit blade
    # sampling span. GU uses a root sphere and a 90-unit blade sampling span.
    pack_into("<f", body, 12, 80 * 90 / 49)
    pack_into("<f", body, 20, 28 * 90 / 49)
    release = blade + body
    if count == 18:
        if groups[17] != release:
            raise ValueError("Release shape index is already occupied")
        return data
    groups.append(release)

    rebuilt = bytearray(data[:16] + bytes(8 * len(groups)))
    pack_into("<I", rebuilt, 8, len(groups))
    for i, group in enumerate(groups):
        pack_into("<2I", rebuilt, 16 + i * 8, len(group) // 48, len(rebuilt))
        rebuilt.extend(group)
    return bytes(rebuilt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("wilds_tools", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.wilds_tools.resolve()))
    from portkit import arc_replace, read_arc

    _, entries = read_arc(args.archive)
    entry = next(item for item in entries if item.name.endswith("pl_we07_hitsize"))
    updated = add_release_shape(entry.data())
    arc_replace(args.archive, args.output, {entry.name: updated})
    print("Spirit Release group 17 has four blade spheres and one root sphere")


if __name__ == "__main__":
    main()
