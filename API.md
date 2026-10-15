# API — «Слушаем вместе»

Бэкенд совместного прослушивания музыки. Комната живёт на сервере, все клиенты
получают одинаковое состояние воспроизведения.

- REST — вход, комнаты, каталог треков, очередь.
- WebSocket — всё живое: play/pause/seek, смена трека, очередь, участники.

Интерактивная схема OpenAPI доступна на `http://127.0.0.1:8000/docs`.

---

## 1. Запуск сервера

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

Сервер: `http://127.0.0.1:8000`. Настройки — в `backend/.env`
(образец — `backend/.env.example`; все значения имеют дефолты).

**CORS.** Фронтенд на `localhost:5173` или `localhost:3000` работает сразу.
Если фронт на другом адресе — добавь origin в `CORS_ORIGINS` в `.env` и перезапусти.
Список в `.env` пишется как JSON-массив:

```
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

`allow_credentials=True` несовместим с `"*"`, поэтому origin'ы перечисляются явно.

---

## 2. Идентификация: cookie, а не токен

Учётных записей нет. Человек один раз вводит ник и получает cookie `pid`.

```bash
curl -i -X POST http://127.0.0.1:8000/api/auth/guest \
  -H "Content-Type: application/json" \
  -d '{"nickname":"Вася"}'
```

Ответ `200`:

```json
{ "participant_id": "2d327c90f7d4bfb1", "nickname": "Вася" }
```

Заголовок `Set-Cookie: pid=2d327c90f7d4bfb1; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`.

Дальше cookie ходит **сама** — и в REST, и в WebSocket. Фронтенду не нужно ни
хранить, ни прикладывать токен.

**Важно для fetch:** без `credentials` cookie не полетит.

```js
const res = await fetch('http://127.0.0.1:8000/api/auth/guest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ nickname: 'Вася' }),
});
```

Что даёт cookie:

- два человека с одинаковым ником остаются разными людьми (`participant_id` разный);
- после перезагрузки страницы ты тот же участник, а не новичок в списке;
- перезагрузил вкладку — вернулся хост, а не потерял права создателя.

`pid` держится в памяти сервера вместе с комнатами: перезапустил бэкенд — все
комнаты и сессии пропали. Каталог треков при этом сохраняется (лежит в файле).

---

## 3. Объекты в ответах

**Комната**

```json
{ "id": "7c1f...", "name": "Вечеринка", "invite_code": "UXYZJ5HS",
  "creator_id": "2d32...", "host_id": "2d32...", "created_at": 1791922519344 }
```

`invite_code` — то, что стоит в ссылке-приглашении: `/room/UXYZJ5HS`.
`creator_id` — кто создал комнату (он забирает права хоста, если вернётся),
`host_id` — кто управляет прямо сейчас.

**Состояние воспроизведения**

```json
{ "room_id": "7c1f...", "item_id": "b91a...", "track_id": "a1b2c3d4",
  "track": { "...": "метаданные трека" },
  "is_playing": true, "position_ms": 3000, "updated_at": 1791922515344,
  "duration_ms": 6000, "version": 7, "host_id": "2d32..." }
```

`position_ms` + `updated_at` — якорь: «на позиции 3000 мс мы были в момент
`updated_at`». Как считать текущую позицию — раздел 7.

**Трек**

```json
{ "id": "a1b2c3d4", "title": "In The End", "artist": "Linkin Park",
  "filename": "a1b2c3d4.mp3", "original_name": "in the end.mp3",
  "mime": "audio/mpeg", "size": 3412098, "uploaded_by": "Вася",
  "created_at": 1791922519344, "url": "/media/a1b2c3d4.mp3" }
```

`url` — путь от бэкенда (например, `/media/a1b2c3d4.mp3`), отдельный хостинг не
нужен. Путь **относительный**: клиент склеивает его с базовым адресом API
(`API_URL + track.url`). Если фронт и бэкенд стоят за одним прокси (см.
`frontend/nginx.conf`), путь можно использовать как есть.

**Элемент очереди**

```json
{ "id": "b91a...", "track_id": "a1b2c3d4", "track": { "...": "..." },
  "added_by_id": "f214...", "added_by_name": "Петя",
  "position": 0, "status": "queued", "duration_ms": 6000 }
