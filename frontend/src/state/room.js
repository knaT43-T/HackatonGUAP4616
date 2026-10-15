// Комнатное состояние: единственное место, где разбираются WS-события
// (один switch по msg.type — front.md §10). Компоненты читают этот стор
// и шлют команды через sendCommand, не зная про транспорт.

import { reactive } from "vue";

import { createRoomSocket } from "../ws/client";

export const room = reactive({
  room: null, // { id, name, invite_code, creator_id, host_id, created_at }
  state: null, // якорь воспроизведения (state_payload)
  queue: [],
  members: [],
  meId: null,
  role: "listener", // host | listener — из joined / members_update
  status: "idle", // idle | connecting | online | reconnecting | closed | unauthorized | superseded
  fatal: null, // "not_found" — комнаты больше нет
  toasts: [],
});

let socket = null;
let toastSeq = 0;

export function connectRoom(inviteCode) {
  disconnectRoom();

  socket = createRoomSocket({
    join: { invite_code: inviteCode },
    onEvent: dispatch,
    onStatus: (status) => {
      room.status = status;
    },
  });
  socket.connect();
}

export function disconnectRoom() {
  if (socket) {
    socket.close();
    socket = null;
  }
  room.room = null;
  room.state = null;
  room.queue = [];
  room.members = [];
  room.meId = null;
  room.role = "listener";
  room.status = "idle";
  room.fatal = null;
  room.toasts = [];
}

export function sendCommand(type, extra = null) {
  if (!socket) return false;
  return socket.send({ type, ...(extra || {}) });
}

// Смещение часов сервер↔клиент (мс) — для пересчёта позиции (position.js).
export function serverOffsetMs() {
  return socket ? socket.offsetMs : 0;
}

export function addToast(text, kind = "system") {
  const id = ++toastSeq;
  room.toasts.push({ id, text, kind });
  if (room.toasts.length > 4) room.toasts.splice(0, room.toasts.length - 4);
  setTimeout(() => {
    const index = room.toasts.findIndex((toast) => toast.id === id);
    if (index !== -1) room.toasts.splice(index, 1);
  }, 6000);
}

function syncMyRole() {
  const me = room.members.find((member) => member.id === room.meId);
  if (me) room.role = me.role;
}

function dispatch(msg) {
  switch (msg.type) {
    case "joined":
      room.meId = msg.participant_id;
      room.role = msg.role;
      break;
    case "snapshot":
      room.room = msg.data.room;
      room.state = msg.data.state;
      room.queue = msg.data.queue;
      room.members = msg.data.members;
      syncMyRole();
      break;
    case "state":
      room.state = msg.state;
      break;
    case "queue_update":
      room.queue = msg.queue;
      break;
    case "members_update":
      room.members = msg.members;
      syncMyRole();
      break;
    case "system":
      addToast(msg.text, "system");
      break;
    case "error":
      if (msg.code === "room_not_found") {
        room.fatal = "not_found";
        socket?.close();
      } else {
        addToast(msg.message, "error");
      }
      break;
    default:
      break;
  }
}
