from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import media_url
from ..db import get_db
from ..limit import enforce
from ..models import Comment, DirectMessage, Follow, Like, User, Video, utc_now
from ..present import display_name, iso, present_user

router = APIRouter(prefix="/api", tags=["users"])


class ProfileUpdate(BaseModel):
    bio: str = Field(default="", max_length=160)
    links: str = Field(default="", max_length=200)


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return present_user(db, user, user)


@router.patch("/me")
def update_me(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce("profile", user.id)
    user.bio = body.bio.strip()
    user.links = body.links.strip()
    db.commit()
    db.refresh(user)
    return present_user(db, user, user)


@router.get("/people")
def people(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(User).filter(User.id != user.id).order_by(User.created_at.desc()).limit(40).all()
    return {"items": [present_user(db, row, user) for row in rows]}


@router.get("/users/{user_id}")
def get_user(user_id: int, me_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Корбар ёфт нашуд.")
    return present_user(db, user, me_user)


@router.post("/users/{user_id}/follow")
def toggle_follow(user_id: int, me_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce("follow", me_user.id)
    if user_id == me_user.id:
        raise HTTPException(status_code=400, detail="Ба худ обуна шудан мумкин нест.")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Корбар ёфт нашуд.")
    existing = (
        db.query(Follow)
        .filter(Follow.follower_id == me_user.id, Follow.following_id == user_id)
        .one_or_none()
    )
    if existing:
        db.delete(existing)
        followed = False
    else:
        db.add(Follow(follower_id=me_user.id, following_id=user_id, created_at=utc_now()))
        followed = True
    db.commit()
    followers = db.query(Follow).filter(Follow.following_id == user_id).count()
    return {"followed": followed, "followers_count": followers}


def _actor(user: User) -> dict:
    return {
        "id": user.id,
        "name": display_name(user),
        "username": user.username,
        "photo_url": user.photo_url,
    }


@router.get("/inbox")
def inbox(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    videos = db.query(Video).filter(Video.user_id == user.id, Video.status != "failed").all()
    by_id = {video.id: video for video in videos}
    events: list[tuple] = []
    if by_id:
        likes = (
            db.query(Like, User)
            .join(User, User.id == Like.user_id)
            .filter(Like.video_id.in_(by_id), Like.user_id != user.id)
            .all()
        )
        for like, actor in likes:
            video = by_id[like.video_id]
            events.append(
                (
                    like.created_at,
                    {
                        "id": f"like-{like.user_id}-{like.video_id}",
                        "type": "like",
                        "text": "видеои шуморо писанд кард",
                        "preview": "",
                        "created_at": iso(like.created_at),
                        "actor": _actor(actor),
                        "video_id": video.id,
                        "poster": media_url(video.poster),
                    },
                )
            )
        comments = (
            db.query(Comment, User)
            .join(User, User.id == Comment.user_id)
            .filter(Comment.video_id.in_(by_id), Comment.user_id != user.id)
            .all()
        )
        for comment, actor in comments:
            video = by_id[comment.video_id]
            events.append(
                (
                    comment.created_at,
                    {
                        "id": f"comment-{comment.id}",
                        "type": "comment",
                        "text": "шарҳ гузошт",
                        "preview": comment.text[:120],
                        "created_at": iso(comment.created_at),
                        "actor": _actor(actor),
                        "video_id": video.id,
                        "poster": media_url(video.poster),
                    },
                )
            )
    follows = (
        db.query(Follow, User)
        .join(User, User.id == Follow.follower_id)
        .filter(Follow.following_id == user.id)
        .all()
    )
    for follow, actor in follows:
        events.append(
            (
                follow.created_at,
                {
                    "id": f"follow-{follow.follower_id}",
                    "type": "follow",
                    "text": "шуморо пайгирӣ кард",
                    "preview": "",
                    "created_at": iso(follow.created_at),
                    "actor": _actor(actor),
                    "video_id": None,
                    "poster": None,
                },
            )
        )
    events.sort(key=lambda item: item[0] or utc_now(), reverse=True)
    return {"items": [item for _, item in events[:40]]}


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


def _partner(message: DirectMessage, user_id: int) -> int:
    return message.recipient_id if message.sender_id == user_id else message.sender_id


@router.get("/threads")
def threads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(DirectMessage)
        .filter(or_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == user.id))
        .order_by(DirectMessage.created_at.desc())
        .all()
    )
    latest: dict[int, DirectMessage] = {}
    for message in rows:
        other = _partner(message, user.id)
        if other not in latest:
            latest[other] = message
    people = {person.id: person for person in db.query(User).filter(User.id.in_(latest or [0]))}
    items = []
    for other_id, message in latest.items():
        person = people.get(other_id)
        if person is None:
            continue
        items.append(
            {
                "user": _actor(person),
                "text": message.text,
                "mine": message.sender_id == user.id,
                "created_at": iso(message.created_at),
            }
        )
    return {"items": items}


@router.get("/threads/{user_id}")
def thread_messages(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Корбар ёфт нашуд.")
    rows = (
        db.query(DirectMessage)
        .filter(
            or_(
                (DirectMessage.sender_id == user.id) & (DirectMessage.recipient_id == user_id),
                (DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == user.id),
            )
        )
        .order_by(DirectMessage.created_at.asc())
        .all()
    )
    return {
        "items": [
            {"id": row.id, "text": row.text, "mine": row.sender_id == user.id, "created_at": iso(row.created_at)}
            for row in rows
        ]
    }


@router.post("/threads/{user_id}")
def send_message(user_id: int, body: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce("message", user.id)
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Ба худ паём фиристодан мумкин нест.")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Корбар ёфт нашуд.")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Паём холӣ аст.")
    message = DirectMessage(
        id=uuid4().hex[:16],
        sender_id=user.id,
        recipient_id=user_id,
        text=text,
        created_at=utc_now(),
    )
    db.add(message)
    db.commit()
    return {"id": message.id, "text": message.text, "mine": True, "created_at": iso(message.created_at)}
