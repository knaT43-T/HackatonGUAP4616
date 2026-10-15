// Единая точка правды по адресам бэкенда.
//
// VITE_API_URL / VITE_WS_URL читаются из .env (см. .env.example).
// Если переменные не заданы — берём тот же хост, что и страница, порт 8000.
// Это дефолт для локальной разработки: фронт на :5173, бэкенд на :8000,
// cookie при этом остаётся same-site и улетает без сюрпризов.

const API_PORT = 8000;

function defaultApiUrl() {
  const proto = location.protocol === "https:" ? "https:" : "http:";
  return `${proto}//${location.hostname}:${API_PORT}`;
}

export const API_URL = import.meta.env.VITE_API_URL || defaultApiUrl();

export const WS_URL =
  import.meta.env.VITE_WS_URL || `${API_URL.replace(/^http/, "ws")}/ws`;

// Треки приходят с относительным url (/media/xxx.mp3) — склеиваем с адресом API.
// За одним прокси (nginx.conf) путь можно использовать как есть.
export function mediaUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_URL}${path}`;
}
