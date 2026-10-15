<template>
  <section class="player">
    <div v-if="!hasItem" class="player__empty">
      <div class="player__empty-icon">♪</div>
      <p class="player__empty-title">Сейчас ничего не играет</p>
      <p class="player__empty-hint">
        {{
          isHost
            ? "Добавь трек в очередь и нажми «Слушать»."
            : "Добавь трек в очередь — хост включит воспроизведение."
        }}
      </p>
      <button
        v-if="isHost"
        class="player__btn player__btn--play player__empty-btn"
        type="button"
        :disabled="!isOnline"
        @click="togglePlay"
      >
        ▶ Слушать
      </button>
    </div>

    <template v-else>
      <div class="player__now">
        <div class="player__cover" :class="{ 'player__cover--playing': isPlaying }">
          <span>♪</span>
        </div>
        <div class="player__meta">
          <p class="player__title" :title="trackTitle">{{ trackTitle }}</p>
          <p class="player__artist">{{ trackArtist }}</p>
        </div>
        <span v-if="currentItem?.added_by_name" class="player__by">
          добавил {{ currentItem.added_by_name }}
        </span>
      </div>

      <div class="player__progress">
        <input
          v-if="isHost"
          class="player__seek"
          type="range"
          min="0"
          :max="Math.max(durationMs, 1)"
          step="500"
          :value="displayMs"
          :disabled="!isOnline"
          aria-label="Перемотка"
          @input="onDrag"
          @change="onSeek"
          @blur="dragMs = null"
        />
        <div v-else class="player__bar">
          <div class="player__bar-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="player__times">
          <span>{{ formatMs(displayMs) }}</span>
          <span>{{ durationMs > 0 ? formatMs(durationMs) : "–:––" }}</span>
        </div>
      </div>

      <div class="player__controls">
        <template v-if="isHost">
          <button
            class="player__btn player__btn--play"
            type="button"
            :disabled="!isOnline"
            @click="togglePlay"
          >
            {{ isPlaying ? "⏸ Пауза" : "▶ Слушать" }}
          </button>
          <button
            class="player__btn"
            type="button"
            :disabled="!isOnline"
            title="Следующий трек"
            @click="skip"
          >
            ⏭ Дальше
          </button>
        </template>
        <span v-else class="player__lock" title="Воспроизведением управляет хост комнаты">
          🎧 Управляет хост
        </span>

        <div class="player__volume">
          <button
            class="player__icon-btn"
            type="button"
            :title="muted || volume === 0 ? 'Включить звук' : 'Выключить звук'"
            @click="toggleMuted"
          >
            {{ muted || volume === 0 ? "🔇" : "🔊" }}
          </button>
          <input
            v-model.number="volume"
            class="player__volume-range"
            type="range"
            min="0"
            max="1"
            step="0.02"
            aria-label="Громкость"
          />
        </div>
      </div>

      <div v-if="autoplayBlocked" class="player__blocked">
        <p class="player__blocked-text">Браузер заблокировал автозапуск звука</p>
        <button class="player__btn player__btn--play" type="button" @click="enableSound">
          🔊 Включить звук
        </button>
      </div>
    </template>

    <audio
      ref="audioEl"
      preload="auto"
      @loadedmetadata="onLoadedMetadata"
      @ended="onEnded"
    ></audio>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { mediaUrl } from "../config";
import { room, sendCommand, serverOffsetMs } from "../state/room";
import { formatMs } from "../utils/format";
import { clampPositionMs, positionNowMs } from "../ws/position";

const audioEl = ref(null);

const hasItem = computed(() => Boolean(room.state?.item_id && room.state?.track));
const isHost = computed(() => room.role === "host");
const isOnline = computed(() => room.status === "online");
const isPlaying = computed(() => Boolean(room.state?.is_playing));
const trackTitle = computed(() => room.state?.track?.title || "Без названия");
const trackArtist = computed(
  () => room.state?.track?.artist || "Неизвестный исполнитель",
);
const currentItem = computed(
  () => room.queue.find((item) => item.id === room.state?.item_id) ?? null,
);

const localDurationMs = ref(0);
const durationMs = computed(
  () => room.state?.duration_ms || localDurationMs.value || 0,
);

