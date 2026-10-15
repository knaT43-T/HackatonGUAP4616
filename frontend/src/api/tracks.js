import { api } from "./client";

export function listTracks() {
  return api("/api/tracks").then((data) => data.tracks);
}

export function uploadTrack(file, { title, artist } = {}) {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  if (artist) form.append("artist", artist);
  return api("/api/tracks/upload", { method: "POST", body: form });
}
