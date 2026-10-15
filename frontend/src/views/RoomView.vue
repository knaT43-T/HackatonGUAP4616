<template>
  <div class="room">
    <Toasts />

    <div class="room__inner">
      <div v-if="roomStore.fatal === 'not_found'" class="room__screen">
        <h1 class="room__screen-title">Комната не найдена</h1>
        <p class="room__screen-text">
          Проверь код в ссылке — возможно, комната уже закрылась.
        </p>
        <RouterLink class="room__btn room__btn--primary" :to="{ name: 'rooms' }">
          К комнатам
        </RouterLink>
      </div>

      <div v-else-if="roomStore.status === 'superseded'" class="room__screen">
        <h1 class="room__screen-title">Комната открыта в другой вкладке</h1>
        <p class="room__screen-text">
          Это соединение вытеснено новым. Продолжай там — здесь мы больше не мешаем.
        </p>
        <RouterLink class="room__btn" :to="{ name: 'rooms' }">К комнатам</RouterLink>
      </div>

      <div v-else-if="!roomStore.room" class="room__screen">
        <p class="room__status">{{ loadingText }}</p>
        <RouterLink v-if="showEscape" class="room__btn" :to="{ name: 'rooms' }">
          ← К комнатам
        </RouterLink>
      </div>

      <template v-else>
        <header class="room__header">
          <div>
            <h1 class="room__title">{{ roomStore.room.name }}</h1>
            <p class="room__subtitle">
              создана {{ createdText }}
              <span class="room__conn" :class="`room__conn--${connKind}`">
                {{ connLabel }}
              </span>
            </p>
          </div>
          <div class="room__header-actions">
            <button class="room__btn room__btn--danger" type="button" @click="handleLeave">
              Выйти из комнаты
            </button>
          </div>
        </header>

        <div class="room__layout">
          <main class="room__main">
            <Player />
            <QueueList @add="pickerOpen = true" />
          </main>

          <aside class="room__side">
            <section class="room__card">
              <h2 class="room__card-title">Приглашение</h2>
              <p class="room__card-text">
                Отправь друзьям ссылку — они попадут сразу в эту комнату.
              </p>
              <div class="room__invite">
                <code class="room__code">{{ roomStore.room.invite_code }}</code>
                <button class="room__btn" type="button" @click="copyInvite">
                  {{ copied ? "Скопировано!" : "Скопировать ссылку" }}
                </button>
              </div>
            </section>

            <section class="room__card">
              <h2 class="room__card-title">
                Участники <span class="room__count">{{ roomStore.members.length }}</span>
              </h2>
              <ul class="room__members">
                <li
                  v-for="member in roomStore.members"
                  :key="member.id"
                  class="room__member"
                >
                  <span
                    class="room__dot"
                    :class="{ 'room__dot--online': member.connected }"
                    :title="member.connected ? 'в сети' : 'не в сети'"
                  ></span>
                  <span class="room__member-name">{{ member.nickname }}</span>
                  <span v-if="member.role === 'host'" class="room__badge">хост</span>
                  <span
                    v-if="member.id === roomStore.meId"
                    class="room__badge room__badge--me"
                  >
                    это ты
                  </span>
                </li>
              </ul>
            </section>
          </aside>
        </div>
      </template>
    </div>

    <TrackPicker v-if="pickerOpen" @close="pickerOpen = false" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { leaveRoom } from "../api/rooms";
import Player from "../components/Player.vue";
import QueueList from "../components/QueueList.vue";
import Toasts from "../components/Toasts.vue";
import TrackPicker from "../components/TrackPicker.vue";
import { signOut } from "../state/auth";
import { connectRoom, disconnectRoom, room as roomStore } from "../state/room";

const props = defineProps({
  inviteCode: { type: String, required: true },
});

const router = useRouter();

const copied = ref(false);
const pickerOpen = ref(false);

const createdText = computed(() =>
  roomStore.room
    ? new Date(roomStore.room.created_at).toLocaleString("ru-RU")
    : "",
);

const inviteLink = computed(() =>
  roomStore.room ? `${location.origin}/room/${roomStore.room.invite_code}` : "",
);