const tick = ref(0); // кадровый счётчик: заставляет пересчитывать позицию
const dragMs = ref(null);
const autoplayBlocked = ref(false);

// Позиция считается из якоря на каждый кадр, а не хранится (front.md §11).
const progressMs = computed(() => {
  void tick.value;
  const state = room.state;
  if (!state) return 0;
  return clampPositionMs(positionNowMs(state, serverOffsetMs()), durationMs.value);
});

const displayMs = computed(() => dragMs.value ?? progressMs.value);
const progressPercent = computed(() => {
  const total = durationMs.value;
  if (!total) return 0;
  return Math.min(100, Math.max(0, (displayMs.value / total) * 100));
});

// --- Громкость: локальная настройка, у каждого своя ---
const volume = ref(loadVolume());
const muted = ref(false);

function loadVolume() {
  try {
    const stored = Number(localStorage.getItem("lt-volume"));
    if (Number.isFinite(stored) && stored >= 0 && stored <= 1) return stored;
  } catch {
    // localStorage может быть недоступен (приватный режим)
  }
  return 1;
}

watch(volume, (value) => {
  try {
    localStorage.setItem("lt-volume", String(value));
  } catch {
    // не критично
  }
  applyVolume();
});
watch(muted, applyVolume);

function applyVolume() {
  const el = audioEl.value;
  if (el) el.volume = muted.value ? 0 : volume.value;
}

// --- Кадровый пересчёт позиции для UI ---
let rafId = null;
let driftTimer = null;

function frame() {
  tick.value += 1;
  rafId = requestAnimationFrame(frame);
}

function startFrames() {
  if (rafId === null) rafId = requestAnimationFrame(frame);
}

function stopFrames() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
}

watch(isPlaying, (playing) => {
  if (playing) startFrames();
  else stopFrames();
});

// --- Синхронизация <audio> с серверным якорем ---
let sentLoadedFor = null;

function targetPositionMs() {
  const state = room.state;
  if (!state) return 0;
  return clampPositionMs(
    positionNowMs(state, serverOffsetMs()),
    durationMs.value || null,
  );
}

function seekAudio(targetMs, thresholdMs = 150) {
  const el = audioEl.value;
  if (!el || !Number.isFinite(el.duration) || el.duration <= 0) return;
  if (Math.abs(el.currentTime * 1000 - targetMs) > thresholdMs) {
    el.currentTime = Math.max(0, targetMs / 1000);
  }
}

async function applyPlayback() {
  const el = audioEl.value;
  const state = room.state;
  if (!el || !state?.item_id) return;
  if (state.is_playing) {
    try {
      await el.play();
      autoplayBlocked.value = false;
    } catch {
      // Браузер не даёт играть без жеста пользователя — покажем кнопку.
      autoplayBlocked.value = true;
    }
  } else {
    el.pause();
  }
}

function loadItem(itemId, url) {
  const el = audioEl.value;
  el.dataset.itemId = itemId;
  sentLoadedFor = null;
  localDurationMs.value = 0;
  el.playbackRate = 1;
  el.src = url;
  el.load();
}

function applyState() {
  const el = audioEl.value;
  const state = room.state;
  if (!el) return;

  if (!state?.item_id || !state.track) {
    el.pause();
    delete el.dataset.itemId;
    el.removeAttribute("src");
    el.load();
    localDurationMs.value = 0;
    return;
  }

  if (el.dataset.itemId !== state.item_id) {
    // Новый трек: грузим источник, сик и play сделает loadedmetadata.
    loadItem(state.item_id, mediaUrl(state.track.url));
    return;
  }

  if (el.readyState >= 1) {
    seekAudio(targetPositionMs());
    applyPlayback();
  }
}

watch(() => room.state, applyState);

function onLoadedMetadata() {
  const el = audioEl.value;
  const state = room.state;
  if (!el || !state?.item_id) return;

  localDurationMs.value = Number.isFinite(el.duration)
    ? Math.round(el.duration * 1000)
    : 0;

  // Сообщаем серверу длительность: без этого не работает автопереход (API.md §8).
  if (localDurationMs.value > 0 && sentLoadedFor !== state.item_id) {
    sentLoadedFor = state.item_id;
    sendCommand("track_loaded", {
      item_id: state.item_id,
      duration_ms: localDurationMs.value,
    });
  }

  seekAudio(targetPositionMs(), 0);
  applyPlayback();
}

