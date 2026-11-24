import { authHeader } from "./telegram";

const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function parse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail) ? detail[0]?.msg : detail;
    throw new Error(message || "Хатогӣ рух дод");
  }
  return data;
}

export function request(path, { method = "GET", body } = {}) {
  const headers = { Authorization: authHeader() };
  const options = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  return fetch(BASE + path, options).then(parse);
}

export const api = {
  config: () => fetch(BASE + "/api/config").then(parse),
  me: () => request("/api/me"),
  people: () => request("/api/people"),
  inbox: () => request("/api/inbox"),
  threads: () => request("/api/threads"),
  messages: (id) => request(`/api/threads/${id}`),
  sendMessage: (id, text) => request(`/api/threads/${id}`, { method: "POST", body: { text } }),
  updateMe: (body) => request("/api/me", { method: "PATCH", body }),
  user: (id) => request(`/api/users/${id}`),
  follow: (id) => request(`/api/users/${id}/follow`, { method: "POST" }),
  feed: (params) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") query.set(key, value);
    });
    return request(`/api/feed?${query.toString()}`);
  },
  video: (id) => request(`/api/videos/${id}`),
  like: (id) => request(`/api/videos/${id}/like`, { method: "POST" }),
  view: (id) => request(`/api/videos/${id}/view`, { method: "POST" }),
  comments: (id) => request(`/api/videos/${id}/comments`),
  addComment: (id, text) => request(`/api/videos/${id}/comments`, { method: "POST", body: { text } }),
  likeComment: (id) => request(`/api/comments/${id}/like`, { method: "POST" }),
  deleteVideo: (id) => request(`/api/videos/${id}`, { method: "DELETE" }),
  upload(form, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", BASE + "/api/videos");
      xhr.setRequestHeader("Authorization", authHeader());
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status >= 200 && xhr.status < 300) resolve(data);
          else reject(new Error(data.detail || "Боркунӣ ноком шуд"));
        } catch {
          reject(new Error("Боркунӣ ноком шуд"));
        }
      };
      xhr.onerror = () => reject(new Error("Шабака дастнорас аст"));
      xhr.send(form);
    });
  },
};