const connKind = computed(() => {
  if (roomStore.status === "online") return "online";
  if (roomStore.status === "connecting" || roomStore.status === "reconnecting") {
    return "pending";
  }
  return "closed";
});

const connLabel = computed(
  () =>
    ({
      online: "на связи",
      pending: "переподключаемся…",
      closed: "не в сети",
    })[connKind.value],
);

const loadingText = computed(() => {
  switch (roomStore.status) {
    case "unauthorized":
      return "Требуется вход — возвращаем на главную…";
    case "reconnecting":
      return "Бэкенд недоступен, восстанавливаем соединение…";
    default:
      return "Заходим в комнату…";
  }
});

const showEscape = computed(() => roomStore.status !== "connecting");

async function copyInvite() {
  try {
    await navigator.clipboard.writeText(inviteLink.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    // Clipboard API может быть недоступен (http, старый браузер) — молча ничего.
  }
}

async function handleLeave() {
  // Сначала рвём сокет, потом снимаем участие по REST: сервер разошлёт
  // members_update остальным (в т.ч. передаст хоста, если это были мы).
  const roomId = roomStore.room?.id;
  disconnectRoom();
  if (roomId) {
    try {
      await leaveRoom(roomId);
    } catch {
      // Если уже не участник — не важно, всё равно уходим.
    }
  }
  router.push({ name: "rooms" });
}

// Сессия могла умереть, пока мы были в комнате: сервер закроет сокет кодом 4401.
watch(
  () => roomStore.status,
  (status) => {
    if (status === "unauthorized") {
      signOut();
      router.replace({ name: "home" });
    }
  },
);

onMounted(() => connectRoom(props.inviteCode));
onBeforeUnmount(() => disconnectRoom());
</script>

<style scoped>
.room {
  min-height: calc(100vh - 128px);
  padding: 40px 16px;
}

.room__inner {
  max-width: 1000px;
  margin: 0 auto;
}

.room__status {
  margin: 0 0 18px;
  color: var(--text-muted);
}

.room__screen {
  text-align: center;
  padding: 60px 0;
}

.room__screen-title {
  font-size: 24px;
  color: var(--text);
  margin: 0 0 10px;
}

.room__screen-text {
  color: var(--text-muted);
  margin: 0 0 24px;
}

.room__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.room__title {
  margin: 0 0 4px;
  font-size: 26px;
  color: var(--text);
}

.room__subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.room__conn {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 10px;
  font-size: 12px;
  border-radius: 999px;
}

.room__conn--online {
  background: rgba(47, 191, 113, 0.14);
  color: var(--success);
}

.room__conn--pending {
  background: var(--accent-dim);
  color: var(--accent);
}

.room__conn--closed {
  background: var(--bg-input);
  color: var(--text-muted);
}

.room__header-actions {
  display: flex;
  gap: 10px;
}

.room__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 880px) {
  .room__layout {
    grid-template-columns: 1fr;
  }
}

.room__main,
.room__side {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.room__card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(106, 88, 240, 0.06);
}

.room__card-title {
  margin: 0 0 10px;
  font-size: 17px;
  color: var(--text);
}

.room__count {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 8px;
  font-size: 12px;
  border-radius: 999px;
  background: var(--accent-dim);
  color: var(--accent);
  vertical-align: 2px;
}

.room__card-text {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.room__invite {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.room__code {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.12em;
  padding: 8px 14px;
  border-radius: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--text);
}

.room__members {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.room__member {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.room__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  flex: none;
}

.room__dot--online {
  background: var(--success);
}

.room__member-name {
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room__badge {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-dim);
  color: var(--accent);
}

.room__badge--me {
  background: var(--bg-input);
  color: var(--text-muted);
}

.room__btn {
  padding: 9px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  text-decoration: none;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.room__btn:hover {
  border-color: var(--border-focus);
}

.room__btn--primary {
  color: #fff;
  background: var(--accent);
  border-color: var(--accent);
}

.room__btn--primary:hover {
  background: var(--accent-hover);
}

.room__btn--danger {
  color: var(--danger);
}
</style>
