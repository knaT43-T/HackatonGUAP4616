<template>
  <section class="queue">
    <header class="queue__head">
      <h2 class="queue__title">
        Очередь <span class="queue__count">{{ items.length }}</span>
      </h2>
      <button
        class="queue__add"
        type="button"
        :disabled="!isOnline"
        @click="emit('add')"
      >
        + Добавить трек
      </button>
    </header>

    <p v-if="!items.length" class="queue__empty">
      Пока пусто. Добавь первый трек ✨
    </p>

    <ul v-else class="queue__list">
      <li
        v-for="item in items"
        :key="item.id"
        class="queue__item"
        :class="{ 'queue__item--current': item.id === currentItemId }"
      >
        <span class="queue__mark">{{ item.id === currentItemId ? "▶" : item.position + 1 }}</span>
        <div class="queue__meta">
          <p class="queue__name" :title="item.track.title">{{ item.track.title }}</p>
          <p class="queue__sub">
            {{ item.track.artist || "Неизвестный исполнитель" }} · {{ item.added_by_name }}
          </p>
        </div>
        <span v-if="item.duration_ms" class="queue__duration">
          {{ formatMs(item.duration_ms) }}
        </span>
        <button
          v-if="isHost"
          class="queue__remove"
          type="button"
          :disabled="item.id === currentItemId"
          :title="
            item.id === currentItemId
              ? 'Играющий трек нельзя убрать — используй «Дальше»'
              : 'Убрать из очереди'
          "
          @click="remove(item)"
        >
          ✕
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from "vue";

import { room, sendCommand } from "../state/room";
import { formatMs } from "../utils/format";

const emit = defineEmits(["add"]);

const items = computed(() => room.queue);
const currentItemId = computed(() => room.state?.item_id ?? null);
const isHost = computed(() => room.role === "host");
const isOnline = computed(() => room.status === "online");

function remove(item) {
  sendCommand("queue_remove", { item_id: item.id });
}
</script>

<style scoped>
.queue {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(106, 88, 240, 0.06);
}

.queue__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.queue__title {
  margin: 0;
  font-size: 17px;
  color: var(--text);
}

.queue__count {
  display: inline-block;
  margin-left: 4px;
  padding: 1px 8px;
  font-size: 12px;
  border-radius: 999px;
  background: var(--accent-dim);
  color: var(--accent);
  vertical-align: 2px;
}

.queue__add {
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-dim);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: filter 0.15s;
}

.queue__add:hover:not(:disabled) {
  filter: brightness(0.96);
}

.queue__add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.queue__empty {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
}

.queue__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.queue__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid transparent;
}

.queue__item--current {
  background: var(--accent-dim);
  border-color: var(--accent);
}

.queue__mark {
  flex: none;
  width: 22px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.queue__item--current .queue__mark {
  color: var(--accent);
}

.queue__meta {
  flex: 1;
  min-width: 0;
}

.queue__name {
  margin: 0 0 1px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue__sub {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue__duration {
  flex: none;
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.queue__remove {
  flex: none;
  width: 28px;
  height: 28px;
  font-size: 13px;
  color: var(--text-muted);
  background: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}

.queue__remove:hover:not(:disabled) {
  color: var(--danger);
  border-color: var(--danger);
}

.queue__remove:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