// --- Периодическая сверка дрейфа (front.md §11) ---
function driftCheck() {
  const el = audioEl.value;
  const state = room.state;
  if (!el || !state) return;
  if (!state.is_playing || !state.item_id || dragMs.value !== null) {
    if (el.playbackRate !== 1) el.playbackRate = 1;
    return;
  }
  const target = targetPositionMs();
  const drift = el.currentTime * 1000 - target;
  const abs = Math.abs(drift);
  if (abs > 2000) {
    el.currentTime = Math.max(0, target / 1000); // грубо догоняем
    el.playbackRate = 1;
  } else if (abs > 300) {
    // Мягко подтягиваем скоростью — без слышимых скачков.
    el.playbackRate = drift > 0 ? 0.96 : 1.04;
  } else {
    el.playbackRate = 1;
  }
}

function onVisibility() {
  if (document.visibilityState === "visible" && room.state?.is_playing) {
    seekAudio(targetPositionMs());
    applyPlayback();
  }
}

// --- Управление (только host) ---
function togglePlay() {
  sendCommand(isPlaying.value ? "pause" : "play");
}

function skip() {
  sendCommand("skip");
}

function onDrag(event) {
  dragMs.value = Number(event.target.value);
}

function onSeek() {
  const value = dragMs.value;
  dragMs.value = null;
  if (value !== null) {
    sendCommand("seek", { position_ms: Math.max(0, Math.round(value)) });
  }
}

function onEnded() {
  // Ничего: автопереходом занимается сервер (после track_loaded).
}

function enableSound() {
  seekAudio(targetPositionMs(), 0);
  applyPlayback();
}

function toggleMuted() {
  muted.value = !muted.value;
}

onMounted(() => {
  applyVolume();
  applyState();
  if (isPlaying.value) startFrames();
  driftTimer = setInterval(driftCheck, 2000);
  document.addEventListener("visibilitychange", onVisibility);
});

onBeforeUnmount(() => {
  stopFrames();
  if (driftTimer) clearInterval(driftTimer);
  document.removeEventListener("visibilitychange", onVisibility);
});
</script>

<style scoped>
.player {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(106, 88, 240, 0.06);
}

.player__empty {
  text-align: center;
  padding: 28px 12px;
}

.player__empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: var(--accent);
  background: var(--accent-dim);
  border-radius: 50%;
}

.player__empty-title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
}

.player__empty-hint {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
}

.player__empty-btn {
  margin-top: 18px;
}

.player__now {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.player__cover {
  width: 56px;
  height: 56px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: var(--accent);
  background: var(--accent-dim);
  border-radius: 12px;
}

.player__cover--playing {
  animation: player-pulse 1.6s ease-in-out infinite;
}

@keyframes player-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.06);
  }
}

.player__meta {
  min-width: 0;
  flex: 1;
}

.player__title {
  margin: 0 0 2px;
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player__artist {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.player__by {
  flex: none;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 10px;
}

.player__progress {
  margin-bottom: 16px;
}

.player__seek {
  width: 100%;
  accent-color: var(--accent);
  cursor: pointer;
}

.player__seek:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.player__bar {
  height: 6px;
  border-radius: 3px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  overflow: hidden;
}

.player__bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
}

.player__times {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}

.player__controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.player__btn {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.player__btn:hover:not(:disabled) {
  border-color: var(--border-focus);
}

.player__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.player__btn--play {
  color: #fff;
  background: var(--accent);
  border-color: var(--accent);
  min-width: 128px;
}

.player__btn--play:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.player__lock {
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 9px 14px;
}

.player__volume {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.player__icon-btn {
  font-size: 16px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}

.player__volume-range {
  width: 90px;
  accent-color: var(--accent);
  cursor: pointer;
}

.player__blocked {
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px dashed var(--accent);
  border-radius: 12px;
  background: var(--accent-dim);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.player__blocked-text {
  margin: 0;
  font-size: 13px;
  color: var(--text);
}
</style>
