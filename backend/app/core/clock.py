from __future__ import annotations

import time


def now_ms() -> int:
    return int(time.time() * 1000)


def effective_position_ms(position_ms: int, updated_at: int, is_playing: bool) -> int:
    if not is_playing:
        return position_ms
    return position_ms + max(0, now_ms() - updated_at)