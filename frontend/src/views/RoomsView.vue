<template>
  <div class="rooms">
    <div class="rooms__inner">
      <h1 class="rooms__title">Привет, {{ auth.user?.nickname }}!</h1>
      <p class="rooms__subtitle">
        Создай новую комнату или присоединись по коду приглашения.
      </p>

      <div class="rooms__grid">
        <section class="rooms__card">
          <h2 class="rooms__card-title">Создать комнату</h2>
          <p class="rooms__card-text">
            Ты станешь хостом: сможешь управлять воспроизведением и очередью.
          </p>
          <form class="rooms__form" @submit.prevent="handleCreate">
            <input
              v-model.trim="roomName"
              class="rooms__input"
              type="text"
              placeholder="Например: Вечеринка"
              maxlength="60"
              :disabled="busy"
            />
            <button
              class="rooms__button"
              type="submit"
              :disabled="busy || !roomName"
            >
              Создать
            </button>
          </form>
        </section>

        <section class="rooms__card">
          <h2 class="rooms__card-title">Войти по коду</h2>
          <p class="rooms__card-text">
            Код из ссылки-приглашения — 8 символов. Регистр не важен.
          </p>
          <form class="rooms__form" @submit.prevent="handleJoin">
            <input
              v-model.trim="inviteCode"
              class="rooms__input rooms__input--code"
              type="text"
              placeholder="UXYZJ5HS"
              maxlength="8"
              autocomplete="off"
              spellcheck="false"
              :disabled="busy"
            />
            <button
              class="rooms__button"
              type="submit"
              :disabled="busy || inviteCode.length !== 8"
            >
              Войти
            </button>
          </form>
        </section>
      </div>

      <p v-if="error" class="rooms__error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import { createRoom, joinRoom } from "../api/rooms";
import { auth, signOut } from "../state/auth";

const router = useRouter();

const roomName = ref("");
const inviteCode = ref("");
const busy = ref(false);
const error = ref("");

async function handleCreate() {
  if (!roomName.value || busy.value) return;
  await run(() => createRoom(roomName.value));
}

async function handleJoin() {
  const code = inviteCode.value.trim().toUpperCase();
  if (!code || busy.value) return;
  await run(() => joinRoom(code), { notFoundText: "Комната с таким кодом не найдена" });
}

async function run(action, { notFoundText } = {}) {
  busy.value = true;
  error.value = "";
  try {
    const snapshot = await action();
    router.push({
      name: "room",
      params: { inviteCode: snapshot.room.invite_code },
    });
  } catch (e) {
    if (e.status === 401) {
      signOut();
      router.replace({ name: "home" });
      return;
    }
    error.value =
      e.status === 404 && notFoundText ? notFoundText : e.message;
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.rooms {
  min-height: calc(100vh - 128px);
  padding: 40px 16px;
}

.rooms__inner {
  max-width: 860px;
  margin: 0 auto;
}

.rooms__title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--text);
}

.rooms__subtitle {
  margin: 0 0 28px;
  color: var(--text-muted);
}

.rooms__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.rooms__card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(106, 88, 240, 0.06);
}

.rooms__card-title {
  margin: 0 0 6px;
  font-size: 17px;
  color: var(--text);
}

.rooms__card-text {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.rooms__form {
  display: flex;
  gap: 10px;
}

.rooms__input {
  flex: 1;
  min-width: 0;
  padding: 11px 14px;
  font-size: 15px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-input);
  color: var(--text);
  outline: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

.rooms__input--code {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 600;
}

.rooms__input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

.rooms__button {
  padding: 11px 18px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  white-space: nowrap;
  transition:
    background 0.15s,
    transform 0.1s;
}

.rooms__button:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
}

.rooms__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rooms__error {
  margin: 20px 0 0;
  font-size: 14px;
  color: var(--danger);
}
</style>
