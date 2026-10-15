# Backend — «Слушаем вместе»

FastAPI-приложение: REST (сессии, комнаты, каталог, очередь) и WebSocket
(синхронное воспроизведение, участники). Полная спецификация протокола —
[`API.md`](../API.md).

---

## Стек

| Слой | Технология |
|---|---|
| Web | FastAPI + uvicorn |
| Валидация и настройки | Pydantic v2, pydantic-settings |
| Realtime | WebSocket (нативный FastAPI) |
| Хранилище | в памяти + JSON-файл каталога, аудиофайлы на диске |
| Тесты и линт | pytest, httpx (TestClient), ruff |

---

## Запуск

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # опционально: все настройки имеют дефолты
python -m app.main       # http://127.0.0.1:8000
```

- `RELOAD=true` в `.env` — автоперезапуск при изменении кода.
- Swagger: http://127.0.0.1:8000/docs
- В контейнере (Docker) используется та же команда `python -m app.main`.

---

## Структура

```
app/
├── main.py          # сборка приложения, middleware, /health, /metrics, запуск
├── config.py        # настройки из окружения и .env
├── schemas.py       # схемы тел запросов
├── api/
│   ├── deps.py      # cookie-сессия, проверки прав (участник/хост)
│   └── routes/      # auth, rooms, tracks, queue
├── core/
│   ├── models.py    # домен: Room, QueueItem, Participant, Principal
│   ├── sessions.py  # сессии по cookie "pid"
│   ├── clock.py     # серверное время, позиция воспроизведения
│   ├── logging.py   # формат логов, фильтр «тихих» путей
│   └── metrics.py   # счётчики для /metrics
├── realtime/
│   ├── ws.py        # обработчик /ws: команды клиента
│   ├── hub.py       # реестр сокетов и рассылки
│   ├── events.py    # сборка событий «сервер → клиент»
│   └── ticker.py    # фоновый тикер: автопереход треков, очистка комнат
└── services/        # бизнес-логика: playback, queue, tracks, rooms
```

---

## Настройки

Все переменные имеют дефолты (полный список — `app/config.py` и комментарии
в `.env.example`).

| Переменная | Дефолт | Значение |
|---|---|---|
| `HOST` / `PORT` | `0.0.0.0` / `8000` | адрес сервера |
| `RELOAD` | `false` | автоперезапуск (для разработки) |
| `COOKIE_NAME` | `pid` | имя cookie-сессии |
| `COOKIE_SECURE` | `false` | отдавать cookie только по HTTPS |
| `SESSION_TTL_DAYS` | `30` | срок жизни сессии |
| `NICKNAME_MAX_LEN` | `32` | максимальная длина ника |
| `ROOM_NAME_MAX_LEN` | `60` | максимальная длина названия комнаты |
| `CORS_ORIGINS` | `localhost:5173/3000` | origin'ы фронтенда (JSON-массив) |
| `CATALOG_DIR` | `catalog` | аудиофайлы треков |
| `DATA_DIR` | `data` | метаданные (`tracks.json`) |
| `UPLOAD_MAX_MB` | `50` | лимит загрузки трека |
| `ROOM_IDLE_TTL_MIN` | `30` | автоочистка комнат без участников |
| `TICKER_INTERVAL_MS` | `1000` | период фонового тикера |
| `BROADCAST_TIMEOUT_S` | `5.0` | таймаут рассылки в сокет |
| `LOG_LEVEL` | `INFO` | уровень логов |
| `ACCESS_LOG` | `true` | access-лог запросов |

---

## Тесты и линт

```bash
pip install -r requirements-dev.txt
python -m pytest    # смоук: REST + WebSocket + наблюдаемость
ruff check .        # линт (конфиг — ruff.toml)
```

Тесты поднимают приложение в памяти и не трогают рабочие папки `catalog/`
и `data/` — рабочие каталоги подменяются временными (см. `tests/conftest.py`).

---

## Логи и мониторинг

- **Логи** — единый формат `дата уровень имя: сообщение`; uvicorn пишет туда же.
  Уровень — `LOG_LEVEL`, access-лог выключается через `ACCESS_LOG=false`.
  Запросы к `/health` и `/metrics` в access-лог не попадают.
- **`/health`** — статус, версия, uptime, проверка рабочих каталогов, счётчики
  комнат/сокетов/треков/ошибок. Если каталоги недоступны — `503` и
  `"status": "degraded"`.
- **`/metrics`** — формат Prometheus: `http_requests_total{method,path,status}`
  (по шаблонам маршрутов, без раздувания меток), `app_errors_total`,
  `app_ws_connections_active`, `app_rooms_total/playing`,
  `app_participants_connected`, `app_tracks`, `app_uptime_seconds`.
- **Ошибки** — middleware в `main.py` ловит необработанные исключения: пишет
  трейсбек в лог, отвечает JSON `500` и увеличивает `app_errors_total`.

---

## Данные

- `catalog/` — загруженные аудиофайлы (имя = id трека + расширение).
- `data/tracks.json` — метаданные каталога, атомарная запись через tmp-файл.
- Обе папки создаются автоматически и не попадают в git.
