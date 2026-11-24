import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.auth import verify_init_data


def auth(user_id: int = 1001) -> dict[str, str]:
    return {"Authorization": f"Demo {user_id}"}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_demo_profile_and_feed(client):
    me = client.get("/api/me", headers=auth())
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "mehmon"
    assert body["is_demo"] is True
    feed = client.get("/api/feed", headers=auth())
    assert feed.status_code == 200
    items = feed.json()["items"]
    assert len(items) >= 4
    assert items[0]["author"]["name"]


def test_requires_auth(client):
    assert client.get("/api/feed").status_code == 401


def test_like_comment_follow_and_hashtag(client):
    liked = client.post("/api/videos/escapes/like", headers=auth())
    assert liked.status_code == 200
    assert liked.json()["liked"] is True
    again = client.post("/api/videos/escapes/like", headers=auth())
    assert again.json()["liked"] is False

    too_long = client.post("/api/videos/escapes/comments", headers=auth(), json={"text": "а" * 301})
    assert too_long.status_code == 400

    comment = client.post("/api/videos/escapes/comments", headers=auth(1002), json={"text": "Роҳ зебо аст"})
    assert comment.status_code == 200
    assert comment.json()["author"]["username"] == "samandar"

    heart = client.post(f"/api/comments/{comment.json()['id']}/like", headers=auth())
    assert heart.json()["liked"] is True

    follow = client.post("/api/users/1001/follow", headers=auth(1002))
    assert follow.status_code == 200
    assert follow.json()["followed"] is True
    self_follow = client.post("/api/users/1002/follow", headers=auth(1002))
    assert self_follow.status_code == 400

    tagged = client.get("/api/feed", headers=auth(), params={"hashtag": "сафар"})
    ids = [item["id"] for item in tagged.json()["items"]]
    assert ids == ["escapes"]

    following = client.get("/api/feed", headers=auth(), params={"tab": "following"})
    authors = {item["author"]["id"] for item in following.json()["items"]}
    assert authors == {1002}


def test_search_and_people(client):
    found = client.get("/api/feed", headers=auth(), params={"q": "Душанбе"})
    assert found.status_code == 200
    assert [item["id"] for item in found.json()["items"]] == ["joyrides"]
    people = client.get("/api/people", headers=auth())
    assert people.status_code == 200
    ids = [item["id"] for item in people.json()["items"]]
    assert 1002 in ids
    assert 1001 not in ids


def test_direct_messages(client):
    denied = client.post("/api/threads/1002", json={"text": "Салом"})
    assert denied.status_code == 401
    sent = client.post("/api/threads/1002", headers=auth(), json={"text": "Салом"})
    assert sent.status_code == 200
    assert sent.json()["mine"] is True
    self_message = client.post("/api/threads/1001", headers=auth(), json={"text": "Ман"})
    assert self_message.status_code == 400
    threads = client.get("/api/threads", headers=auth())
    assert threads.json()["items"][0]["user"]["id"] == 1002
    assert threads.json()["items"][0]["text"] == "Салом"
    history = client.get("/api/threads/1002", headers=auth())
    assert history.json()["items"][-1]["text"] == "Салом"


def test_inbox(client):
    denied = client.get("/api/inbox")
    assert denied.status_code == 401
    response = client.get("/api/inbox", headers=auth())
    assert response.status_code == 200
    items = response.json()["items"]
    types = {item["type"] for item in items}
    assert "like" in types
    assert "comment" in types
    assert all(item["actor"]["id"] != 1001 for item in items)


def test_profile_update(client):
    updated = client.patch("/api/me", headers=auth(), json={"bio": "Биои нав", "links": "https://t.me/telegram"})
    assert updated.status_code == 200
    assert updated.json()["bio"] == "Биои нав"


def test_upload_and_delete(client):
    payload = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64
    response = client.post(
        "/api/videos",
        headers=auth(),
        data={"caption": "Нав #тест", "hashtags": "шаҳр", "duration": "12"},
        files={"file": ("clip.mp4", payload, "video/mp4")},
    )
    assert response.status_code == 202
    video_id = response.json()["id"]
    status = "processing"
    for _ in range(40):
        current = client.get(f"/api/videos/{video_id}", headers=auth())
        status = current.json()["status"]
        if status in {"ready", "failed"}:
            break
        time.sleep(0.05)
    assert status == "ready"
    assert "тест" in current.json()["hashtags"]
    removed = client.delete(f"/api/videos/{video_id}", headers=auth())
    assert removed.status_code == 200
    missing = client.get(f"/api/videos/{video_id}", headers=auth())
    assert missing.status_code == 404


def test_init_data_hmac():
    token = "123456:TEST"
    user = json.dumps({"id": 42, "first_name": "Али", "username": "ali"}, ensure_ascii=False, separators=(",", ":"))
    pairs = {"auth_date": str(int(time.time())), "query_id": "AAE", "user": user}
    check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    init_data = urlencode(pairs) + "&hash=" + digest
    verified = verify_init_data(init_data, token)
    assert verified["id"] == 42
    assert verified["first_name"] == "Али"
    with pytest.raises(ValueError):
        verify_init_data(init_data + "x", token)
    old = dict(pairs)
    old["auth_date"] = "100"
    old_check = "\n".join(f"{key}={value}" for key, value in sorted(old.items()))
    old_hash = hmac.new(secret, old_check.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(ValueError):
        verify_init_data(urlencode(old) + "&hash=" + old_hash, token)
