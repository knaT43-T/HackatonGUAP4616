import { api } from "./client";

export function loginGuest(nickname) {
  return api("/api/auth/guest", {
    method: "POST",
    body: JSON.stringify({ nickname }),
  });
}

export function getMe() {
  return api("/api/auth/me");
}
