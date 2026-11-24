from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import media_url
from .models import Comment, CommentLike, Follow, Like, User, Video, VideoHashtag


def iso(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def display_name(user: User) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(part for part in parts if part).strip()
    return name or user.username or "Корбар"


def stats_for(db: Session, user_id: int, include_processing: bool) -> dict:
    video_query = db.query(func.count(Video.id)).filter(Video.user_id == user_id, Video.status != "failed")
    if not include_processing:
        video_query = video_query.filter(Video.status == "ready")
    videos = video_query.scalar() or 0
    likes = (
        db.query(func.coalesce(func.sum(Video.likes_count), 0))
        .filter(Video.user_id == user_id, Video.status != "failed")
        .scalar()
        or 0
    )
    followers = db.query(func.count()).select_from(Follow).filter(Follow.following_id == user_id).scalar() or 0
    following = db.query(func.count()).select_from(Follow).filter(Follow.follower_id == user_id).scalar() or 0
    return {
        "videos_count": int(videos),
        "likes_count": int(likes),
        "followers_count": int(followers),
        "following_count": int(following),
    }


def present_user(db: Session, user: User, me: User | None) -> dict:
    followed = False
    if me is not None and me.id != user.id:
        followed = (
            db.query(Follow)
            .filter(Follow.follower_id == me.id, Follow.following_id == user.id)
            .first()
            is not None
        )
    return {
        "id": user.id,
        "username": user.username,
        "name": display_name(user),
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "photo_url": user.photo_url,
        "bio": user.bio or "",
        "links": user.links or "",
        "is_demo": bool(user.is_demo),
        "is_me": me is not None and me.id == user.id,
        "followed": followed,
        **stats_for(db, user.id, include_processing=me is not None and me.id == user.id),
    }


def present_videos(db: Session, videos: list[Video], me: User) -> list[dict]:
    if not videos:
        return []
    ids = [video.id for video in videos]
    user_ids = {video.user_id for video in videos}
    users = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids))}
    liked = {
        row.video_id
        for row in db.query(Like.video_id).filter(Like.user_id == me.id, Like.video_id.in_(ids))
    }
    followed = {
        row.following_id
        for row in db.query(Follow.following_id).filter(
            Follow.follower_id == me.id, Follow.following_id.in_(user_ids)
        )
    }
    tags: dict[str, list[str]] = defaultdict(list)
    for row in db.query(VideoHashtag).filter(VideoHashtag.video_id.in_(ids)):
        tags[row.video_id].append(row.tag)
    result = []
    for video in videos:
        author = users.get(video.user_id)
        result.append(
            {
                "id": video.id,
                "caption": video.caption or "",
                "hashtags": tags.get(video.id, []),
                "status": video.status,
                "src": media_url(video.src),
                "hls": media_url(video.hls),
                "poster": media_url(video.poster),
                "duration": video.duration,
                "likes_count": video.likes_count,
                "comments_count": video.comments_count,
                "views_count": video.views_count,
                "liked": video.id in liked,
                "error": video.error,
                "created_at": iso(video.created_at),
                "author": None
                if author is None
                else {
                    "id": author.id,
                    "username": author.username,
                    "name": display_name(author),
                    "photo_url": author.photo_url,
                    "followed": author.id in followed,
                    "is_me": author.id == me.id,
                },
            }
        )
    return result


def present_comments(db: Session, comments: list[Comment], me: User) -> list[dict]:
    if not comments:
        return []
    user_ids = {comment.user_id for comment in comments}
    users = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids))}
    ids = [comment.id for comment in comments]
    liked = {
        row.comment_id
        for row in db.query(CommentLike.comment_id).filter(
            CommentLike.user_id == me.id, CommentLike.comment_id.in_(ids)
        )
    }
    items = []
    for comment in comments:
        author = users.get(comment.user_id)
        items.append(
            {
                "id": comment.id,
                "text": comment.text,
                "likes_count": comment.likes_count,
                "liked": comment.id in liked,
                "created_at": iso(comment.created_at),
                "author": {
                    "id": author.id if author else comment.user_id,
                    "username": author.username if author else None,
                    "name": display_name(author) if author else "Корбар",
                    "photo_url": author.photo_url if author else None,
                },
            }
        )
    return items
