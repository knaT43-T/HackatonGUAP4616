# Frontend «Слушаем вместе» — документация

Одностраничное приложение для совместного прослушивания музыки на React + Vite. Светлая тема, роутинг, работа с REST API и WebSocket. Комната живёт на сервере, клиент держит состояние и пересчитывает позицию сам.

---

## 1. Стек

| Слой | Технология |
|---|---|
| Сборщик | Vite 5 |
| UI | React 18 |
| Роутинг | react-router-dom 7 |
| HTTP | fetch (обёртка `api`) |
| Realtime | WebSocket (нативный) |
| Стили | чистый CSS, CSS-переменные |
| Состояние | hooks + context |
| Модули | ESM |

---

## 2. Быстрый старт

```bash
cd frontend
npm install
npm run dev
```

Открывается `http://localhost:5173`

**Переменные окружения**

`frontend/.env`:

```
VITE_API_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000/ws
```

`.env.example` — коммитится в репозиторий, содержит те же переменные.

**Скрипты**

| Команда | Что делает |
|---|---|
| `npm run dev` | Dev-сервер Vite, порт 5173 |
| `npm run build` | Prod-сборка в `dist/` |
| `npm run preview` | Просмотр `dist/` локально |

---

## 3. Структура проекта

```
frontend/
├── .env
├── .env.example
├── index.html
├── package.json
├── vite.config.js
├── public/
│   └── logo.svg
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── api/
    │   ├── index.js
    │   ├── client.js
    │   ├── auth.js
    │   ├── rooms.js
    │   ├── tracks.js
    │   └── queue.js
    ├── ws/
    │   ├── client.js
    │   ├── clock.js
    │   └── position.js
    ├── context/
    │   ├── AuthContext.jsx
    │   └── RoomContext.jsx
    ├── components/
    │   ├── Header.jsx
    │   ├── LoginForm.jsx
    │   ├── Player.jsx
    │   ├── QueueList.jsx
    │   ├── MembersList.jsx
    │   ├── InviteBox.jsx
    │   ├── TrackPicker.jsx
    │   ├── UploadTrack.jsx
    │   ├── Toasts.jsx
    │   └── NotFound.jsx
    ├── pages/
    │   ├── LoginPage.jsx
    │   ├── RoomsPage.jsx
    │   ├── RoomPage.jsx
    │   └── ErrorPage.jsx
    └── styles/
        ├── index.css
        ├── base.css
        ├── header.css
        ├── login.css
        ├── rooms.css
        ├── room.css
        ├── player.css
        ├── error.css
        └── animations.css
```

**Правила:**

- Компоненты — `PascalCase.jsx`, один компонент — один файл.
- API и утилиты — `camelCase.js`.
- Стили — `kebab-case.css`, подключаются через `index.css`.

---

## 4. Маршруты

| Путь | Компонент | Доступ | Что показывает |
|---|---|---|---|
| `/` | редирект | — | уводит на `/rooms` или `/login` |
| `/login` | `LoginPage` | публичный | Ввод ника |
| `/rooms` | `RoomsPage` | приватный | Создать/войти, каталог треков |
| `/room/:invite_code` | `RoomPage` | приватный | Плеер, очередь, участники |
| `/error` | `ErrorPage` | публичный | 4401, room_not_found, connection_lost |
| `*` | `NotFound` | публичный | 404 |

**Приватные маршруты**

Обёртка `PrivateRoute` пропускает дальше только тех, у кого есть валидная сессия. Сессия проверяется через `GET /api/auth/me`. Пока проверка идёт — показываем спиннер. Если ответил 401 — редирект на `/login`.

---

## 5. API

`src/api/client.js`

Единая обёртка над `fetch`. Задачи:

- приложить cookie (`credentials: 'include'`) — без этого бэкенд не узнает человека;
- выставить `Content-Type: application/json` для JSON-запросов;
- при `!res.ok` выбросить `ApiClientError` со статусом, текстом и кодом ошибки.

Экспорты: `api` — базовый вызов, `ApiClientError` — класс ошибки.

`src/api/auth.js`

| Функция | HTTP | Описание |
|---|---|---|
| `loginGuest(nickname)` | `POST /api/auth/guest` | Получает cookie `pid` |
| `getMe()` | `GET /api/auth/me` | Текущий участник |

`src/api/rooms.js`

| Функция | HTTP |
|---|---|
| `createRoom(name)` | `POST /api/rooms` |
| `joinRoom(inviteCode)` | `POST /api/rooms/join` |
| `getRoom(roomId)` | `GET /api/rooms/{room_id}` |
| `getSnapshot(roomId)` | `GET /api/rooms/{room_id}/snapshot` |
| `getMembers(roomId)` | `GET /api/rooms/{room_id}/members` |
| `leaveRoom(roomId)` | `POST /api/rooms/{room_id}/leave` |

