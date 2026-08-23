# priceparcer

FastAPI-сервис для парсинга карточек товаров с Ozon, Wildberries и Yandex Market.

Сервис работает в два шага:
1. Selenium + `undetected_chromedriver` открывает страницы и сохраняет HTML-снимки.
2. `BeautifulSoup` извлекает из снимков имя, цены, артикул, продавца, ссылку и характеристики.

## Возможности

- Поиск по названию, артикулу и прямой ссылке.
- Поиск по одной площадке (`/search`) и по всем сразу (`/api/search-all`, только для `name`).
- Повторный разбор последних HTML-снимков (`/last-results-parse`).
- Веб-интерфейс и простая локальная документация API (`/frontend/docs.html`).

## Стек

- Python 3
- FastAPI + Uvicorn
- Selenium + undetected-chromedriver
- BeautifulSoup + lxml
- Jinja2

## Быстрый локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Открыть:
- UI: `http://localhost:8000/`
- Docs page: `http://localhost:8000/frontend/docs.html`

## Запуск в Docker

```bash
docker compose up --build
```

После старта:
- UI: `http://localhost:8000/`

В контейнере включен `HEADLESS=1`, чтобы Chrome работал без графической сессии.

## Переменные окружения

- `HEADLESS`:
  - `1` (по умолчанию) - headless режим браузера.
  - `0` - запуск с UI (обычно локально, не для контейнера).

## Полезные API точки

- `POST /search`
- `POST /api/search-all`
- `GET /last-results-parse?marketplace=ozon`

Примеры запросов есть в `frontend/docs.html`.

## Что не коммитить в git

Проект содержит тяжелые и чувствительные runtime-данные:
- папки браузерных профилей `parsers/userdata*`
- HTML-снимки `data/*/html_snapshots`
- логи `logs/`
- локальные окружения (`.venv`, `.env`)

Все это добавлено в `.gitignore`.

## Рекомендация по инициализации отдельного репозитория

Если хотите вести `priceparcer` как отдельный проект:

```bash
cd /root/project/priceparcer
git init
git add .
git commit -m "Initial commit: dockerized parser service"
```
