from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Video, VideoHashtag, utc_now
from .mp4 import mp4_duration_seconds

log = logging.getLogger("minitok.media")
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="media")


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def sniff_extension(path: Path) -> str | None:
    try:
        head = path.read_bytes()[:32]
    except OSError:
        return None
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return ".mov" if head[8:12] == b"qt  " else ".mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    return None


def _probe_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            log.warning("ffprobe ноком шуд", exc_info=True)
    return mp4_duration_seconds(path)


def resolve_duration(path: Path, claimed: float) -> float:
    probed = _probe_duration(path)
    duration = probed if probed and probed > 0 else claimed
    if duration < settings.min_duration or duration > settings.max_duration + 1:
        raise HTTPException(
            status_code=400,
            detail="Давомнокии видео бояд аз 5 то 60 сония бошад.",
        )
    return duration


def save_upload(file: UploadFile, video_id: str) -> Path:
    target = settings.media_dir / "original" / video_id
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with target.open("wb") as handle:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="Ҳаҷми файл аз 50 МБ зиёд аст.")
                handle.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Файл холӣ аст.")
    ext = sniff_extension(target)
    if ext is None:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Формат дастгирӣ намешавад. MP4, MOV ё WEBM бор кунед.")
    final = target.with_suffix(ext)
    target.replace(final)
    return final


def parse_tags(caption: str, extra: str) -> list[str]:
    import re

    found = re.findall(r"#([\w]{1,40})", caption or "", flags=re.UNICODE)
    found += re.split(r"[\s,]+", extra or "")
    tags: list[str] = []
    seen: set[str] = set()
    for raw in found:
        tag = re.sub(r"[^\w]", "", raw.lstrip("#").strip().lower(), flags=re.UNICODE)
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag[:40])
        if len(tags) >= 8:
            break
    return tags


def create_video(db: Session, user_id: int, path: Path, caption: str, tags: list[str], duration: float) -> Video:
    video = Video(
        id=path.stem,
        user_id=user_id,
        caption=caption,
        status="processing",
        original_path=str(path),
        duration=duration,
        created_at=utc_now(),
    )
    db.add(video)
    for tag in tags:
        db.add(VideoHashtag(video_id=video.id, tag=tag))
    db.commit()
    db.refresh(video)
    return video


def enqueue(video_id: str) -> None:
    executor.submit(process_video, video_id)


def _run_ffmpeg(args: list[str]) -> bool:
    try:
        result = subprocess.run(args, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired):
        log.exception("ffmpeg иҷро нашуд")
        return False
    if result.returncode != 0:
        log.warning("ffmpeg рад кард: %s", result.stderr[-400:])
        return False
    return True


def _public(path: Path) -> str:
    relative = path.relative_to(settings.media_dir).as_posix()
    return f"/media/{relative}"


def _under_media(path: Path) -> bool:
    try:
        path.resolve().relative_to(settings.media_dir.resolve())
        return True
    except ValueError:
        return False


def process_video(video_id: str) -> None:
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None or not video.original_path:
            return
        source = Path(video.original_path)
        if not source.exists():
            video.status = "failed"
            video.error = "Файли аслӣ ёфт нашуд."
            db.commit()
            return
        ready = settings.media_dir / "ready" / f"{video_id}.mp4"
        poster = settings.media_dir / "thumbs" / f"{video_id}.jpg"
        playlist = settings.media_dir / "hls" / video_id / "index.m3u8"
        ffmpeg = shutil.which("ffmpeg")
        ok = False
        if ffmpeg:
            ok = _run_ffmpeg(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    "scale='min(1080,iw)':-2",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-movflags",
                    "+faststart",
                    "-t",
                    "61",
                    str(ready),
                ]
            )
            if ok:
                _run_ffmpeg(
                    [ffmpeg, "-y", "-ss", "0.4", "-i", str(ready), "-frames:v", "1", "-vf", "scale=480:-2", str(poster)]
                )
                playlist.parent.mkdir(parents=True, exist_ok=True)
                hls_ok = _run_ffmpeg(
                    [
                        ffmpeg,
                        "-y",
                        "-i",
                        str(ready),
                        "-hls_time",
                        "2",
                        "-hls_playlist_type",
                        "vod",
                        "-hls_segment_filename",
                        str(playlist.parent / "seg_%03d.ts"),
                        str(playlist),
                    ]
                )
                video.src = _public(ready)
                video.poster = _public(poster) if poster.exists() else None
                video.hls = _public(playlist) if hls_ok and playlist.exists() else None
                source.unlink(missing_ok=True)
                video.original_path = None
        if not ok:
            ext = source.suffix or ".mp4"
            copied = settings.media_dir / "ready" / f"{video_id}{ext}"
            if source.resolve() != copied.resolve():
                shutil.copy2(source, copied)
            video.src = _public(copied)
            video.hls = None
            video.poster = None
        video.status = "ready"
        video.error = None
        db.commit()
        _maybe_s3(db, video)
    except Exception:
        log.exception("Коркарди видео ноком шуд")
        db.rollback()
        failed = db.get(Video, video_id)
        if failed is not None:
            failed.status = "failed"
            failed.error = "Коркарди видео ноком шуд."
            db.commit()
    finally:
        db.close()


def _maybe_s3(db: Session, video: Video) -> None:
    if not settings.use_s3:
        return
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        mapping = {"src": video.src, "poster": video.poster, "hls": video.hls}
        for field, url in list(mapping.items()):
            if not url or not url.startswith("/media/"):
                continue
            path = settings.media_dir / url.removeprefix("/media/")
            if field == "hls":
                folder = path.parent
                for item in folder.rglob("*"):
                    if item.is_file() and _under_media(item):
                        key = item.relative_to(settings.media_dir).as_posix()
                        client.upload_file(str(item), settings.s3_bucket, key)
                if settings.s3_public_url:
                    setattr(video, field, f"{settings.s3_public_url}/{path.relative_to(settings.media_dir).as_posix()}")
                continue
            if path.is_file() and _under_media(path):
                key = path.relative_to(settings.media_dir).as_posix()
                client.upload_file(str(path), settings.s3_bucket, key)
                if settings.s3_public_url:
                    setattr(video, field, f"{settings.s3_public_url}/{key}")
        db.commit()
    except Exception:
        log.exception("Боркунӣ ба S3/R2 ноком шуд. Файли маҳаллӣ мемонад.")


def delete_video_files(video: Video) -> None:
    candidates = [
        Path(video.original_path) if video.original_path else None,
        settings.media_dir / "ready" / f"{video.id}.mp4",
        settings.media_dir / "ready" / f"{video.id}.mov",
        settings.media_dir / "ready" / f"{video.id}.webm",
        settings.media_dir / "thumbs" / f"{video.id}.jpg",
    ]
    for path in candidates:
        if path and path.exists() and _under_media(path):
            path.unlink(missing_ok=True)
    folder = settings.media_dir / "hls" / video.id
    if folder.exists() and _under_media(folder):
        shutil.rmtree(folder, ignore_errors=True)
