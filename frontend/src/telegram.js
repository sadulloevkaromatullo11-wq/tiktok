import WebApp from "@twa-dev/sdk";

export function tg() {
  return window.Telegram?.WebApp || WebApp;
}

export function initTelegram() {
  const app = tg();
  const scheme = app?.colorScheme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  document.documentElement.dataset.scheme = scheme;
  const params = app?.themeParams || {};
  const root = document.documentElement;
  Object.entries(params).forEach(([key, value]) => {
    root.style.setProperty(`--tg-theme-${key.replaceAll("_", "-")}`, value);
  });
  try {
    app.ready();
    app.expand();
    app.setHeaderColor("#161722");
    app.setBackgroundColor(scheme === "light" ? "#fbfbfb" : "#161722");
    app.disableVerticalSwipes?.();
  } catch {
    /* берун аз Telegram */
  }
  const inset = app.contentSafeAreaInset || app.safeAreaInset || {};
  if (inset.top) root.style.setProperty("--safe-top", `${inset.top}px`);
  if (inset.bottom) root.style.setProperty("--safe-bottom", `${inset.bottom}px`);
}

export function inTelegram() {
  return Boolean(tg()?.initData);
}

export function authHeader() {
  const initData = tg()?.initData;
  if (initData) return `tma ${initData}`;
  return `Demo ${localStorage.getItem("demoUser") || "1001"}`;
}

export function startVideoId() {
  const fromUrl = new URLSearchParams(location.search).get("v");
  if (fromUrl) return fromUrl;
  const start = tg()?.initDataUnsafe?.start_param || "";
  return start.startsWith("v_") ? start.slice(2) : "";
}

export function haptic(kind = "light") {
  try {
    tg()?.HapticFeedback?.impactOccurred(kind);
  } catch {
    /* ignore */
  }
}

let backHandler = null;

export function syncBackButton(show, onClick) {
  const button = tg()?.BackButton;
  if (!button?.show) return;
  if (backHandler) button.offClick?.(backHandler);
  backHandler = onClick;
  if (show) {
    button.onClick?.(onClick);
    button.show();
  } else {
    button.hide();
  }
}

export function shareVideo(video, botUsername) {
  const link = botUsername
    ? `https://t.me/${botUsername}?startapp=v_${video.id}`
    : `${location.origin}/?v=${video.id}`;
  const text = video.caption || "Ин видеоро тамошо кун";
  const url = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`;
  const app = tg();
  if (app?.openTelegramLink) app.openTelegramLink(url);
  else window.open(url, "_blank", "noopener");
}

export function switchDemo(id) {
  localStorage.setItem("demoUser", String(id));
  location.reload();
}
