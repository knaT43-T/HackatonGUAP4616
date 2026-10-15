# Frontend — «Слушаем вместе»

SPA на Vue 3 + Vite: комнаты, плеер с серверной синхронизацией, очередь и
каталог треков. Подробная документация (компоненты, правила синхронизации,
деплой) — [`front.md`](../front.md).

---

## Стек

| Слой | Технология |
|---|---|
| Сборщик | Vite 5 |
| UI | Vue 3 (Composition API, `<script setup>`) |
| Роутинг | vue-router 4 |
| HTTP | fetch (обёртка `api` с cookie и разбором ошибок) |
| Realtime | нативный WebSocket |
| Стили | чистый CSS, CSS-переменные |

---

## Запуск

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Бэкенд должен быть запущен на `http://localhost:8000` (см.
[`backend/README.md`](../backend/README.md)).

**Скрипты**

| Команда | Что делает |
|---|---|
| `npm run dev` | dev-сервер Vite на порту 5173 |
| `npm run build` | прод-сборка в `dist/` |
| `npm run preview` | локальный просмотр сборки (порт 4173) |

---

## Настройки

Все переменные необязательны: без `.env` используются адреса
`http://<хост страницы>:8000` и `ws://<хост страницы>:8000/ws`.
Для нестандартной конфигурации скопируй `.env.example` в `.env`:

```
VITE_API_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000/ws
```

Переменные `VITE_*` инлайнятся в бандл при сборке.

---

## Структура

```
src/
├── main.js               # точка входа
├── App.vue               # каркас: шапка, router-view, подвал
├── config.js             # API_URL / WS_URL / mediaUrl()
├── api/
│   ├── client.js         # fetch-обёртка: cookie, ошибки, FormData
│   ├── auth.js           # вход по нику, «кто я»
│   ├── rooms.js          # создание / вход / выход из комнаты
│   ├── tracks.js         # каталог + загрузка файла
│   └── queue.js          # добавление в очередь (удаление — по сокету)
├── state/
│   ├── auth.js           # сессия: ensureSession / signIn / signOut
│   └── room.js           # состояние комнаты + диспетчер WS-событий
├── ws/
│   ├── client.js         # сокет: join, ping-цикл, reconnect с backoff
│   ├── clock.js          # смещение часов по ping/pong (минимальный RTT)
│   └── position.js       # позиция из якоря (positionNowMs)
├── components/
│   ├── Player.vue        # <audio>, прогресс, управление, дрейф, автоплей
│   ├── QueueList.vue     # очередь; удаление — хост
│   ├── TrackPicker.vue   # модалка: каталог + загрузка файла
│   ├── Toasts.vue        # system / error уведомления
│   ├── AppHeader.vue     # шапка: навигация, выход
│   └── AppFooter.vue     # подвал
├── views/
│   ├── HomeView.vue      # вход по нику
│   ├── RoomsView.vue     # создать комнату / войти по коду
│   ├── RoomView.vue      # комната: плеер, очередь, приглашение, участники
│   └── NotFound.vue      # 404
├── utils/
│   └── format.js         # formatMs / formatBytes
└── styles/
    ├── index.css         # точка входа стилей
    └── base.css          # токены и база
```

---

## Как это работает (кратко)

- **Один диспетчер событий** — всё, что приходит по WebSocket, разбирается
  в `state/room.js` (один `switch` по типу события); компоненты читают стор
  и шлют команды через `sendCommand`.
- **Позиция не хранится**, а вычисляется из серверного якоря:
  `position_ms + (now + смещение − updated_at)` — см. `ws/position.js`.
- **Часы** — ping каждые 4 с; смещение оценивается по замеру с минимальным RTT
  (скользящее окно из 8 замеров) — см. `ws/clock.js`.
- **Дрейф звука** — каждые 2 с: расхождение > 2 с — жёсткий seek,
  300 мс–2 с — мягкая коррекция скоростью ±4 %, иначе скорость 1 (`Player.vue`).
- **Автоплей** — если браузер заблокировал звук, плеер показывает кнопку
  «Включить звук».
- **Уход из комнаты** — сначала закрывается сокет, затем REST `leave`:
  сервер разошлёт участникам `members_update` и передаст права хоста.

---

## Прод-сборка

```bash
npm run build    # → dist/
```

`dist/` — статика с SPA-fallback на `index.html` (любой хостинг: nginx,
Caddy, Netlify, Vercel). В репозитории лежит готовая заготовка `nginx.conf`:
SPA-fallback + проксирование `/api/`, `/media/` и `/ws` на бэкенд.
В `docker-compose.yml` сейчас поднимается dev-сервер Vite, поэтому nginx-конфиг
ждёт «настоящего» деплоя статикой.
