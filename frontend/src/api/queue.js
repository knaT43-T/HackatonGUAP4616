import { api } from "./client";

// Добавление — REST: сервер сам разошлёт queue_update всем в комнате.
// Удаление — командой queue_remove по сокету (host), см. state/room.js.
export function addToQueue(roomId, trackId) {
  return api(`/api/rooms/${encodeURIComponent(roomId)}/queue`, {
    method: "POST",
    body: JSON.stringify({ track_id: trackId }),
  });
}