```

`status`: `queued` → `playing` → `played` | `skipped`.

**Участник**

```json
{ "id": "2d32...", "nickname": "Вася", "role": "host",
  "connected": true, "joined_at": 1791922519344 }
```

`connected: false` — человек в списке, но сокет отвалился (скоро вернётся).
Роли: `host` (управляет) и `listener` (слушает, может добавлять треки).

**Снапшот** — всё состояние комнаты разом:

```json
{ "room": { "...": "..." }, "state": { "...": "..." },
  "queue": [ "..." ], "members": [ "..." ] }
```

---

## 4. REST API

Ошибки возвращаются как `{ "detail": "текст" }` с кодом 401 / 403 / 404 / 409 / 413 / 422.

### Вход

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| `POST` | `/api/auth/guest` | `{"nickname":"Вася"}` | `{participant_id, nickname}` + cookie |
| `GET` | `/api/auth/me` | — | `{participant_id, nickname}` |

### Комнаты

| Метод | Путь | Тело | Кто может |
|---|---|---|---|
| `POST` | `/api/rooms` | `{"name":"Вечеринка"}` | любой |
| `POST` | `/api/rooms/join` | `{"invite_code":"UXYZJ5HS"}` | любой |
| `GET` | `/api/rooms/{room_id}` | — | участник |
| `GET` | `/api/rooms/{room_id}/snapshot` | — | участник |
| `GET` | `/api/rooms/{room_id}/members` | — | участник |
| `POST` | `/api/rooms/{room_id}/leave` | — | участник |

Создатель комнаты автоматически становится `host`.

Выход из комнаты (`POST .../leave`) рассылает остальным `members_update`;
если ушедший был хостом — придёт ещё и `system` о передаче управления.
Выйти может и создатель: комната не удаляется, а живёт до idle-очистки (§10),
и при возвращении сокетом создатель снова становится хостом.

```bash
curl -X POST http://127.0.0.1:8000/api/rooms \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"name":"Вечеринка"}'
```

### Треки

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/tracks/upload` | multipart: `file`, `title`, `artist` |
| `GET` | `/api/tracks` | каталог, свежие первыми |
| `GET` | `/api/tracks/{track_id}` | один трек |

```bash
curl -X POST http://127.0.0.1:8000/api/tracks/upload \
  -b cookies.txt -F "file=@song.mp3" -F "title=In The End" -F "artist=Linkin Park"
```

Если `title` не передан — берётся имя файла без расширения.
Ограничения: до 50 МБ (`UPLOAD_MAX_MB`), только аудио-расширения
(`.mp3 .wav .ogg .oga .opus .m4a .aac .flac .webm .aiff`).

Файлы лежат в `backend/catalog/`, метаданные — в `backend/data/tracks.json`.
Раздача: `GET /media/<filename>`.

### Очередь

| Метод | Путь | Тело | Кто может |
|---|---|---|---|
| `GET` | `/api/rooms/{room_id}/queue` | — | участник |
| `POST` | `/api/rooms/{room_id}/queue` | `{"track_id":"a1b2c3d4"}` | **участник** |
| `DELETE` | `/api/rooms/{room_id}/queue/{item_id}` | — | **только host** |

Добавление трека доступно всем — это единственное действие слушателя.
Остальные получают `queue_update` по сокету.

---

## 5. Служебное

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/health` | Статус сервиса: версия, uptime, проверка каталогов, счётчики |
| `GET` | `/metrics` | Метрики в формате Prometheus |
| `GET` | `/docs` | Swagger UI |

### `/health`

Отдаёт `ok`, когда рабочие каталоги на месте. Если `catalog` или `data`
недоступны — возвращает `503` и `"status": "degraded"`, чтобы оркестратор
перезапустил контейнер. Запросы к `/health` не пишутся в access-лог.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_s": 42,
  "server_time": 1792073995984,
  "checks": { "catalog_dir": true, "data_dir": true },
  "tracks": 2,
  "sockets": 1,
  "errors_total": 0,
  "rooms": 2,
  "playing": 1,
  "connections": 1
}
```

### `/metrics`

Формат Prometheus — скрейпится любым агентом. Запросы считаются по
**шаблону** маршрута (`/api/rooms/{room_id}`), чтобы метки не раздувались
на каждом id. Необработанные ошибки (ответ `500` с телом
`{"detail": "Внутренняя ошибка сервера"}`) попадают в `app_errors_total`.

