// Тонкий транспортный слой над WebSocket: подключение, join, ping-цикл,
// автопереподключение с backoff. Никакой бизнес-логики — события уходят
// в колбэк onEvent, статус соединения — в onStatus.
//
// Коды закрытия из API.md §6:
//   4401 — нет сессии: не переподключаемся, сообщаем наверх;
//   4404 — сокет вытеснен новой вкладкой: молча останавливаемся.

import { WS_URL } from "../config";
import { createClock } from "./clock";

const PING_INTERVAL_MS = 4000;
const MAX_BACKOFF_MS = 15_000;

export function createRoomSocket({ join, onEvent, onStatus }) {
  const clock = createClock();
  let ws = null;
  let stopped = false;
  let attempts = 0;
  let pingTimer = null;
  let reconnectTimer = null;

  function setStatus(status) {
    onStatus?.(status);
  }

  function connect() {
    if (stopped) return;
    setStatus(attempts === 0 ? "connecting" : "reconnecting");

    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      attempts = 0;
      send({ type: "join", ...join });
      // После join и после reconnect смещение часов может быть устаревшим —
      // меряем сразу (front.md §11).
      ping();
      pingTimer = setInterval(ping, PING_INTERVAL_MS);
      document.addEventListener("visibilitychange", onVisibility);
      setStatus("online");
    };

    ws.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!message || typeof message !== "object") return;
      if (message.type === "pong") {
        clock.register(message.client_time, message.server_time);
        return;
      }
      onEvent?.(message);
    };

    ws.onclose = (event) => {
      teardownSocketListeners();
      if (stopped) return;
      if (event.code === 4401) {
        stopped = true;
        setStatus("unauthorized");
        return;
      }
      if (event.code === 4404) {
        stopped = true;
        setStatus("superseded");
        return;
      }
      scheduleReconnect();
    };

    ws.onerror = () => {
      // Браузер сам закроет сокет — решение принимает onclose.
    };
  }

  function onVisibility() {
    if (document.visibilityState === "visible") ping();
  }

  function teardownSocketListeners() {
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
    document.removeEventListener("visibilitychange", onVisibility);
  }

  function scheduleReconnect() {
    setStatus("reconnecting");
    attempts += 1;
    const delay = Math.min(1000 * 2 ** (attempts - 1), MAX_BACKOFF_MS);
    reconnectTimer = setTimeout(connect, delay);
  }

  function ping() {
    send({ type: "ping", client_time: Date.now() });
  }

  function send(command) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    try {
      ws.send(JSON.stringify(command));
      return true;
    } catch {
      return false;
    }
  }

  function close() {
    stopped = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    teardownSocketListeners();
    if (ws) {
      ws.onclose = null; // закрываем осознанно: статусы больше не нужны
      try {
        ws.close(1000, "leave");
      } catch {
        /* сокет уже мёртв */
      }
      ws = null;
    }
    setStatus("closed");
  }

  return {
    connect,
    close,
    send,
    get offsetMs() {
      return clock.offsetMs;
    },
    get rttMs() {
      return clock.rttMs;
    },
  };
}
