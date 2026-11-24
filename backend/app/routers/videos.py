from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..cache import redis_client
from ..db import get_db
from ..limit import enforce
from ..media import create_video, delete_video_files, enqueue, new_id, parse_tags, resolve_duration, save_upload
from ..models import Comment, CommentLike, Follow, Like, User, Video, VideoHashtag, View, utc_now
from ..notify import notify
from ..present import present_comments, present_videos

router = APIRouter(prefix="/api", tags=["videos"])


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=400)


def _sync_like_count(db: Session, video: Video) -> int:
    video.likes_count = db.query(Like).filter(Like.video_id == video.id).count()
    return video.likes_count


def _sync_comment_count(db: Session, video: Video) -> int:
    video.comments_count = db.query(Comment).filter(Comment.video_id == video.id).count()
    return video.comments_count


@router.get("/feed")
def feed(
    tab: str = Query(default="foryou"),
    hashtag: str = Query(default=""),
    q: str = Query(default=""),
    author: int | None = Query(default=None),
    start: str = Query(default=""),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=6, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tag = hashtag.lstrip("#").strip().lower()
    text = q.strip().replace("%", "").replace("_", "")[:40]
    cache_key = None
    use_cache = tab == "foryou" and not author and not start and not text
    if use_cache:
        cache_key = f"feed:foryou:{tag or '*'}:{cursor}:{limit}"
        client = redis_client()
        if client is not None:
            try:
                raw = client.get(cache_key)
            except Exception:
                raw = None
            if raw:
                payload = json.loads(raw)
                videos = db.query(Video).filter(Video.id.in_(payload["ids"])).all() if payload["ids"] else []
                order = {video_id: index for index, video_id in enumerate(payload["ids"])}
                videos.sort(key=lambda item: order.get(item.id, 0))
                return {
                    "items": present_videos(db, videos, user),
                    "next_cursor": payload["next"],
                }

    query = db.query(Video)
    if author:
        query = query.filter(Video.user_id == author)
        if author != user.id:
            query = query.filter(Video.status == "ready")
    else:
        query = query.filter(Video.status == "ready")
    if tag:
        query = query.join(VideoHashtag, VideoHashtag.video_id == Video.id).filter(VideoHashtag.tag == tag)
    if text:
        folded = text.lower()
        query = query.filter(
            or_(
                Video.caption.like(f"%{text}%"),
                Video.id.in_(db.query(VideoHashtag.video_id).filter(VideoHashtag.tag.like(f"%{folded}%"))),
            )
        )
    if tab == "following" and not author:
        query = query.join(Follow, Follow.following_id == Video.user_id).filter(Follow.follower_id == user.id)
    if tab == "foryou" and not author:
        rank = Video.likes_count * 3 + Video.comments_count * 5 + Video.views_count
        query = query.order_by(rank.desc(), Video.created_at.desc())
    else:
        query = query.order_by(Video.created_at.desc())

    rows = query.offset(cursor).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    if start and cursor == 0:
        first = db.get(Video, start)
        if first is not None and first.status == "ready":
            rows = [first] + [row for row in rows if row.id != first.id]
            rows = rows[:limit]
    next_cursor = cursor + limit if has_more else None
    if use_cache and cache_key and redis_client() is not None:
        try:
            redis_client().setex(
                cache_key,
                15,
                json.dumps({"ids": [row.id for row in rows], "next": next_cursor}),
            )
        except Exception:
            pass
    return {"items": present_videos(db, rows, user), "next_cursor": next_cursor}


@router.get("/videos/{video_id}")
def get_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    if video.status != "ready" and video.user_id != user.id:
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    return present_videos(db, [video], user)[0]


@router.post("/videos", status_code=202)
def upload_video(
    file: UploadFile = File(...),
    caption: str = Form(""),
    hashtags: str = Form(""),
    duration: float = Form(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce("upload", user.id)
    caption = caption.strip()
    if len(caption) > 500:
        raise HTTPException(status_code=400, detail="Тавсиф то 500 аломат аст.")
    video_id = new_id()
    path = save_upload(file, video_id)
    try:
        length = resolve_duration(path, duration)
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    video = create_video(db, user.id, path, caption, parse_tags(caption, hashtags), length)
    enqueue(video.id)
    return present_videos(db, [video], user)[0]


@router.delete("/videos/{video_id}")
def delete_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    if video.user_id != user.id:
        raise HTTPException(status_code=403, detail="Фақат видеои худро нест карда метавонед.")
    comment_ids = [row.id for row in db.query(Comment.id).filter(Comment.video_id == video_id)]
    if comment_ids:
        db.query(CommentLike).filter(CommentLike.comment_id.in_(comment_ids)).delete(synchronize_session=False)
    db.query(Comment).filter(Comment.video_id == video_id).delete(synchronize_session=False)
    db.query(Like).filter(Like.video_id == video_id).delete(synchronize_session=False)
    db.query(View).filter(View.video_id == video_id).delete(synchronize_session=False)
    db.query(VideoHashtag).filter(VideoHashtag.video_id == video_id).delete(synchronize_session=False)
    delete_video_files(video)
    db.delete(video)
    db.commit()
    return {"ok": True}


@router.post("/videos/{video_id}/like")
def toggle_like(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce("like", user.id)
    video = db.get(Video, video_id)
    if video is None or video.status != "ready":
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    existing = db.query(Like).filter(Like.user_id == user.id, Like.video_id == video_id).one_or_none()
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=user.id, video_id=video_id, created_at=utc_now()))
        liked = True
    db.flush()
    count = _sync_like_count(db, video)
    db.commit()
    if liked:
        notify(video.user_id, user, video, "like")
    return {"liked": liked, "likes_count": count}


@router.post("/videos/{video_id}/view")
def add_view(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if video is None or video.status != "ready":
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    seen = db.query(View).filter(View.user_id == user.id, View.video_id == video_id).one_or_none()
    if seen is None:
        try:
            db.add(View(user_id=user.id, video_id=video_id))
            video.views_count += 1
            db.commit()
        except IntegrityError:
            db.rollback()
    return {"views_count": video.views_count}


@router.get("/videos/{video_id}/comments")
def list_comments(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    rows = (
        db.query(Comment)
        .filter(Comment.video_id == video_id)
        .order_by(Comment.created_at.desc())
        .limit(100)
        .all()
    )
    return {"items": present_comments(db, rows, user)}


@router.post("/videos/{video_id}/comments")
def add_comment(
    video_id: str,
    body: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce("comment", user.id)
    video = db.get(Video, video_id)
    if video is None or video.status != "ready":
        raise HTTPException(status_code=404, detail="Видео ёфт нашуд.")
    text = body.text.strip()
    if not text or len(text) > 300:
        raise HTTPException(status_code=400, detail="Шарҳ бояд аз 1 то 300 аломат бошад.")
    comment = Comment(
        id=new_id(),
        video_id=video_id,
        user_id=user.id,
        text=text,
        likes_count=0,
        created_at=utc_now(),
    )
    db.add(comment)
    db.flush()
    _sync_comment_count(db, video)
    db.commit()
    db.refresh(comment)
    notify(video.user_id, user, video, "comment", text)
    return present_comments(db, [comment], user)[0]


@router.post("/comments/{comment_id}/like")
def toggle_comment_like(comment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce("like", user.id)
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Шарҳ ёфт нашуд.")
    existing = (
        db.query(CommentLike)
        .filter(CommentLike.user_id == user.id, CommentLike.comment_id == comment_id)
        .one_or_none()
    )
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(CommentLike(user_id=user.id, comment_id=comment_id))
        liked = True
    db.flush()
    comment.likes_count = db.query(CommentLike).filter(CommentLike.comment_id == comment_id).count()
    db.commit()
    return {"liked": liked, "likes_count": comment.likes_count}