`src/api/tracks.js`

| Функция | HTTP |
|---|---|
| `uploadTrack(file, title?, artist?)` | `POST /api/tracks/upload` (multipart) |
| `getTracks()` | `GET /api/tracks` |
| `getTrack(trackId)` | `GET /api/tracks/{track_id}` |

`src/api/queue.js`

| Функция | HTTP |
|---|---|
| `getQueue(roomId)` | `GET /api/rooms/{room_id}/queue` |
| `addToQueue(roomId, trackId)` | `POST /api/rooms/{room_id}/queue` |
| `removeFromQueue(roomId, itemId)` | `DELETE /api/rooms/{room_id}/queue/{item_id}` |

`src/api/index.js` — единая точка импорта: экспортирует клиент и все модули как пространства имён (`auth`, `rooms`, `tracks`, `queue`), чтобы в компонентах писать коротко.

---

## 6. Аутентификация

**Хранение**

Никаких токенов. Только cookie `pid`, выставленная бэкендом. Браузер прикладывает её сам ко всем запросам с `credentials: 'include'` и к WebSocket. Фронту не нужно ничего хранить и прикладывать вручную.

**Поток «гость → комнаты»**

1. Пользователь вводит ник в `LoginForm` (до 32 символов).
2. Вызывается `loginGuest(nickname)`.
3. Приходит ответ с `participant_id` и `nickname`, cookie ставится автоматически.
4. Редирект на `/rooms`.

**Проверка на входе**

При загрузке приложения — один раз `getMe()`:

- 200 — сохранить текущего участника, пустить дальше;
- 401 — считать гостем. Приватные страницы будут редиректить на `/login`.

**Logout**

Отдельного эндпоинта на бэкенде нет. Выход — очистка клиентского состояния и редирект на `/login`. Cookie останется, но UI считает пользователя гостем до следующего логина.

---

## 7. Компоненты

`Header.jsx`

Меняет содержимое по авторизации.

| Гость | Авторизованный |
|---|---|
| Войти | @nickname |
| Начать | Выйти |

`me` берётся из `AuthContext`.

`LoginForm.jsx`

| Проп | Тип | Описание |
|---|---|---|
| `onSuccess(me)` | function | Вызывается после успеха |

Поле — `nickname`. Валидация: непустой, до 32 символов.

`Player.jsx` — главный компонент синхронизации.

| Проп | Тип | Описание |
|---|---|---|
| `state` | object | Из `RoomContext` |
| `role` | string | `host` или `listener` |
| `send` | function | Отправка команд в сокет |

Содержит `<audio>`, прогресс-бар, кнопки `play/pause/seek/skip`. Позиция не хранится в стейте — считается на каждый рендер через `positionNow(state)`.

`QueueList.jsx`

| Проп | Тип |
|---|---|
| `queue` | array |
| `role` | string |
| `onAdd` | function |
| `onRemove` | function |

Кнопка удаления видна только `host`.

`MembersList.jsx`

| Проп | Тип |
|---|---|
| `members` | array |
| `meId` | string |

`InviteBox.jsx`

Показывает `invite_code`, копирует `location.origin + '/room/' + invite_code` в буфер обмена.

`TrackPicker.jsx`

Модалка с каталогом треков. По выбору вызывает `onPick(trackId)`.

`UploadTrack.jsx`

Форма загрузки файла. Проверяет размер (`<50 МБ`) и расширение до отправки, чтобы не гонять файл впустую и не получать 413.

`NotFound.jsx`

Показывает путь и кнопки «На главную» / «Войти».

---

## 8. Страницы

`LoginPage.jsx` — `/login`

Обёртка `LoginForm`. По успеху — переход на `/rooms`. Если `me` уже есть — сразу редирект на `/rooms`.

`RoomsPage.jsx` — `/rooms`

- Кнопка «Создать комнату» → создаёт комнату и уводит в неё.
- Поле «Код приглашения» (8 символов) → присоединяет к комнате.
- Каталог треков: список и загрузка новых.

`RoomPage.jsx` — `/room/:invite_code`

Основная страница. Слева — плеер и очередь, справа — участники и приглашение. Снизу — тосты `system` и `error`. При монтировании подключается WebSocket, отправляет `join`, ждёт `snapshot`.

`ErrorPage.jsx` — `/error`

Принимает причину через query (например, `room_not_found`) и показывает понятный текст и кнопку возврата.

---

## 9. Стили

**Переменные**

