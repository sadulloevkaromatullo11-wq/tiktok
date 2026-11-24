import { useEffect, useRef, useState } from "react";
import { compact, initial } from "../format";
import { haptic } from "../telegram";
import { CommentIcon, Heart, ShareIcon, SoundIcon } from "./Icons";

export default function VideoSlide({
  video,
  active,
  near,
  muted,
  onToggleMute,
  onLike,
  onComment,
  onShare,
  onProfile,
  onFollow,
  onTag,
}) {
  const ref = useRef(null);
  const barRef = useRef(null);
  const tap = useRef({ time: 0, timer: null });
  const [hearts, setHearts] = useState([]);
  const [flash, setFlash] = useState(false);
  const [broken, setBroken] = useState(false);
  const author = video.author;

  const activeRef = useRef(active);
  activeRef.current = active;

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (!near || (!video.src && !video.hls)) {
      el.pause();
      el.removeAttribute("src");
      return undefined;
    }
    let dead = false;
    let hls = null;
    async function load() {
      const nativeHls = el.canPlayType("application/vnd.apple.mpegurl");
      if (video.hls && nativeHls) el.src = video.hls;
      else if (video.hls) {
        try {
          const { default: Hls } = await import("hls.js");
          if (dead) return;
          if (Hls.isSupported()) {
            hls = new Hls({ maxBufferLength: 12 });
            hls.loadSource(video.hls);
            hls.attachMedia(el);
          } else el.src = video.src;
        } catch {
          el.src = video.src;
        }
      } else {
        el.src = video.src;
      }
      if (!dead && activeRef.current) el.play().catch(() => {});
    }
    load();
    return () => {
      dead = true;
      el.pause();
      hls?.destroy();
    };
  }, [near, video.id, video.src, video.hls]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.muted = muted;
    if (!active) {
      el.pause();
      return;
    }
    el.play().catch(() => {});
  }, [active, muted]);

  function spawnHeart(event) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const id = Date.now() + Math.random();
    setHearts((list) => [...list, { id, x: event.clientX - bounds.left, y: event.clientY - bounds.top }]);
    setTimeout(() => setHearts((list) => list.filter((item) => item.id !== id)), 750);
  }

  function onPointerUp(event) {
    if (event.target.closest("[data-ui]")) return;
    const now = Date.now();
    if (now - tap.current.time < 280) {
      clearTimeout(tap.current.timer);
      tap.current.time = 0;
      spawnHeart(event);
      haptic("medium");
      onLike(true);
      return;
    }
    tap.current.time = now;
    tap.current.timer = setTimeout(() => {
      onToggleMute();
      setFlash(true);
      setTimeout(() => setFlash(false), 650);
    }, 280);
  }

  const tagsInCaption = new Set(
    (video.caption.match(/#[\p{L}\p{N}_]+/gu) || []).map((tag) => tag.slice(1).toLowerCase())
  );

  return (
    <article className="slide" onPointerUp={onPointerUp}>
      {near && (video.src || video.hls) && !broken ? (
        <video
          ref={ref}
          poster={video.poster || undefined}
          playsInline
          loop
          muted={muted}
          preload={active ? "auto" : "metadata"}
          onError={() => setBroken(true)}
          onTimeUpdate={(event) => {
            const node = event.currentTarget;
            if (barRef.current && node.duration) {
              barRef.current.style.width = `${(node.currentTime / node.duration) * 100}%`;
            }
          }}
        />
      ) : null}
      {broken && <div className="center-screen">Видео бор нашуд</div>}
      <div className="scrim" />
      {hearts.map((heart) => (
        <div key={heart.id} className="heart" style={{ left: heart.x, top: heart.y }}>
          <Heart filled size={92} />
        </div>
      ))}
      {flash && (
        <div className="mute-flash">
          <SoundIcon muted={muted} />
        </div>
      )}
      <div className="rail">
        <button data-ui className="avatar-btn" onClick={() => onProfile(author.id)} aria-label="Профил">
          {author.photo_url ? (
            <img src={author.photo_url} alt="" />
          ) : (
            <span className="avatar-fallback">{initial(author.name)}</span>
          )}
          {!author.is_me && (
            <span
              data-ui
              className="follow-dot"
              onClick={(event) => {
                event.stopPropagation();
                onFollow(author);
              }}
            >
              {author.followed ? "✓" : "+"}
            </span>
          )}
        </button>
        <button data-ui onClick={() => onLike(false)} aria-label="Лайк" style={{ color: video.liked ? "#e6436d" : "#fbfbfb" }}>
          <Heart filled={video.liked} />
          <span className="count">{compact(video.likes_count)}</span>
        </button>
        <button data-ui onClick={onComment} aria-label="Шарҳ">
          <CommentIcon />
          <span className="count">{compact(video.comments_count)}</span>
        </button>
        <button data-ui onClick={onShare} aria-label="Мубодила">
          <ShareIcon />
          <span className="count">Фиристодан</span>
        </button>
        <button data-ui onClick={onToggleMute} aria-label={muted ? "Овоз" : "Беовоз"}>
          <SoundIcon muted={muted} />
        </button>
      </div>
      <div className="caption-block">
        <button data-ui className="name" onClick={() => onProfile(author.id)}>
          @{author.username || author.name}
        </button>
        <p>
          {(video.caption || "").split(/(#[\p{L}\p{N}_]+)/gu).map((part, index) =>
            part.startsWith("#") ? (
              <button data-ui key={index} className="tag" onClick={() => onTag(part.slice(1))}>
                {part}
              </button>
            ) : (
              <span key={index}>{part}</span>
            )
          )}
        </p>
        <div>
          {video.hashtags
            .filter((tag) => !tagsInCaption.has(tag))
            .map((tag) => (
              <button data-ui key={tag} className="tag" onClick={() => onTag(tag)}>
                #{tag}
              </button>
            ))}
        </div>
      </div>
      <div className="progress">
        <span ref={barRef} />
      </div>
    </article>
  );
}
