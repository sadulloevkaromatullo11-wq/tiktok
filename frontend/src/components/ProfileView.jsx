import { useEffect, useState } from "react";
import { api } from "../api";
import { compact, initial } from "../format";
import { inTelegram, switchDemo } from "../telegram";

export default function ProfileView({ userId, me, demoEnabled, onOpenVideo, onMe, onToast }) {
  const [user, setUser] = useState(null);
  const [videos, setVideos] = useState([]);
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState("");
  const [links, setLinks] = useState("");

  async function reload() {
    const [profile, feed] = await Promise.all([
      api.user(userId),
      api.feed({ author: userId, limit: 18 }),
    ]);
    setUser(profile);
    setVideos(feed.items);
    setBio(profile.bio || "");
    setLinks(profile.links || "");
    if (profile.is_me) onMe(profile);
  }

  useEffect(() => {
    let alive = true;
    reload().catch((error) => alive && onToast(error.message));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function save(event) {
    event.preventDefault();
    try {
      const updated = await api.updateMe({ bio, links });
      setUser(updated);
      onMe(updated);
      setEditing(false);
    } catch (error) {
      onToast(error.message);
    }
  }

  async function follow() {
    try {
      const result = await api.follow(user.id);
      setUser((current) => ({ ...current, followed: result.followed, followers_count: result.followers_count }));
    } catch (error) {
      onToast(error.message);
    }
  }

  async function remove(video, event) {
    event.stopPropagation();
    if (!window.confirm("Ин видео нест карда шавад?")) return;
    try {
      await api.deleteVideo(video.id);
      setVideos((list) => list.filter((item) => item.id !== video.id));
    } catch (error) {
      onToast(error.message);
    }
  }

  if (!user) return <div className="center-screen">Бор шуда истодааст…</div>;

  return (
    <div className="page">
      <div style={{ display: "grid", justifyItems: "center", gap: 8 }}>
        <div className="avatar-fallback" style={{ width: 88, height: 88, fontSize: 32 }}>
          {user.photo_url ? <img src={user.photo_url} alt="" style={{ width: "100%", height: "100%", borderRadius: 99, objectFit: "cover" }} /> : initial(user.name)}
        </div>
        <h1 style={{ margin: 0, fontSize: 22 }}>{user.name}</h1>
        <div className="hint">@{user.username || user.id}</div>
        {user.is_me ? (
          <button className="ghost" onClick={() => setEditing((value) => !value)}>Таҳрири профил</button>
        ) : (
          <button className="primary" onClick={follow}>{user.followed ? "Обуна шудед" : "Обуна шудан"}</button>
        )}
      </div>
      <div className="stats">
        <div><b>{compact(user.videos_count)}</b><span>Видео</span></div>
        <div><b>{compact(user.likes_count)}</b><span>Лайк</span></div>
        <div><b>{compact(user.followers_count)}</b><span>Обуначиён</span></div>
        <div><b>{compact(user.following_count)}</b><span>Обунаҳо</span></div>
      </div>
      {user.bio && <p style={{ textAlign: "center" }}>{user.bio}</p>}
      {user.links && (
        <p style={{ textAlign: "center" }}>
          <a href={user.links} target="_blank" rel="noreferrer">{user.links}</a>
        </p>
      )}
      {editing && (
        <form onSubmit={save} style={{ display: "grid", gap: 10 }}>
          <textarea className="field" maxLength={160} value={bio} onChange={(event) => setBio(event.target.value)} placeholder="Дар бораи ман" />
          <input className="field" maxLength={200} value={links} onChange={(event) => setLinks(event.target.value)} placeholder="Истинод" />
          <button className="primary" type="submit">Захира</button>
        </form>
      )}
      {demoEnabled && me.is_demo && !inTelegram() && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center", margin: "8px 0 16px" }}>
          <button className="ghost" onClick={() => switchDemo(1001)}>Меҳмон</button>
          <button className="ghost" onClick={() => switchDemo(1002)}>Самандар</button>
        </div>
      )}
      <div className="grid-videos">
        {videos.map((video) => (
          <button key={video.id} className="tile" onClick={() => video.status === "ready" && onOpenVideo(video)}>
            {video.poster ? <img src={video.poster} alt="" /> : video.src && video.status === "ready" ? <video src={video.src} muted preload="metadata" /> : null}
            {video.status !== "ready" && <em className="badge">{video.status === "processing" ? "Коркард" : "Хато"}</em>}
            <i>♥ {compact(video.likes_count)}</i>
            {user.is_me && (
              <em className="badge" style={{ left: "auto", right: 6 }} onClick={(event) => remove(video, event)}>
                Нест
              </em>
            )}
          </button>
        ))}
      </div>
      {videos.length === 0 && <p className="hint" style={{ textAlign: "center" }}>Видео нест.</p>}
    </div>
  );
}
