import { compact, initial } from "../format";
import { Heart } from "./Icons";

export default function CommunityView({ items, loading, onOpen, onProfile, onLike, onScroll }) {
  return (
    <div className="community-layout" onScroll={onScroll}>
      {loading && <p className="hint community-empty">Бор шуда истодааст…</p>}
      {!loading && items.length === 0 && <p className="hint community-empty">Видео нест. Аввалинро бор кунед.</p>}
      <div className="community-grid">
        {items.map((video) => (
          <article key={video.id} className="community-card">
            <button className="community-thumb" onClick={() => onOpen(video)}>
              <video src={video.src} poster={video.poster || undefined} muted playsInline preload="metadata" />
              <span className="play-mark" aria-hidden="true" />
              {video.caption && <span className="community-caption">{video.caption}</span>}
            </button>
            <div className="community-meta">
              <button className="meta-author" onClick={() => onProfile(video.author.id)}>
                <span className="meta-face">
                  {video.author.photo_url ? <img src={video.author.photo_url} alt="" /> : initial(video.author.name)}
                </span>
                <b>{video.author.username || video.author.name}</b>
              </button>
              <button className={video.liked ? "meta-like on" : "meta-like"} onClick={() => onLike(video)} aria-label="Лайк">
                <Heart filled={video.liked} size={16} />
                {compact(video.likes_count)}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
