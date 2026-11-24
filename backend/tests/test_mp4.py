from app.mp4 import mp4_duration_seconds


def _box(kind: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + kind + payload


def test_mp4_duration(tmp_path):
    mvhd = bytes([0, 0, 0, 0])
    mvhd += (0).to_bytes(4, "big") * 2
    mvhd += (1000).to_bytes(4, "big")
    mvhd += (15000).to_bytes(4, "big")
    mvhd += bytes(60)
    data = _box(b"ftyp", b"isom" + b"\x00" * 8) + _box(b"moov", _box(b"mvhd", mvhd))
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)
    assert mp4_duration_seconds(path) == 15
