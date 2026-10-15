<template>
  <div class="home">
    <div class="home__card">
      <div class="home__logo">
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
          <path
            d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"
          />
        </svg>
        <h1>Слушаем вместе</h1>
      </div>

      <p class="home__subtitle">
        Создай комнату, позови друзей и слушайте музыку синхронно.
      </p>

      <form class="home__form" @submit.prevent="handleLogin">
        <label class="home__label" for="nickname">Как тебя зовут?</label>
        <input
          id="nickname"
          v-model.trim="nickname"
          class="home__input"
          type="text"
          placeholder="Вася"
          maxlength="32"
          autocomplete="off"
          autofocus
          :disabled="loading"
        />
        <button
          class="home__button"
          type="submit"
          :disabled="loading || !isValid"
        >
          {{ loading ? "Входим…" : "Войти" }}
        </button>
        <p v-if="error" class="home__error">{{ error }}</p>
      </form>

      <p class="home__hint">Регистрация не нужна. Ник — и ты в деле.</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ensureSession, signIn } from "../state/auth";

const route = useRoute();
const router = useRouter();

const nickname = ref("");
const loading = ref(false);
const error = ref("");

const isValid = computed(
  () => nickname.value.length >= 2 && nickname.value.length <= 32,
);

// Куда вернуть человека после входа (например, если сработал guard приватной страницы).
const redirectTo = computed(() =>
  typeof route.query.redirect === "string" ? route.query.redirect : "/rooms",
);

// Если сессия уже жива (cookie на месте) — сразу уводим в комнаты.
onMounted(async () => {
  if (await ensureSession()) {
    router.replace(redirectTo.value);
  }
});

async function handleLogin() {
  if (!isValid.value || loading.value) return;
  loading.value = true;
  error.value = "";
  try {
    await signIn(nickname.value);
    router.replace(redirectTo.value);
  } catch (e) {
    error.value = e.message || "Не удалось войти";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.home {
  min-height: calc(100vh - 128px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.home__card {
  max-width: 440px;
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px 32px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(106, 88, 240, 0.06);
}

.home__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--accent);
  margin-bottom: 12px;
}

.home__logo h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.home__subtitle {
  color: var(--text-muted);
  font-size: 15px;
  margin: 0 0 28px;
  line-height: 1.5;
}

.home__form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.home__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
}

.home__input {
  width: 100%;
  padding: 12px 14px;
  font-size: 15px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-input);
  color: var(--text);
  outline: none;
  box-sizing: border-box;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

.home__input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

.home__input:disabled {
  opacity: 0.6;
}

.home__button {
  margin-top: 6px;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition:
    background 0.15s,
    transform 0.1s;
}

.home__button:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
}

.home__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.home__error {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--danger);
}

.home__hint {
  margin: 24px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}
</style>
