# HackatonGUAP4616

# Слушаем вместе

[![Linter](https://github.com/OWNER/REPO/actions/workflows/ci_linter_test.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci_linter_test.yml)
[![Python Test](https://github.com/OWNER/REPO/actions/workflows/ci_python_test.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci_python_test.yml)
[![Frontend Build](https://github.com/OWNER/REPO/actions/workflows/ci_frontend_build.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci_frontend_build.yml)

---

## 🛠 Необходимое ПО

Перед запуском проекта убедитесь, что у вас установлены:

- 🐋 Docker (версия 20.10 или выше)

---

## 🚀 Инструкция по запуску

Проект полностью контейнеризирован. Запуск базы данных, создание таблиц и старт приложения происходят автоматически.

### 1. Подготовка окружения

Скопируйте шаблон конфигурации в рабочий файл `.env`:

```bash
cp env.example .env
```

_После копирования вы можете открыть файл `.env` и отредактировать доступы к базе данных, если дефолтные вам не подходят._

### 2. Запуск проекта

Выполните следующую команду в корневой директории:

```bash
docker-compose up --build
```

## 📁 Структура репозитория

- backend — приложение, каталог треков, данные, зависимости, пример env.
- frontend — исходники, публичные файлы, package.json.
- docs — документация, включая front.api.md.
- docker-compose.yml — оркестрация сервисов.
- README.md — этот файл.
- .env.example — пример конфигурации.

---

#### Разработчики

- Кирилл — DevOps / инфраструктура / деплой
- Андрей — Backend-разработчик / API / WebSocket / синхронизация
- Костя — Геймдизайнер / менеджер / ТЗ / приёмка MVP
- Артём — Frontend-разработчик / UI комнаты и плеера
- Ярослав — QA / тестирование real-time и сценариев
