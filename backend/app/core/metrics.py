"""Простые счётчики для мониторинга — без внешних зависимостей.

Считаем HTTP-запросы по (метод, шаблон маршрута, статус) и ошибки (5xx).
Отдаём в формате Prometheus на `/metrics`: его поймёт любой скрейпер,
а человек может посмотреть `curl http://localhost:8000/metrics`.

Важно: в метках используется ШАБЛОН пути (`/api/rooms/{room_id}`), а не
сырой URL — иначе кардинальность метрик раздуется на каждом id.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_started_at = time.monotonic()

_requests: dict[tuple[str, str, str], int] = defaultdict(int)
_errors_total = 0


def observe_request(method: str, path: str, status: int) -> None:
    with _lock:
        _requests[(method.upper(), path, str(status))] += 1
    if status >= 500:
        observe_error()


def observe_error() -> None:
    global _errors_total
    with _lock:
        _errors_total += 1


def errors_total() -> int:
    with _lock:
        return _errors_total


def uptime_seconds() -> float:
    return time.monotonic() - _started_at


def render_prometheus(gauges: dict[str, float] | None = None) -> str:
    with _lock:
        requests = dict(_requests)
        errors = _errors_total

    lines = [
        "# HELP app_uptime_seconds Время с запуска процесса, секунды",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {uptime_seconds():.0f}",
        "# HELP app_errors_total Ошибки сервиса (HTTP 5xx и необработанные исключения)",
        "# TYPE app_errors_total counter",
        f"app_errors_total {errors}",
        "# HELP http_requests_total HTTP-запросы по маршрутам",
        "# TYPE http_requests_total counter",
    ]
    for (method, path, status), count in sorted(requests.items()):
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    for name, value in sorted((gauges or {}).items()):
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value:g}")
    return "\n".join(lines) + "\n"