```
:root {
  --bg: #fbfbfe;            фон страниц
  --bg-elevated: #ffffff;   карточки, шапка
  --bg-input: #f3f4fa;      поля ввода
  --border: #e4e6ef;
  --border-focus: #6a58f0;
  --text: #1a1c25;
  --text-muted: #6d7285;
  --accent: #6a58f0;        акцент, кнопки
  --accent-hover: #5a48e0;
  --accent-dim: rgba(106, 88, 240, 0.12);
  --danger: #e5484d;        ошибки
  --success: #2fbf71;       успех, online
  --warning: #f5a623;
}
```

**Подключение**

`main.jsx` импортирует `styles/index.css`. Тот в свою очередь собирает все остальные через `@import`.

Порядок: `base.css` — первым (там `:root`), `animations.css` — последним. Остальные — по смыслу.

**Палитра**

| Токен | Значение | Где применяется |
|---|---|---|
| `--bg` | `#fbfbfe` | Фон страниц |
| `--bg-elevated` | `#ffffff` | Карточки, шапка |
| `--bg-input` | `#f3f4fa` | Поля ввода |
| `--accent` | `#6a58f0` | Акцент, кнопки |
| `--danger` | `#e5484d` | Ошибки |
| `--success` | `#2fbf71` | Успех, статус online |

Стиль — светлый, дружелюбный, 3–4 акцента, без мрачных тёмных пятен.

---

## 10. WebSocket

`src/ws/client.js`

Подключение: `VITE_WS_URL` или `ws://127.0.0.1:8000/ws`. Cookie `pid` браузер прикладывает сам.

**Порядок работы:**

1. Открыли сокет — отправляем `join` (с `room_id` или `invite_code`).
2. Получили `joined` — сохранили `role` и `participant_id`.
3. Получили `snapshot` — заменили `room`, `state`, `queue`, `members` целиком.
4. Дальше реагируем на события: `state`, `queue_update`, `members_update`, `system`, `error`.

**Команды клиента — всё через сокет.** REST для управления плеером не используется:

| Команда | Кто | Что делает |
|---|---|---|
| `play` | host | Запустить / продолжить |
| `pause` | host | Пауза |
| `seek` | host | Перемотка |
| `skip` | host | Следующий трек |
| `queue_remove` | host | Убрать из очереди |
| `track_loaded` | любой | Сообщить длительность |
| `ping` | любой | Мерка часов |
| `leave` | любой | Выйти из комнаты |

**Коды закрытия**

| Код | Что делать |
|---|---|
| `4401` | Сессии нет — очистить состояние, увести на `/login` |
| `4404` | Сокет вытеснен новой вкладкой — ничего не показывать |

**Диспетчер событий** — один `switch` по `msg.type` в `RoomContext`. Каждый кейс — маленькая функция. Не разбирать одно событие в разных местах приложения.

---

## 11. Синхронизация

`src/ws/clock.js`

Смещение часов меряется через `ping/pong`. Берётся кандидат с минимальным RTT — так меньше сказывается сетевая задержка.

- `ping` — сразу после `join`, затем каждые 3–5 секунд.
- После `visibilitychange` (возврат на вкладку) — `ping` немедленно.
- После reconnect — `ping` немедленно, старый `clockOffset` может быть неактуален.

`src/ws/position.js`

Позиция не хранится в стейте, а считается на каждый рендер:

```
position = is_playing
  ? position_ms + (now_server - updated_at)
  : position_ms
```

Где `now_server = Date.now() + clockOffset`.

`src/components/Player.jsx`

- Пришёл `state` с новым якорем — выставляем `audio.currentTime` из `positionNow(state)`.
- Если `state.is_playing` — включаем воспроизведение, иначе ставим на паузу.
- Серия `play/pause/seek` — каждое событие перезаписывает позицию. Следим за `state.version`, чтобы старые события не откатывали трек назад.
- Раз в 30–60 секунд сверяем реальную позицию `<audio>` с расчётной. Расхождение больше 200 мс — мягко подтягиваем. Иначе будет слышен «сдвиг».

**Частая ошибка:** выставлять позицию по `state.position_ms` без пересчёта. Между событием и его обработкой проходит время — трек уедет назад.

---

## 12. Длительность и автопереключение

Сервер не читает длительность из файла. Её сообщает клиент, у которого загрузился `<audio>`:

- по событию `loadedmetadata` отправляем `track_loaded` с `item_id` и `duration_ms`.

`item_id` — это id элемента **очереди**, не трека. Бери из `state.item_id`. Отправлять может кто угодно, достаточно один раз на трек.

**Без этого автопереключение не работает.** Сервер не знает, что трек кончился, и не перейдёт к следующему сам. Ручной `skip` работает всегда.

Отправлять повторно при каждой смене `state.item_id` — `<audio>` перезагружает новый источник, и `loadedmetadata` срабатывает заново.

---

## 13. Права в UI

| Действие | host | listener |
|---|:---:|:---:|
| play / pause / seek / skip | ✅ | ❌ |
| Убрать трек из очереди | ✅ | ❌ |
| Добавить трек в очередь | ✅ | ✅ |
| Слушать | ✅ | ✅ |

