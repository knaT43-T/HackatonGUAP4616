<template>
  <div class="picker" @click.self="$emit('close')">
    <div class="picker__dialog" role="dialog" aria-label="Каталог треков">
      <header class="picker__head">
        <h2 class="picker__title">Каталог треков</h2>
        <button class="picker__close" type="button" title="Закрыть" @click="$emit('close')">
          ✕
        </button>
      </header>

      <form class="picker__upload" @submit.prevent="submitUpload">
        <label class="picker__file">
          <input
            ref="fileInput"
            type="file"
            accept="audio/*,.mp3,.wav,.ogg,.oga,.opus,.m4a,.aac,.flac,.webm,.aiff"
            @change="onFile"
          />
          <span>{{ file ? file.name : "Выбрать аудиофайл" }}</span>
        </label>
        <input
          v-model.trim="uploadTitle"
          class="picker__input"
          type="text"
          placeholder="Название"
          maxlength="120"
        />
        <input
          v-model.trim="uploadArtist"
          class="picker__input"
          type="text"
          placeholder="Исполнитель (необязательно)"
          maxlength="120"
        />
        <button class="picker__button" type="submit" :disabled="!file || uploading">
          {{ uploading ? "Загружаем…" : "Загрузить" }}
        </button>
      </form>
      <p class="picker__hint">
        До {{ MAX_MB }} МБ · mp3, wav, ogg, opus, m4a, aac, flac, webm, aiff
      </p>
      <p v-if="uploadError" class="picker__error">{{ uploadError }}</p>

      <p v-if="loading" class="picker__status">Загружаем каталог…</p>
      <p v-else-if="loadError" class="picker__error">{{ loadError }}</p>
      <p v-else-if="!tracks.length" class="picker__status">
        Каталог пуст — загрузи первый трек.
      </p>
      <ul v-else class="picker__list">
        <li v-for="track in tracks" :key="track.id" class="picker__item">
          <div class="picker__meta">
            <p class="picker__name" :title="track.title">{{ track.title }}</p>
            <p class="picker__sub">
              {{ track.artist || "Неизвестный исполнитель" }} · {{ formatBytes(track.size) }} ·
              {{ track.uploaded_by }}
            </p>
          </div>
          <button
            class="picker__button picker__button--ghost"
            type="button"
            :disabled="!isOnline || addingId === track.id"
            @click="add(track)"
          >
            {{ addingId === track.id ? "…" : "В очередь" }}
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";

import { addToQueue } from "../api/queue";
import { listTracks, uploadTrack } from "../api/tracks";
import { addToast, room } from "../state/room";
import { formatBytes } from "../utils/format";

defineEmits(["close"]);

const MAX_MB = 50;

const tracks = ref([]);
const loading = ref(true);
const loadError = ref("");

const file = ref(null);
const fileInput = ref(null);
const uploadTitle = ref("");
const uploadArtist = ref("");
const uploading = ref(false);
const uploadError = ref("");

const addingId = ref(null);
const isOnline = computed(() => room.status === "online");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    tracks.value = await listTracks();
  } catch (e) {
    loadError.value = e.message || "Не удалось загрузить каталог";
  } finally {
    loading.value = false;
  }
}

function onFile(event) {
  const picked = event.target.files?.[0] ?? null;
  file.value = picked;
  if (picked && !uploadTitle.value) {
    uploadTitle.value = picked.name.replace(/\.[^.]+$/, "");
  }
}

async function submitUpload() {
  if (!file.value || uploading.value) return;
  uploadError.value = "";
  if (file.value.size > MAX_MB * 1024 * 1024) {
    uploadError.value = `Файл больше ${MAX_MB} МБ — сервер его отклонит`;
    return;
  }
  uploading.value = true;
  try {
    await uploadTrack(file.value, {
      title: uploadTitle.value,
      artist: uploadArtist.value,
    });
    addToast("Трек загружен в каталог", "system");
    file.value = null;
    uploadTitle.value = "";
    uploadArtist.value = "";
    if (fileInput.value) fileInput.value.value = "";
    await load();
  } catch (e) {
    uploadError.value = e.message || "Не удалось загрузить файл";
  } finally {
    uploading.value = false;
  }
}

async function add(track) {
  const roomId = room.room?.id;
  if (!roomId || addingId.value) return;
  addingId.value = track.id;
  try {
    await addToQueue(roomId, track.id);
    addToast(`«${track.title}» в очереди`, "system");
  } catch (e) {
    addToast(e.message || "Не удалось добавить трек", "error");
  } finally {
    addingId.value = null;
  }
}

onMounted(load);
</script>

<style scoped>
.picker {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(26, 22, 51, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.picker__dialog {
  width: 100%;
  max-width: 560px;
  max-height: 84vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 48px rgba(26, 22, 51, 0.24);
}

.picker__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.picker__title {
  margin: 0;
  font-size: 18px;
  color: var(--text);
}

.picker__close {
  width: 30px;
  height: 30px;
  font-size: 14px;
  color: var(--text-muted);
  background: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
}

.picker__close:hover {
  color: var(--danger);
  border-color: var(--danger);
}

.picker__upload {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 6px;
}

.picker__file {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 14px;
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px dashed var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.picker__file:hover {
  border-color: var(--accent);
}

.picker__file input {
  display: none;
}

.picker__input {
  padding: 10px 14px;
  font-size: 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-input);
  color: var(--text);
  outline: none;
  min-width: 0;
}

.picker__input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

.picker__button {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.picker__button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.picker__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker__button--ghost {
  color: var(--accent);
  background: var(--accent-dim);
}

.picker__button--ghost:hover:not(:disabled) {
  background: var(--accent-dim);
  filter: brightness(0.95);
}

.picker__hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.picker__status {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--text-muted);
}

.picker__error {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--danger);
}

.picker__list {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.picker__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
}

.picker__meta {
  flex: 1;
  min-width: 0;
}

.picker__name {
  margin: 0 0 1px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.picker__sub {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
