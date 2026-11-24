import { useEffect, useState } from "react";
import { api } from "./api";
import BottomNav from "./components/BottomNav";
import Feed from "./components/Feed";
import InboxView from "./components/InboxView";
import LiveView from "./components/LiveView";
import ProfileView from "./components/ProfileView";
import SearchView from "./components/SearchView";
import UploadView from "./components/UploadView";
import { initTelegram, startVideoId, syncBackButton } from "./telegram";

export default function App() {
  const [me, setMe] = useState(null);
  const [error, setError] = useState("");
  const [view, setView] = useState("feed");
  const [profileId, setProfileId] = useState(null);
  const [toast, setToast] = useState("");
  const [botUsername, setBotUsername] = useState(import.meta.env.VITE_BOT_USERNAME || "");
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [query, setQuery] = useState({ tab: "foryou", hashtag: "", author: "", start: "", q: "" });

  useEffect(() => {
    initTelegram();
    const start = startVideoId();
    if (start) setQuery((current) => ({ ...current, start }));
    api.config().then((config) => {
      setDemoEnabled(Boolean(config.demo));
      if (config.bot_username) setBotUsername(config.bot_username);
    }).catch(() => {});
    api.me().then(setMe).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const playingCommunity = view === "feed" && query.tab === "community" && query.start;
    const onBack = () => {
      if (playingCommunity) {
        setQuery({ tab: "community", hashtag: "", author: "", start: "", q: "" });
        return;
      }
      setView("feed");
      setProfileId(null);
    };
    syncBackButton(view !== "feed" || playingCommunity, onBack);
  }, [query.start, query.tab, view]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(""), 2800);
    return () => clearTimeout(timer);
  }, [toast]);

  function showProfile(id) {
    setProfileId(id);
    setView("profile");
  }

  function openOwnProfile() {
    if (!me) return;
    setProfileId(me.id);
    setView("profile");
  }

  if (!me) {
    return (
      <div className="shell">
        <div className="center-screen">
          <div className="logo"><span>Mini</span><span>Tok</span></div>
          <p className="hint">{error || "Бор шуда истодааст…"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="shell" data-view={view}>
      {view === "feed" && (
        <Feed
          me={me}
          botUsername={botUsername}
          onProfile={showProfile}
          onToast={setToast}
          onLive={() => setView("live")}
          onUpload={() => setView("upload")}
          onSearch={() => setView("search")}
          query={{
            ...query,
            setTab: (tab) => setQuery({ tab, hashtag: "", author: "", start: "", q: "" }),
            setHashtag: (hashtag) => setQuery({ tab: "foryou", hashtag, author: "", start: "", q: "" }),
            setSearch: (text) => setQuery({ tab: "foryou", hashtag: "", author: "", start: "", q: text.trim() }),
            openCommunity: (start) => setQuery({ tab: "community", hashtag: "", author: "", start, q: "" }),
            openFollowing: (start) => setQuery({ tab: "following", hashtag: "", author: "", start, q: "" }),
          }}
        />
      )}
      {view === "search" && (
        <SearchView
          onBack={() => setView("feed")}
          onSearch={(text) => {
            setQuery({ tab: "foryou", hashtag: "", author: "", start: "", q: text.trim() });
            setView("feed");
          }}
        />
      )}
      {view === "live" && (
        <LiveView onBack={() => { setQuery({ tab: "foryou", hashtag: "", author: "", start: "", q: "" }); setView("feed"); }} />
      )}
      {view === "upload" && <UploadView onToast={setToast} onDone={() => showProfile(me.id)} />}
      {view === "inbox" && (
        <InboxView
          me={me}
          onToast={setToast}
          onProfile={showProfile}
          onUpload={() => setView("upload")}
          onCommunity={() => {
            setProfileId(null);
            setQuery({ tab: "community", hashtag: "", author: "", start: "", q: "" });
            setView("feed");
          }}
          onOpenVideo={(item) => {
            setQuery({ tab: "author", hashtag: "", author: me.id, start: item.video_id, q: "" });
            setView("feed");
          }}
        />
      )}
      {view === "profile" && (
        <ProfileView
          userId={profileId || me.id}
          me={me}
          demoEnabled={demoEnabled}
          onMe={setMe}
          onToast={setToast}
          onOpenVideo={(video) => {
            setQuery({ tab: "author", hashtag: "", author: video.author.id, start: video.id, q: "" });
            setView("feed");
          }}
        />
      )}
      {view !== "search" && <BottomNav
        view={
          view === "profile" && profileId === me.id
            ? "profile"
            : view === "inbox"
              ? "inbox"
              : view === "upload"
                ? "upload"
                : view === "feed" && query.tab === "following"
                  ? "friends"
                  : "feed"
        }
        onChange={(next) => {
          if (next === "profile") {
            openOwnProfile();
            return;
          }
          if (next === "feed") {
            setProfileId(null);
            setQuery({ tab: "foryou", hashtag: "", author: "", start: "", q: "" });
            setView("feed");
            return;
          }
          if (next === "friends") {
            setProfileId(null);
            setQuery({ tab: "following", hashtag: "", author: "", start: "", q: "" });
            setView("feed");
            return;
          }
          setView(next);
        }}
      />}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