```
http_requests_total{method="GET",path="/api/rooms/{room_id}",status="200"} 12
http_requests_total{method="GET",path="unmatched",status="404"} 3
app_errors_total 0
app_ws_connections_active 2
app_rooms_total 1
app_uptime_seconds 3600
```

---

## 6. WebSocket

Подключение: `ws://127.0.0.1:8000/ws`

Cookie `pid` браузер приложит сам. Запасной вариант, если cookie не долетит:
`ws://127.0.0.1:8000/ws?pid=<participant_id>`.

```js
const ws = new WebSocket('ws://127.0.0.1:8000/ws');
ws.onopen = () => ws.send(JSON.stringify({ type: 'join', room_id }));
```

При подключении отправь `join`. Сервер в ответ пришлёт `joined`, затем `snapshot`
с полным состоянием. С этого момента держи `state` и пересчитывай позицию сам.

### Команды: клиент → сервер

| `type` | Поля | Кто | Что делает |
|---|---|---|---|
| `join` | `room_id` **или** `invite_code` | любой | войти в комнату, придёт `snapshot` |
| `leave` | — | любой | выйти (сокет можно не закрывать) |
| `ping` | `client_time` (необязательно) | любой | ответ `pong`, мерка часов |
| `play` | — | host | запустить / продолжить |
| `pause` | — | host | пауза на текущей позиции |
| `seek` | `position_ms` | host | перемотка |
| `skip` | — | host | следующий трек |
| `track_loaded` | `item_id`, `duration_ms` | любой | сообщить длительность (раздел 8) |
| `queue_remove` | `item_id` | host | убрать из очереди |

### События: сервер → клиент

Все события несут `server_time` (epoch-мс сервера) — он нужен для синхронизации.

| `type` | Содержимое | Когда |
|---|---|---|
| `joined` | `room_id`, `participant_id`, `role` | сразу после `join` |
| `snapshot` | `{room, state, queue, members}` | после `join` и при reconnect |
| `state` | `state` | play / pause / seek / skip / автосмена трека |
| `queue_update` | `queue` | добавление, удаление, смена играющего |
| `members_update` | `members` | кто вошёл / вышел / отвалился / сменился хост |
| `system` | `text`, иногда `host_id` | передача прав и прочие уведомления |
| `error` | `code`, `message` | отказ: не хост, нечего играть и т.п. |
| `pong` | `server_time`, эхо `client_time` | на `ping` |

### Коды ошибок в `error`

`unauthorized`, `room_not_found`, `not_in_room`, `forbidden`, `queue_empty`,
`nothing_playing`, `not_found`, `is_playing`, `bad_json`, `bad_request`,
`unknown_command`.

### Коды закрытия сокета

| Код | Значение |
|---|---|
| `4401` | нет валидной сессии — сначала `POST /api/auth/guest` |
| `4404` | этот сокет вытеснен новым подключением того же человека (refresh) |

### Пример диалога

```
→ {"type":"join","room_id":"7c1f..."}
← {"type":"joined","server_time":1791922519344,"room_id":"7c1f...","role":"host"}
← {"type":"snapshot","server_time":1791922519344,"data":{room, state, queue, members}}

→ {"type":"play"}
← {"type":"state","server_time":...,"state":{"is_playing":true,"position_ms":0,
     "updated_at":...,"duration_ms":6000,"version":1, ...}}
← (то же самое у всех остальных в комнате)

→ {"type":"seek","position_ms":30000}
← {"type":"state", ... "position_ms":30000, "version":2}

→ {"type":"pause"}
← {"type":"state", ... "is_playing":false, "position_ms":31840, "version":3}
```

---

## 7. Синхронизация по времени

Сервер — источник истины. Он шлёт **якорь**, а не текущую позицию: «в момент
`updated_at` позиция была `position_ms`». Клиент сам доезжает:

```js
position = is_playing
  ? position_ms + (now_server - updated_at)
  : position_ms
```

`now_server` = локальное время + смещение часов. Смещение меряется через `ping`:

