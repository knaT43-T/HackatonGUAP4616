"""Смоук-тесты API «Слушаем вместе».

Покрывают основной путь: сессия → комнаты → каталог → очередь → WebSocket
(join/snapshot/ping, права host/listener, play/seek/track_loaded/pause,
передача прав при отключении хоста).

Запуск из папки backend:  python -m pytest
"""

from fastapi.testclient import TestClient

from app.main import app


def login(nickname: str) -> TestClient:
    """Отдельный пользователь со своим cookie-jar (без контекста lifespan)."""
    client = TestClient(app)
    r = client.post("/api/auth/guest", json={"nickname": nickname})
    assert r.status_code == 200, r.text
    return client


# --- 1. Сессия и комнаты ------------------------------------------------------


def test_auth_and_rooms():
    with TestClient(app) as host:
        r = host.post("/api/auth/guest", json={"nickname": "Вася"})
        assert r.status_code == 200, r.text
        assert "pid" in r.cookies
        assert host.get("/api/auth/me").json()["nickname"] == "Вася"

        r = host.post("/api/rooms", json={"name": "Вечеринка"})
        assert r.status_code == 200, r.text
        snap = r.json()
        room_id = snap["room"]["id"]
        code = snap["room"]["invite_code"]
        assert len(code) == 8
        assert snap["members"][0]["role"] == "host"

        # Второй участник заходит кодом в нижнем регистре — регистр не важен.
        guest = login("Петя")
        r = guest.post("/api/rooms/join", json={"invite_code": code.lower()})
        assert r.status_code == 200, r.text
        assert len(r.json()["members"]) == 2

        # Аноним не пускается в комнату.
        anon = TestClient(app)
        assert anon.get(f"/api/rooms/{room_id}/snapshot").status_code == 401

        # Выход из комнаты.
        r = guest.post(f"/api/rooms/{room_id}/leave")
        assert r.status_code == 200 and r.json()["left"] is True

        # health жив.
        health = host.get("/health").json()
        assert health["status"] == "ok" and health["rooms"] >= 1


# --- 2. WebSocket: плейбек, очередь, время -----------------------------------


def test_websocket_playback_flow():
    with TestClient(app) as host:
        host.post("/api/auth/guest", json={"nickname": "Вася"})
        room_id = host.post("/api/rooms", json={"name": "Плейбек"}).json()["room"]["id"]

        # Загружаем трек и ставим в очередь.
        files = {"file": ("in the end.mp3", b"ID3-fake-bytes", "audio/mpeg")}
        r = host.post(
            "/api/tracks/upload",
            files=files,
            data={"title": "In The End", "artist": "Linkin Park"},
        )
        assert r.status_code == 200, r.text
        track = r.json()
        assert track["title"] == "In The End" and track["url"].endswith(".mp3")

        r = host.post(f"/api/rooms/{room_id}/queue", json={"track_id": track["id"]})
        assert r.status_code == 201, r.text
        item = r.json()

        with host.websocket_connect("/ws") as ws:
            ws.send_json({"type": "join", "room_id": room_id})
            joined = ws.receive_json()
            assert joined["type"] == "joined" and joined["role"] == "host", joined
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"

            # ping/pong — мерка часов.
            ws.send_json({"type": "ping", "client_time": 123})
            pong = ws.receive_json()
            assert pong["type"] == "pong" and pong["client_time"] == 123

            # Мусорные команды не роняют сокет.
            ws.send_json({"type": "нечто"})
            assert ws.receive_json()["code"] == "unknown_command"
            ws.send_json({"type": "join", "room_id": "нет-такой"})
            assert ws.receive_json()["code"] == "room_not_found"

            # Играем: state + queue_update (сменился играющий элемент).
            ws.send_json({"type": "play"})
            st = ws.receive_json()
            assert st["type"] == "state" and st["state"]["is_playing"], st
            assert st["state"]["item_id"] == item["id"]
            assert ws.receive_json()["type"] == "queue_update"

            # Клиент сообщает длительность — сервер запоминает.
            ws.send_json(
                {"type": "track_loaded", "item_id": item["id"], "duration_ms": 200_000}
            )
            st = ws.receive_json()
            assert st["state"]["duration_ms"] == 200_000

            # Перемотка и пауза фиксируют якорь.
            ws.send_json({"type": "seek", "position_ms": 30_000})
            st = ws.receive_json()
            assert st["state"]["position_ms"] == 30_000

            ws.send_json({"type": "pause"})
            st = ws.receive_json()
            assert st["state"]["is_playing"] is False
            assert st["state"]["position_ms"] >= 30_000  # время шло, позиция не откатилась


def test_websocket_empty_queue_error():
    with TestClient(app) as host:
        host.post("/api/auth/guest", json={"nickname": "Вася"})
        room_id = host.post("/api/rooms", json={"name": "Пусто"}).json()["room"]["id"]

        with host.websocket_connect("/ws") as ws:
            ws.send_json({"type": "join", "room_id": room_id})
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "play"})
            err = ws.receive_json()
            assert err["type"] == "error" and err["code"] == "queue_empty", err


# --- 3. Права и передача хоста ------------------------------------------------


def test_ws_rights_and_host_transfer():
    with TestClient(app) as host:
        host.post("/api/auth/guest", json={"nickname": "Вася"})
        snap = host.post("/api/rooms", json={"name": "Права"}).json()
        room_id = snap["room"]["id"]
        code = snap["room"]["invite_code"]

        listener = login("Петя")
        listener.post("/api/rooms/join", json={"invite_code": code})

        with host.websocket_connect("/ws") as ws_host:
            ws_host.send_json({"type": "join", "room_id": room_id})
            j = ws_host.receive_json()
            ws_host.receive_json()
            assert j["role"] == "host", j

            with listener.websocket_connect("/ws") as ws_listener:
                ws_listener.send_json({"type": "join", "room_id": room_id})
                j = ws_listener.receive_json()
                ws_listener.receive_json()
                assert j["role"] == "listener", j

                # Хост узнал о подключении слушателя.
                assert ws_host.receive_json()["type"] == "members_update"

                # Слушателю нельзя управлять.
                ws_listener.send_json({"type": "pause"})
                err = ws_listener.receive_json()
                assert err["type"] == "error" and err["code"] == "forbidden", err

                # Хост уходит из комнаты → права переходят первому слушателю.
                r = host.post(f"/api/rooms/{room_id}/leave")
                assert r.status_code == 200

                members = ws_listener.receive_json()
                assert members["type"] == "members_update"
                petya = next(m for m in members["members"] if m["nickname"] == "Петя")
                assert petya["role"] == "host", petya
                names = [m["nickname"] for m in members["members"]]
                assert "Вася" not in names, names

                system = ws_listener.receive_json()
                assert system["type"] == "system"
                assert "Управление передано" in system["text"], system

                # То же видно и в REST-снапшоте.
                snap = listener.get(f"/api/rooms/{room_id}").json()
                petya = next(m for m in snap["members"] if m["nickname"] == "Петя")
                assert snap["room"]["host_id"] == petya["id"]
