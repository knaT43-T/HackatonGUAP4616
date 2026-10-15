"""Общая настройка тестов.

ВАЖНО: переменные окружения выставляются до импорта `app`, потому что
`app.config.settings` читает их при первом импорте. Так тесты не трогают
рабочие папки `backend/catalog` и `backend/data`.
"""

import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="listen-together-tests-")
os.environ["CATALOG_DIR"] = os.path.join(_TMP, "catalog")
os.environ["DATA_DIR"] = os.path.join(_TMP, "data")


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP, ignore_errors=True)