```js
let clockOffset = 0;
let bestRtt = Infinity;

function sendPing(ws) {
  ws.send(JSON.stringify({ type: 'ping', client_time: Date.now() }));
}

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'pong') {
    const rtt = Date.now() - msg.client_time;
    // лучший кандидат — тот, у кого RTT минимальный
    if (rtt <= bestRtt) {
      bestRtt = rtt;
      clockOffset = msg.server_time - (msg.client_time + rtt / 2);
    }
  }
};

setInterval(() => sendPing(ws), 5000);

function positionNow(state) {
  if (!state) return 0;
  if (!state.is_playing) return state.position_ms;
  return state.position_ms + (Date.now() + clockOffset - state.updated_at);
}
```

Пингуй раз в 3–5 секунд, особенно сразу после `join` и после возврата на вкладку.

**Догон после seek/pause/skip.** Пришёл `state` с новым якорем — сдвинь
`<audio>.currentTime = positionNow(state) / 1000` и, если `is_playing`, играй.
Пропущенные события лечатся сами: клиент пересчитывает позицию локально, а
пропуск компенсируется тем, что придёт следующий `state`.

**Частая ошибка:** ставить `currentTime` на `position_ms` из события, не пересчитав
позицию на «сейчас». Между событием и его обработкой проходит время — трек уедет.

**Дрейф длинной сессии.** Раз в 30–60 секунд имеет смысл мягко подтягивать
`currentTime` к `positionNow(state)`, если расхождение больше 150–250 мс
(иначе будет слышно повторяющийся «сдвиг»).

---

## 8. Длительность трека

Сервер не умеет читать длительность из файла (нет ffprobe), поэтому её сообщает
фронтенд: как `<audio>` загрузил метаданные, шли

```json
{ "type": "track_loaded", "item_id": "<item_id из state>", "duration_ms": 224000 }
```

```js
audio.addEventListener('loadedmetadata', () => {
  ws.send(JSON.stringify({
    type: 'track_loaded',
    item_id: state.item_id,
    duration_ms: Math.round(audio.duration * 1000),
  }));
});
```

**Без этого автопереключение не работает**: сервер не знает, когда трек кончился,
и не перейдёт к следующему сам. Ручной `skip` при этом работает всегда.

Принимается для текущего играющего трека; отправлять может кто угодно.

---

## 9. Права

| Действие | host | listener |
|---|:---:|:---:|
| play / pause / seek / skip | ✅ | ❌ |
| убрать трек из очереди | ✅ | ❌ |
| добавить трек в очередь | ✅ | ✅ |
| слушать | ✅ | ✅ |

Попытка от слушателя возвращает `{"type":"error","code":"forbidden"}`.

---

## 10. Reconnect и уход хоста

**Reconnect.** Cookie та же → сервер узнаёт человека и не создаёт дубль.
При переподключении клиент шлёт `join` и получает свежий `snapshot` — с позицией,
очередью и участниками. Старый сокет того же человека вытесняется (код `4404`),
если он не умер как-то иначе.

**Ушёл хост.** Права управления переходят **первому подключённому слушателю**:
прилетает `members_update` с новой ролью и `system` вида
`"Управление передано: Петя"`.

**Хост вернулся.** Если это создатель комнаты (`creator_id`), он снова становится
`host` автоматически — достаточно войти по той же ссылке.

**Пустая комната.** Музыка ставится на паузу, комната живёт
`ROOM_IDLE_TTL_MIN` (по умолчанию 30 минут), затем удаляется. Каталог треков при
этом не трогается.

**Перезапуск сервера** — комнаты, участники и сессии теряются (они в памяти),
каталог треков остаётся. Для демо это нормально.

---

## 11. Подводные камни

- **`credentials: 'include'`** во всех `fetch`. Иначе cookie не долетит и будет 401.
- **CORS-origins** — фронт должен быть прописан в `.env`, иначе cookie не улетит.
- **`item_id`** для `track_loaded` и `queue_remove` — это id элемента **очереди**,
  а не трека. Бери из `state.item_id` или из `queue[].id`.
- **Название комнаты и ник** — обязательные непустые строки, ник до 32 символов.
- **Код приглашения** — 8 символов; регистр не важен: `uxyzj5hs` сработает как `UXYZJ5HS`.
- **Вкладка в фоне** браузеры душат таймеры — при `visibilitychange` пошли `ping`
  и пересчитай позицию, иначе после возврата на вкладку позиция уедет.
- **HTTPS-деплой:** поставь `COOKIE_SECURE=true` в `backend/.env` — cookie начнёт
  отдаваться только по HTTPS.