import { useEffect, useState } from "react";
import { api } from "../api";
import { ago, initial } from "../format";
import { haptic } from "../telegram";
import { Heart } from "./Icons";

export default function CommentsSheet({ video, onClose, onCount }) {
  const [items, setItems] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    api.comments(video.id).then((data) => {
      if (alive) setItems(data.items);
    }).catch((err) => setError(err.message));
    return () => {
      alive = false;
    };
  }, [video.id]);

  async function send(event) {
    event.preventDefault();
    const value = text.trim();
    if (!value || sending) return;
    setSending(true);
    setError("");
    try {
      const comment = await api.addComment(video.id, value);
      setItems((list) => [comment, ...list]);
      setText("");
      onCount(video.comments_count + 1);
      haptic("light");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function like(comment) {
    const previous = items;
    setItems((list) =>
      list.map((item) =>
        item.id === comment.id
          ? {
              ...item,
              liked: !item.liked,
              likes_count: item.likes_count + (item.liked ? -1 : 1),
            }
          : item
      )
    );
    try {
      const result = await api.likeComment(comment.id);
      setItems((list) => list.map((item) => (item.id === comment.id ? { ...item, ...result } : item)));
    } catch (err) {
      setItems(previous);
      setError(err.message);
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <section className="sheet" onClick={(event) => event.stopPropagation()} role="dialog" aria-label="Шарҳҳо">
        <div className="handle" />
        <strong>{video.comments_count} шарҳ</strong>
        <div className="comments">
          {items.length === 0 && <p className="hint">Ҳанӯз шарҳ нест. Аввалин бошед.</p>}
          {items.map((comment) => (
            <article key={comment.id} className="comment">
              <div className="avatar-fallback" style={{ width: 36, height: 36 }}>
                {comment.author.photo_url ? <img src={comment.author.photo_url} alt="" /> : initial(comment.author.name)}
              </div>
              <div>
                <b>{comment.author.name}</b>
                <span className="hint"> · {ago(comment.created_at)}</span>
                <p>{comment.text}</p>
              </div>
              <button className="ghost" style={{ padding: 6, color: comment.liked ? "#e6436d" : "inherit" }} onClick={() => like(comment)} aria-label="Лайки шарҳ">
                <Heart filled={comment.liked} size={18} />
                <span className="count">{comment.likes_count || ""}</span>
              </button>
            </article>
          ))}
        </div>
        {error && <p className="hint" style={{ color: "#e44558" }}>{error}</p>}
        <form className="composer" onSubmit={send}>
          <input
            value={text}
            maxLength={300}
            placeholder="Шарҳ нависед…"
            onChange={(event) => setText(event.target.value)}
            aria-label="Матни шарҳ"
          />
          <button className="primary" disabled={sending || !text.trim()} type="submit">
            Фиристодан
          </button>
        </form>
        <div className="hint" style={{ textAlign: "right" }}>{text.length}/300</div>
      </section>
    </div>
  );
}
