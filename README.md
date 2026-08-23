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

## Обязательная подготовка профиля Chrome

Парсер использует cookies, local storage и другие данные браузерной сессии. Без
подготовленного профиля маркетплейс может показать CAPTCHA, страницу входа или
урезанную выдачу, поэтому результаты парсинга могут быть пустыми.

Для каждой площадки используется отдельная копия профиля:

- Ozon: `parsers/userdata/`
- Wildberries: `parsers/userdata_wb/`
- Yandex Market: `parsers/userdata_yandex/`

### Рекомендуемый способ: создать чистые профили

1. Остановите сервис и все процессы Chrome, которые используют эти папки.
2. Запустите сервис локально с видимым браузером:

   ```bash
   HEADLESS=0 uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Выполните по одному тестовому запросу к Ozon, Wildberries и Yandex Market.
   Chrome автоматически создаст соответствующие папки `parsers/userdata*`.
4. В открывшихся окнах вручную войдите в аккаунты, пройдите CAPTCHA и подтвердите
   регион доставки. Затем закройте браузеры штатно.
5. Перезапустите сервис с `HEADLESS=1`. Сохранённые сессии будут использоваться
   при последующих запусках.

### Копирование существующего профиля Chrome

Этот вариант переносит cookies и настройки из уже настроенного Chrome. Он менее
надёжен: часть cookies может быть зашифрована средствами ОС. Не публикуйте и не
передавайте скопированный профиль — он может содержать активные сессии и личные
данные.

1. Откройте `chrome://version` в обычном Chrome и найдите поле **Profile Path**.
   Примеры стандартных путей:

   - Linux: `~/.config/google-chrome/Default`
   - macOS: `~/Library/Application Support/Google/Chrome/Default`
   - Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\Default`

2. Полностью закройте Chrome. Нельзя копировать профиль во время его работы.
3. Создайте отдельную копию для каждой площадки. Копировать нужно каталог
   `Default` вместе с файлом `Local State` из родительского каталога `User Data`.
   Пример для Linux:

   ```bash
   mkdir -p parsers/userdata parsers/userdata_wb parsers/userdata_yandex

   cp ~/.config/google-chrome/'Local State' parsers/userdata/
   cp -a ~/.config/google-chrome/Default parsers/userdata/

   cp ~/.config/google-chrome/'Local State' parsers/userdata_wb/
   cp -a ~/.config/google-chrome/Default parsers/userdata_wb/

   cp ~/.config/google-chrome/'Local State' parsers/userdata_yandex/
   cp -a ~/.config/google-chrome/Default parsers/userdata_yandex/
   ```

   Если в `chrome://version` указан `Profile 1`, `Profile 2` и т. п., копируйте
   выбранный каталог в целевую папку под именем `Default`, например:

   ```bash
   cp -a ~/.config/google-chrome/'Profile 1' parsers/userdata/Default
   ```

4. Один раз запустите парсер с `HEADLESS=0`, убедитесь, что нужные сайты открываются
   без входа и CAPTCHA, затем переключитесь на `HEADLESS=1`.

Папки `parsers/userdata*` исключены из Git намеренно. При переносе проекта на
другой компьютер их нужно подготовить заново; простое клонирование репозитория
не переносит авторизованные браузерные сессии.

Для Docker эти каталоги необходимо примонтировать в контейнер, иначе профиль
исчезнет при пересоздании контейнера:

```yaml
volumes:
  - ./parsers/userdata:/app/parsers/userdata
  - ./parsers/userdata_wb:/app/parsers/userdata_wb
  - ./parsers/userdata_yandex:/app/parsers/userdata_yandex
```

## Запуск в Docker

```bash
docker compose up --build
```

После старта:
- UI: `http://localhost:8000/`

В контейнере включен `HEADLESS=1`, чтобы Chrome работал без графической сессии.
Перед первым headless-запуском подготовьте профили по инструкции выше.

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
