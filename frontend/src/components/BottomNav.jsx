import { FriendsIcon, HomeIcon, InboxIcon, PlusIcon, ProfileIcon } from "./Icons";

const ITEMS = [
  { id: "feed", label: "Асосӣ", Icon: HomeIcon },
  { id: "friends", label: "Дӯстон", Icon: FriendsIcon },
  { id: "inbox", label: "Паёмҳо", Icon: InboxIcon },
  { id: "profile", label: "Профил", Icon: ProfileIcon },
];

export default function BottomNav({ view, onChange }) {
  const left = ITEMS.slice(0, 2);
  const right = ITEMS.slice(2);
  return (
    <nav className="nav">
      {left.map(({ id, label, Icon }) => (
        <button key={id} className={view === id ? "active" : ""} onClick={() => onChange(id)}>
          <Icon />
          <span>{label}</span>
        </button>
      ))}
      <div className="plus-slot">
        <button className="plus" onClick={() => onChange("upload")} aria-label="Боркунӣ">
          <PlusIcon />
        </button>
      </div>
      {right.map(({ id, label, Icon }) => (
        <button key={id} className={view === id ? "active" : ""} onClick={() => onChange(id)}>
          <Icon />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  );
}
