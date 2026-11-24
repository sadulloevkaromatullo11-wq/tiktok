from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Comment, Follow, Like, User, Video, VideoHashtag, utc_now

SAMPLES = [
    (
        1001,
        "joyrides",
        "Шаби Душанбе — чароғҳои шаҳр #шаҳр #шаб",
        ["шаҳр", "шаб"],
        "https://media.w3.org/2010/05/sintel/trailer.mp4",
        15,
        128,
    ),
    (
        1001,
        "escapes",
        "Роҳи кушод ба сӯи кӯҳистон #сафар #табиат",
        ["сафар", "табиат"],
        "https://media.w3.org/2010/05/bunny/trailer.mp4",
        15,
        86,
    ),
    (
        1002,
        "blazes",
        "Оташи ҷашн, ки шабро равшан кард #ҷашн",
        ["ҷашн"],
        "https://media.w3.org/2010/05/video/movie_300.mp4",
        15,
        240,
    ),
    (
        1002,
        "fun",
        "Вақтхушӣ бо дӯстон #дӯстон #ханда",
        ["дӯстон", "ханда"],
        "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        15,
        64,
    ),
]


def seed(db: Session) -> None:
    if db.get(User, 1001) is not None:
        return
    now = utc_now()
    db.add_all(
        [
            User(
                id=1001,
                username="mehmon",
                first_name="Меҳмон",
                last_name="",
                bio="Видеоҳои кӯтоҳ аз шаҳр ва сафар.",
                links="https://t.me/telegram",
                is_demo=True,
                created_at=now,
            ),
            User(
                id=1002,
                username="samandar",
                first_name="Самандар",
                last_name="",
                bio="Лаҳзаҳои хурсандиовар.",
                links="",
                is_demo=True,
                created_at=now,
            ),
        ]
    )
    db.add(Follow(follower_id=1001, following_id=1002, created_at=now))
    for user_id, video_id, caption, tags, src, duration, views in SAMPLES:
        db.add(
            Video(
                id=video_id,
                user_id=user_id,
                caption=caption,
                status="ready",
                src=src,
                duration=duration,
                views_count=views,
                likes_count=0,
                comments_count=0,
                created_at=now,
            )
        )
        for tag in tags:
            db.add(VideoHashtag(video_id=video_id, tag=tag))
    db.flush()
    db.add_all(
        [
            Like(user_id=1002, video_id="joyrides", created_at=now),
            Like(user_id=1001, video_id="blazes", created_at=now),
            Like(user_id=1001, video_id="fun", created_at=now),
            Comment(
                id="c1",
                video_id="joyrides",
                user_id=1002,
                text="Зебо! Шаҳр имшаб ҷон дорад.",
                likes_count=1,
                created_at=now,
            ),
            Comment(
                id="c2",
                video_id="blazes",
                user_id=1001,
                text="Оташ! 🔥",
                likes_count=0,
                created_at=now,
            ),
        ]
    )
    from .models import CommentLike

    db.add(CommentLike(user_id=1001, comment_id="c1"))
    for video_id, count in (("joyrides", 1), ("blazes", 1), ("fun", 1)):
        video = db.get(Video, video_id)
        if video:
            video.likes_count = count
    joy = db.get(Video, "joyrides")
    blaze = db.get(Video, "blazes")
    if joy:
        joy.comments_count = 1
    if blaze:
        blaze.comments_count = 1
    db.commit()
