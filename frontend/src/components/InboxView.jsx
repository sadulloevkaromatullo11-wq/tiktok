import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { ago, initial } from "../format";
import { FriendsIcon, SearchIcon } from "./Icons";

function Face({ person, className = "" }) {
  return (
    <span className={`story-face ${className}`}>
      {person?.photo_url ? <img src={person.photo_url} alt="" /> : <span>{initial(person?.name)}</span>}
    </span>
  );
}

function ChatPane({ person, onBack, onProfile, onToast }) {
  const [items, setItems] = useState(null);
  const [text, setText] = useState("");

  useEffect(() => {
    let alive = true;
    api.messages(person.id)
      .then((data) => alive && setItems(data.items || []))
      .catch((error) => alive && onToast(error.message));
    return () => {
      alive = false;
    };
  }, [onToast, person.id]);

  async function send(event) {
    event.preventDefault();
    const value = text.trim();
    if (!value) return;
    setText("");
    try {
      const message = await api.sendMessage(person.id, value);
      setItems((current) => [...(current || []), message]);
    } catch (error) {
      setText(value);
      onToast(error.message);
    }
  }

  return (
    <div className="inbox-page chat-page">
      <header className="inbox-head">
        <button className="icon-btn" onClick={onBack} aria-label="Бозгашт">←</button>
        <button className="chat-title" onClick={() => onProfile(person.id)}>
          <Face person={person} className="tiny" />
          <b>{person.name}</b>
        </button>
        <span />
      </header>
      <div className="chat-log">
        {items === null && <p className="hint">Бор шуда истодааст…</p>}
        {items && items.length === 0 && <p className="hint">Аввалин паёмро нависед.</p>}
        {(items || []).map((item) => (
          <div key={item.id} className={item.mine ? "bubble mine" : "bubble"}>
            {item.text}
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={send}>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Паём" maxLength={300} />
        <button className="primary" type="submit">Фиристодан</button>
      </form>
    </div>
  );
}

export default function InboxView({ me, onProfile, onOpenVideo, onUpload, onCommunity, onToast }) {
  const [activity, setActivity] = useState([]);
  const [people, setPeople] = useState([]);
  const [threads, setThreads] = useState([]);
  const [ready, setReady] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("home");
  const [chat, setChat] = useState(null);

  function reload() {
    return Promise.all([api.inbox(), api.people(), api.threads()])
      .then(([inbox, community, chats]) => {
        setActivity(inbox.items || []);
        setPeople(community.items || []);
        setThreads(chats.items || []);
        setReady(true);
      })
      .catch((error) => onToast(error.message));
  }

  useEffect(() => {
    let alive = true;
    reload().finally(() => {
      if (!alive) return;
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const needle = query.trim().toLowerCase();
  const stories = useMemo(
    () => people.filter((person) => !needle || person.name.toLowerCase().includes(needle) || (person.username || "").toLowerCase().includes(needle)),
    [needle, people]
  );
  const chats = useMemo(
    () => threads.filter((item) => !needle || item.user.name.toLowerCase().includes(needle) || item.text.toLowerCase().includes(needle)),
    [needle, threads]
  );
  const latest = activity[0];

  if (chat) {
    return (
      <ChatPane
        person={chat}
        onBack={() => {
          setChat(null);
          reload();
        }}
        onProfile={onProfile}
        onToast={onToast}
      />
    );
  }

  if (mode === "activity") {
    return (
      <div className="inbox-page">
        <header className="inbox-head">
          <button className="icon-btn" onClick={() => setMode("home")} aria-label="Бозгашт">←</button>
          <h1>Фаъолият</h1>
          <span />
        </header>
        {activity.length === 0 && <p className="hint inbox-empty">Ҳанӯз фаъолият нест.</p>}
        <div className="inbox-list">
          {activity.map((item) => (
            <div key={item.id} className="thread-row">
              <button className="thread-main" onClick={() => onProfile(item.actor.id)}>
                <Face person={item.actor} className="ring-pink" />
                <span>
                  <b>{item.actor.name}</b>
                  <p>
                    {item.text}
                    {item.preview ? `: ${item.preview}` : ""}
                    <span> · {ago(item.created_at)}</span>
                  </p>
                </span>
              </button>
              {item.video_id && (
                <button className="inbox-poster" onClick={() => onOpenVideo(item)} aria-label="Видео">
                  {item.poster ? <img src={item.poster} alt="" /> : <span />}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="inbox-page">
      <header className="inbox-head">
        <button className="icon-btn" onClick={onCommunity} aria-label="Ҷамоат">
          <FriendsIcon />
        </button>
        <h1>
          Паёмҳо
          <i className="online-dot" />
        </h1>
        <button className="icon-btn" onClick={() => setSearchOpen((open) => !open)} aria-label="Ҷустуҷӯ">
          <SearchIcon />
        </button>
      </header>
      {searchOpen && (
        <input
          className="inbox-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ҷустуҷӯи паём"
        />
      )}
      <div className="story-rail">
        <button className="story" onClick={onUpload}>
          <span className="story-bubble">Видеои нав</span>
          <span className="story-face create">
            {me.photo_url ? <img src={me.photo_url} alt="" /> : <span>{initial(me.name)}</span>}
            <i>+</i>
          </span>
          <em>Эҷод</em>
        </button>
        <button className="story" onClick={() => onToast("Ҳанӯз хотираи ин рӯз нест.")}>
          <span className="story-face lock" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24">
              <rect x="6" y="11" width="12" height="9" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
              <path d="M8.5 11V8.5a3.5 3.5 0 0 1 7 0V11" fill="none" stroke="currentColor" strokeWidth="1.8" />
            </svg>
          </span>
          <em>Дар ин рӯз</em>
        </button>
        {stories.map((person, index) => (
          <button key={person.id} className="story" onClick={() => setChat(person)}>
            <Face person={person} className={index % 2 ? "ring-cyan" : "ring-pink"} />
            <em>{person.username || person.name}</em>
          </button>
        ))}
      </div>
      <button className="notice-row" onClick={() => setMode("activity")}>
        <span className="notice-icon bolt">⚡</span>
        <span>
          <b>Фаъолият ва обунаҳои нав</b>
          <p>{latest ? `${latest.actor.name} ${latest.text}` : "Лайк, шарҳ ва обунаҳо"}</p>
        </span>
      </button>
      <button className="notice-row" onClick={() => onToast("Огоҳии нави система нест.")}>
        <span className="notice-icon system">▢</span>
        <span>
          <b>Огоҳиҳои система</b>
          <p>Хуш омадед ба Mini TikTok</p>
        </span>
      </button>
      {!ready && <p className="hint inbox-empty">Бор шуда истодааст…</p>}
      <div className="inbox-list">
        {chats.map((item) => (
          <button key={item.user.id} className="thread-row thread-main" onClick={() => setChat(item.user)}>
            <Face person={item.user} className="ring-cyan" />
            <span>
              <b>{item.user.name}</b>
              <p>
                {item.mine ? "Фиристода шуд" : item.text}
                <span> · {ago(item.created_at)}</span>
              </p>
            </span>
          </button>
        ))}
      </div>
      {ready && chats.length === 0 && <p className="hint inbox-empty">Паёми шахсӣ нест. Ба ҳикояи боло пахш кунед.</p>}
    </div>
  );
}
