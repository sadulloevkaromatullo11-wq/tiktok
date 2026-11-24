import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const TYPES = ["video/mp4", "video/quicktime", "video/webm"];

export default function UploadView({ onDone, onToast }) {
  const input = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [duration, setDuration] = useState(0);
  const [caption, setCaption] = useState("");
  const [tags, setTags] = useState("");
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  async function choose(event) {
    const next = event.target.files?.[0];
    event.target.value = "";
    if (!next) return;
    setError("");
    const name = next.name.toLowerCase();
    const allowed = TYPES.includes(next.type) || /\.(mp4|mov|webm)$/.test(name);
    if (!allowed) {
      setError("Формат: MP4, MOV ё WEBM.");
      return;
    }
    if (next.size > 50 * 1024 * 1024) {
      setError("Ҳаҷми файл то 50 МБ.");
      return;
    }
    const url = URL.createObjectURL(next);
    const length = await readDuration(url);
    if (!Number.isFinite(length) || length < 5 || length > 60) {
      URL.revokeObjectURL(url);
      setError("Давомнокӣ бояд аз 5 то 60 сония бошад.");
      return;
    }
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return url;
    });
    setFile(next);
    setDuration(length);
  }

  async function submit() {
    if (!file || progress !== null) return;
    setError("");
    const form = new FormData();
    form.set("file", file);
    form.set("caption", caption.trim());
    form.set("hashtags", tags.trim());
    form.set("duration", String(duration));
    setProgress(0);
    try {
      await api.upload(form, setProgress);
      onDone();
    } catch (err) {
      setError(err.message);
      onToast(err.message);
      setProgress(null);
    }
  }

  return (
    <div className="page">
      <h1 style={{ marginTop: 0 }}>Видеои нав</h1>
      <p className="hint">MP4, MOV, WEBM · 5–60 сония · то 50 МБ</p>
      <input ref={input} hidden type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" onChange={choose} />
      {!preview ? (
        <button className="dropzone" onClick={() => input.current?.click()}>Аз галерея интихоб кунед</button>
      ) : (
        <video src={preview} className="mx-auto max-h-[46vh] w-full rounded-2xl bg-black object-contain" controls playsInline />
      )}
      <div style={{ height: 14 }} />
      <textarea className="field" rows={3} maxLength={500} placeholder="Тавсиф нависед… #ҳэштег" value={caption} onChange={(event) => setCaption(event.target.value)} />
      <div style={{ height: 10 }} />
      <input className="field" placeholder="#шаҳр #сафар" value={tags} onChange={(event) => setTags(event.target.value)} />
      {error && <p style={{ color: "#e44558" }}>{error}</p>}
      {progress !== null && (
        <div className="bar" style={{ marginTop: 12 }}>
          <span style={{ width: `${progress}%` }} />
        </div>
      )}
      <div style={{ height: 14 }} />
      <button className="primary" style={{ width: "100%" }} disabled={!file || progress !== null} onClick={submit}>
        {progress === null ? "Интишор" : `Бор шуд ${progress}%`}
      </button>
    </div>
  );
}

function readDuration(url) {
  return new Promise((resolve) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => resolve(video.duration);
    video.onerror = () => resolve(NaN);
    video.src = url;
  });
}
