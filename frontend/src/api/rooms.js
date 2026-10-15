import { api } from "./client";

export function createRoom(name) {
  return api("/api/rooms", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function joinRoom(inviteCode) {
  return api("/api/rooms/join", {
    method: "POST",
    body: JSON.stringify({ invite_code: inviteCode }),
  });
}

export function leaveRoom(roomId) {
  return api(`/api/rooms/${encodeURIComponent(roomId)}/leave`, { method: "POST" });
}
