import { useEffect, useState } from "react";
import { api } from "../api";

const KEY = "minitok-search-history";

function readHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string" && item.trim()) : [];
  } catch {
    return [];
  }
}

function writeHistory(items) {
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, 12)));
}

export default function SearchView({ onBack, onSearch }) {
  const [draft, setDraft] = useState("");
  const [items, setItems] = useState(readHistory);
  const [people, setPeople] = useState([]);

  useEffect(() => {
    let alive = true;
    api.people()
      .then((data) => alive && setPeople(data.items || []))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  function remember(text) {
    const value = text.trim();
    if (!value) return;
    const next = [value, ...items.filter((item) => item.toLowerCase() !== value.toLowerCase())].slice(0, 12);
    writeHistory(next);
    setItems(next);
  }

  function submit(text) {
    const value = (text ?? draft).trim();
    if (!value) return;
    remember(value);
    onSearch(value);
  }

  function remove(text) {
    const next = items.filter((item) => item !== text);
    writeHistory(next);
    setItems(next);
  }

  function clear() {
    writeHistory([]);
    setItems([]);
  }

  return (
    <div className="search-page">
      <form className="search-head" onSubmit={(event) => { event.preventDefault(); submit(); }}>
        <button type="button" className="search-back" onClick={onBack} aria-label="Бозгашт">←</button>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ҷустуҷӯ"
          enterKeyHint="search"
          autoFocus
        />
        <button type="submit" className="search-go">Ҷустуҷӯ</button>
      </form>
      <div className="history-head">
        <h1>Таърихи ҷустуҷӯ</h1>
        {items.length > 0 && <button type="button" onClick={clear}>Тоза</button>}
      </div>
      <div className="history-list">
        {items.map((item) => {
          const fresh = people.some((person) => {
            const names = [person.username, person.name].filter(Boolean).map((name) => name.toLowerCase());
            return person.videos_count > 0 && names.includes(item.toLowerCase());
          });
          return (
            <div key={item} className="history-row">
              <button type="button" className="history-main" onClick={() => submit(item)}>
                <span className="history-clock" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="1.7" />
                    <path d="M12 8v4.5l3 2" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </span>
                <span className="history-text">{item}</span>
                {fresh && (
                  <span className="history-fresh">
                    <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                      <circle cx="12" cy="8" r="3" fill="currentColor" />
                      <path d="M6 19c1-3 3.2-4.5 6-4.5S17 16 18 19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Нашри нав
                  </span>
                )}
              </button>
              <button type="button" className="history-x" onClick={() => remove(item)} aria-label="Нест кардан">×</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
