import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { initial } from "../format";
import { haptic, shareVideo } from "../telegram";
import CommentsSheet from "./CommentsSheet";
import CommunityView from "./CommunityView";
import { SearchIcon } from "./Icons";
import VideoSlide from "./VideoSlide";

export default function Feed({ me, query, botUsername, onProfile, onToast, onLive, onUpload, onSearch }) {
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(0);
  const [done, setDone] = useState(false);
  const [active, setActive] = useState(0);
  const [muted, setMuted] = useState(true);
  const [commentsFor, setCommentsFor] = useState(null);
  const [loading, setLoading] = useState(true);
  const scroller = useRef(null);
  const tabs = useRef(null);
  const [followed, setFollowed] = useState([]);
  const seen = useRef(new Set());
  const loadingMore = useRef(false);

  const load = useCallback(async (reset) => {
    if (loadingMore.current) return;
    loadingMore.current = true;
    try {
      const page = await api.feed({
        tab: query.tab,
        hashtag: query.hashtag,
        author: query.author,
        start: reset ? query.start : "",
        q: query.q,
        cursor: reset ? 0 : cursor,
        limit: query.tab === "community" ? 12 : 5,
      });
      setItems((current) => (reset ? page.items : [...current, ...page.items.filter((item) => !current.some((have) => have.id === item.id))]));
      setCursor(page.next_cursor ?? 0);
      setDone(page.next_cursor == null);
      if (reset) setActive(0);
    } catch (error) {
      onToast(error.message);
    } finally {
      setLoading(false);
      loadingMore.current = false;
    }
  }, [cursor, onToast, query.author, query.hashtag, query.q, query.start, query.tab]);

  useEffect(() => {
    setLoading(true);
    setItems([]);
    setDone(false);
    setCursor(0);
    seen.current.clear();
    loadingMore.current = false;
    scroller.current?.scrollTo({ top: 0 });
    load(true);
    // query identity is the reload key
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.tab, query.hashtag, query.author, query.start, query.q]);

  useEffect(() => {
    if (query.tab !== "following") return undefined;
    let alive = true;
    api.people()
      .then((data) => alive && setFollowed((data.items || []).filter((person) => person.followed)))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [query.tab]);

  useEffect(() => {
    const root = tabs.current;
    const activeTab = root?.querySelector(".active");
    if (!root || !activeTab) return;
    root.scrollTo({ left: activeTab.offsetLeft - (root.clientWidth - activeTab.clientWidth) / 2 });
  }, [query.tab]);

  useEffect(() => {
    const root = scroller.current;
    if (!root) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.6) {
            setActive(Number(entry.target.dataset.index));
          }
        });
      },
      { root, threshold: 0.6 }
    );
    root.querySelectorAll("[data-index]").forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [items]);

  useEffect(() => {
    const video = items[active];
    if (!video || seen.current.has(video.id)) return;
    seen.current.add(video.id);
    api.view(video.id).catch(() => {});
    if (!done && active >= items.length - 2) load(false);
  }, [active, done, items, load]);

  useEffect(() => {
    function onKey(event) {
      if (commentsFor) return;
      const root = scroller.current;
      if (!root) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const next = event.key === "ArrowDown" ? active + 1 : active - 1;
        const node = root.querySelector(`[data-index="${next}"]`);
        node?.scrollIntoView({ behavior: "smooth" });
      }
      if (event.key === "m") setMuted((value) => !value);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, commentsFor]);

  function patch(id, recipe) {
    setItems((current) => current.map((item) => (item.id === id ? recipe(item) : item)));
  }

  async function like(video, onlyLike) {
    if (onlyLike && video.liked) {
      patch(video.id, (item) => ({ ...item }));
      return;
    }
    const nextLiked = onlyLike ? true : !video.liked;
    patch(video.id, (item) => ({
      ...item,
      liked: nextLiked,
      likes_count: item.likes_count + (nextLiked ? 1 : -1),
    }));
    try {
      const result = await api.like(video.id);
      patch(video.id, (item) => ({ ...item, ...result }));
      if (result.liked) haptic("light");
    } catch (error) {
      patch(video.id, () => video);
      onToast(error.message);
    }
  }

  async function follow(author) {
    patchAuthor(author.id, { followed: !author.followed });
    try {
      const result = await api.follow(author.id);
      patchAuthor(author.id, { followed: result.followed });
      setFollowed((current) => {
        if (result.followed) return current.some((person) => person.id === author.id) ? current : [...current, author];
        return current.filter((person) => person.id !== author.id);
      });
      haptic("light");
    } catch (error) {
      patchAuthor(author.id, { followed: author.followed });
      onToast(error.message);
    }
  }

  function patchAuthor(id, extra) {
    setItems((current) =>
      current.map((item) => (item.author?.id === id ? { ...item, author: { ...item.author, ...extra } } : item))
    );
  }

  const communityGrid = query.tab === "community" && !query.start;
  const followingHome = query.tab === "following" && !query.author;

  async function openFollowed(person) {
    try {
      const page = await api.feed({ author: person.id, limit: 1 });
      const first = page.items[0];
      if (!first) {
        onToast("Ин корбар видео надорад.");
        return;
      }
      query.openFollowing(first.id);
    } catch (error) {
      onToast(error.message);
    }
  }

  function onGridScroll(event) {
    const node = event.currentTarget;
    if (!done && node.scrollTop + node.clientHeight >= node.scrollHeight - 240) load(false);
  }

  const player = (
      <div ref={scroller} className={`feed-scroller${commentsFor ? " locked" : ""}`}>
        {loading && <div className="center-screen">Бор шуда истодааст…</div>}
        {!loading && items.length === 0 && (
          <div className="center-screen">
            <div className="logo"><span>Mini</span><span>Tok</span></div>
            <p className="hint">
              {query.q ? "Чизе ёфт нашуд." : query.tab === "following" ? "Ҳанӯз ба касе обуна нестед." : "Видео нест. Аввалинро бор кунед."}
            </p>
          </div>
        )}
        {items.map((video, index) => (
          <div key={video.id} data-index={index} style={{ height: "100%" }}>
            <VideoSlide
              video={video}
              active={index === active}
              near={Math.abs(index - active) <= 2}
              muted={muted}
              onToggleMute={() => setMuted((value) => !value)}
              onLike={(onlyLike) => like(video, onlyLike)}
              onComment={() => setCommentsFor(video)}
              onShare={() => shareVideo(video, botUsername)}
              onProfile={onProfile}
              onFollow={follow}
              onTag={(tag) => query.setHashtag(tag.toLowerCase())}
            />
          </div>
        ))}
      </div>
  );

  return (
    <>
      <div className="topbar">
        <button className="live-btn" onClick={onLive} aria-label="LIVE">
          <span className="live-ant" />
          LIVE
        </button>
        <div className="top-tabs" ref={tabs}>
          <button className={query.tab === "community" ? "tab active" : "tab"} onClick={() => query.setTab("community")}>
            Ҷамоат
          </button>
          <button className={query.tab === "following" ? "tab active" : "tab"} onClick={() => query.setTab("following")}>
            Обунаҳо
          </button>
          <button className={query.tab === "foryou" && !query.author ? "tab active" : "tab"} onClick={() => query.setTab("foryou")}>
            Тавсияҳо
          </button>
        </div>
        <button className="search-btn" onClick={onSearch} aria-label="Ҷустуҷӯ">
          <SearchIcon />
        </button>
      </div>
      {query.hashtag && (
        <button className="filter-chip" onClick={() => query.setHashtag("")}>
          #{query.hashtag} ×
        </button>
      )}
      {query.q && (
        <button className="filter-chip search-chip" onClick={() => query.setSearch("")}>
          {query.q} ×
        </button>
      )}
      {communityGrid ? (
        <CommunityView
          items={items}
          loading={loading}
          onOpen={(video) => query.openCommunity(video.id)}
          onProfile={onProfile}
          onLike={(video) => like(video)}
          onScroll={onGridScroll}
        />
      ) : followingHome ? (
        <div className="follow-layout">
          <div className="follow-rail">
            <button className="story" onClick={onUpload}>
              <span className="story-face create">
                {me.photo_url ? <img src={me.photo_url} alt="" /> : <span>{initial(me.name)}</span>}
                <i>+</i>
              </span>
              <em>Эҷод</em>
            </button>
            {followed.map((person) => (
              <button key={person.id} className="story" onClick={() => openFollowed(person)}>
                <span className="story-face ring-pink">
                  {person.photo_url ? <img src={person.photo_url} alt="" /> : <span>{initial(person.name)}</span>}
                  <i className="story-bars" />
                </span>
                <em>{person.username || person.name}</em>
              </button>
            ))}
          </div>
          {player}
        </div>
      ) : (
        <>
          {player}
          {query.tab === "community" && query.start && (
            <button className="viewer-back" onClick={() => query.setTab("community")} aria-label="Бозгашт">←</button>
          )}
        </>
      )}
      {commentsFor && (
        <CommentsSheet
          video={items.find((item) => item.id === commentsFor.id) || commentsFor}
          onClose={() => setCommentsFor(null)}
          onCount={(count) => patch(commentsFor.id, (item) => ({ ...item, comments_count: count }))}
        />
      )}
      <span className="sr-only">{me.username}</span>
    </>
  );
}
