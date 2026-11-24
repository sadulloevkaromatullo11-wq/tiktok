from __future__ import annotations

from pathlib import Path


def mp4_duration_seconds(path: Path) -> float | None:
    try:
        buf = path.read_bytes()
    except OSError:
        return None
    if len(buf) < 16 or buf[4:8] != b"ftyp":
        return None

    def walk(start: int, end: int) -> float | None:
        index = start
        while index + 8 <= end:
            size = int.from_bytes(buf[index : index + 4], "big")
            kind = buf[index + 4 : index + 8]
            header = 8
            if size == 1 and index + 16 <= end:
                size = int.from_bytes(buf[index + 8 : index + 16], "big")
                header = 16
            elif size == 0:
                size = end - index
            if size < header or index + size > end:
                return None
            if kind == b"mvhd":
                return _mvhd(buf[index + header : index + size])
            if kind in {b"moov", b"trak", b"mdia"}:
                found = walk(index + header, index + size)
                if found:
                    return found
            index += size
        return None

    return walk(0, len(buf))


def _mvhd(box: bytes) -> float | None:
    if len(box) < 20:
        return None
    version = box[0]
    if version == 0:
        timescale = int.from_bytes(box[12:16], "big")
        duration = int.from_bytes(box[16:20], "big")
    elif version == 1 and len(box) >= 32:
        timescale = int.from_bytes(box[20:24], "big")
        duration = int.from_bytes(box[24:32], "big")
    else:
        return None
    if timescale <= 0:
        return None
    return duration / timescale
