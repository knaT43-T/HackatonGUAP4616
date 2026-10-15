"""Настройка логирования для бэкенда.

Одна точка входа — `setup_logging()`:
* единый формат и уровень (LOG_LEVEL);
* uvicorn пишет в те же хендлеры (запуск через `python -m app.main`);
* служебные пути (/health, /metrics) не засоряют access-лог.

Модуль вызывается при импорте `app.main`, поэтому логи в нашем формате
появляются при любом способе запуска.
"""

from __future__ import annotations

import logging
import sys

from app.config import settings

# Пути, которые опрашиваются часто (докер-хелсчек, скрейперы): их записи
# в access-логе только создают шум.
SILENT_ACCESS_PATHS = {"/health", "/metrics"}

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"


class SilentPathsFilter(logging.Filter):
    """Не пропускает в access-лог записи о служебных путях.

    Uvicorn логирует доступ строкой `'%s - "%s %s HTTP/%s" %d'`, где
    `path` — третий аргумент. Достаём его и сверяем со списком.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3:
            path = args[2]
            if isinstance(path, str) and path.split("?", 1)[0] in SILENT_ACCESS_PATHS:
                return False
        return True


def resolve_level(name: str) -> str:
    """Приводит уровень из настроек к валидному имени (иначе INFO)."""

    candidate = (name or "INFO").upper()
    return candidate if isinstance(logging.getLevelName(candidate), int) else "INFO"


def setup_logging() -> None:
    level_name = resolve_level(settings.log_level)
    level = logging.getLevelName(level_name)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT, DATEFMT))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Убираем шум хелсчеков и метрик из access-лога. Фильтр на логгере
    # работает при любом способе запуска uvicorn (log_config=None и дефолт).
    logging.getLogger("uvicorn.access").addFilter(SilentPathsFilter())
