// Позиция воспроизведения не хранится в состоянии, а вычисляется из якоря:
// «в момент updated_at позиция была position_ms». Дальше клиент доезжает сам.
//
//   position = is_playing ? position_ms + (now_server - updated_at) : position_ms
//
// now_server = Date.now() + смещение часов (см. clock.js). API.md §7.

export function positionNowMs(state, offsetMs = 0, nowMs = Date.now()) {
  if (!state) return 0;
  const anchor = Math.max(0, state.position_ms || 0);
  if (!state.is_playing) return anchor;
  return Math.max(0, anchor + (nowMs + offsetMs - state.updated_at));
}

export function clampPositionMs(positionMs, durationMs) {
  if (!durationMs || durationMs <= 0) return positionMs;
  return Math.min(positionMs, durationMs);
}
