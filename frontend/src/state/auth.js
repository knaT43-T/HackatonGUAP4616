// Состояние сессии. Токенов нет: бэкенд узнаёт человека по cookie "pid",
// которую браузер прикладывает сам (credentials: "include" в client.js).
import { reactive } from "vue";

import { getMe, loginGuest } from "../api/auth";

export const auth = reactive({
  user: null, // { participant_id, nickname } или null
  ready: false, // true — сессия уже проверена через /api/auth/me
});

let sessionCheck = null;

// Проверяет сессию один раз и кэширует результат. Возвращает пользователя или null.
export async function ensureSession() {
  if (auth.ready) return auth.user;
  if (!sessionCheck) {
    sessionCheck = getMe()
      .then((me) => {
        auth.user = me;
      })
      .catch(() => {
        auth.user = null;
      })
      .finally(() => {
        auth.ready = true;
        sessionCheck = null;
      });
  }
  await sessionCheck;
  return auth.user;
}

export async function signIn(nickname) {
  auth.user = await loginGuest(nickname);
  auth.ready = true;
  return auth.user;
}

// Отдельного эндпоинта logout на бэкенде нет: очищаем состояние на клиенте.
// Cookie остаётся до протухания — после перезагрузки страницы человек снова узнаётся.
export function signOut() {
  auth.user = null;
  auth.ready = true;
}