Правила:

- Кнопки `play/pause/seek/skip` и удаление из очереди видит только host.
- Для listener их лучше не показывать вовсе, а не дизейблить — интерфейс чище.
- Бэкенд всё равно проверит права и вернёт `forbidden`. Покажи тост — не молчи.
- Роль приходит в `joined` и меняется в `members_update`. Держи `role` в `RoomContext`, не пересчитывай вручную из списка участников.

---

## 14. Reconnect и уход хоста

**Reconnect**

- Сокет закрылся не по `4401` — переводим состояние в `reconnecting`.
- Переподключение с backoff: 1s, 2s, 4s, 8s, максимум 15s.
- После открытия — снова `join` и ждём `snapshot`.
- `snapshot` заменяет `room`, `state`, `queue`, `members` целиком.
- Сразу `ping` — обновить `clockOffset`.
- `4401` — не переподключаться, очистить состояние, на `/login`.
- `4404` — ничего не показывать: это refresh, старая вкладка вытеснена.

Во время reconnect плеер продолжает играть локально, UI приглушён. `<audio>` останавливать нельзя — иначе на каждой потере связи будет пауза.

**Ушёл хост.** Права переходят первому подключённому слушателю. Прилетает `members_update` с новой ролью и `system` с текстом «Управление передано: Петя». Покажи уведомление. Если права перешли тебе — обнови `role`, кнопки появятся.

**Хост вернулся.** Создатель комнаты (`creator_id`) снова становится host автоматически. Ничего делать не нужно — достаточно открыть ту же ссылку.

**Пустая комната.** Музыка на паузе, комната живёт `ROOM_IDLE_TTL_MIN` (30 минут), потом удаляется. При `join` в мёртвую комнату — `room_not_found`, редирект на `/error`.

---

## 15. Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| Failed to resolve import | Опечатка или файла нет | Проверить путь |
| X is not defined | Забыл импорт | Добавить `import X` |
| Invalid hook call | Разные версии React и роутера | Обновить react-router-dom |
| CORS policy | Бэкенд не разрешил origin | Добавить origin в `CORS_ORIGINS` |
| ERR_CONNECTION_REFUSED | Бэкенд не запущен | Запустить backend |
| Стили не применяются | `index.css` не импортирован | Проверить `main.jsx` |
| `VITE_API_URL undefined` | `.env` не в корне или Vite не перезапущен | `.env` в `frontend/`, перезапуск |
| 401 на приватном роуте | Cookie `pid` протухла или бэкенд перезапущен | Залогиниться заново |
| Позиция уезжает | Выставляем `currentTime` без пересчёта | Использовать `positionNow(state)` |
| Трек не переключается сам | Не отправлен `track_loaded` | Отправлять по `loadedmetadata` |

---

## 16. Сборка и деплой

**Production build**

```
cd frontend
npm run build
```

Результат — `frontend/dist/`.

**Локальный просмотр**

```
npm run preview
```

Открывается `http://localhost:4173`.

**Деплой**

`dist/` — статика. Кладётся на Nginx, Caddy, Vercel, Netlify или Cloudflare Pages.

Для SPA-роутинга нужен fallback на `index.html`. У каждого хостинга свой способ:

- Nginx — `try_files $uri $uri/ /index.html`;
- Netlify — файл `_redirects` со строкой `/* /index.html 200`;
- Vercel — `vercel.json` с rewrite всех путей на `index.html`.

**Production .env**

```
VITE_API_URL=https://api.listen-together.example.com
VITE_WS_URL=wss://api.listen-together.example.com/ws
```

Переменные с префиксом `VITE_` инлайнятся в бандл при сборке.

**WebSocket за прокси.** Nginx должен проксировать заголовки `Upgrade` и `Connection`, иначе WebSocket не поднимется. Без этого плеер будет работать, а синхронизация — нет.

---

## 17. Что дальше

Фронт покрывает MVP: логин по нику, создание и вход в комнату, плеер с синхронизацией, очередь, участники, приглашение, обработка ошибок.

Следующие шаги:

- Чат комнаты — текстовые сообщения вместе с системными.
- Реакции на треки — эмодзи поверх плеера.
- Публичные комнаты — список активных.
- Мобильная адаптация — плеер внизу, очередь в шторке.
- Тема light/dark — переключатель и второй набор переменных.
- PWA — манифест, service worker, оффлайн-заглушка.
- Уведомления — Web Notifications при смене трека.
- Эквалайзер и визуализация — Web Audio API.

---

## 18. Связанные документы

- `api.md` — спецификация эндпоинтов бэкенда (REST + WebSocket).
- `README.md` — общее описание проекта и инструкция запуска.