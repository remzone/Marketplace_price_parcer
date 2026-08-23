import os
import time
import logging
import asyncio
import concurrent.futures
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc  # type: ignore
import shutil

logger = logging.getLogger("wb_parser")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(ch)

# 📄 Абсолютный путь до data/wb/html_snapshots
current_dir = os.path.dirname(__file__)
BASE_SAVE_PATH = os.path.abspath(os.path.join(current_dir, "..", "..", "data", "wb", "html_snapshots"))

SEARCH_DIR = os.path.join(BASE_SAVE_PATH, "last_search")
PRODUCTS_DIR = os.path.join(BASE_SAVE_PATH, "last_products")

# Создаем папки
os.makedirs(SEARCH_DIR, exist_ok=True)
os.makedirs(PRODUCTS_DIR, exist_ok=True)

def is_headless_enabled() -> bool:
    return os.getenv("HEADLESS", "1").strip().lower() not in {"0", "false", "no"}

def setup_driver_uc():
    options = uc.ChromeOptions()
    user_data_path = os.path.join(os.path.dirname(__file__), "userdata_wb")
    options.add_argument(f"--user-data-dir={user_data_path}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    if is_headless_enabled():
        options.add_argument("--headless=new")

    logger.info(f"⚙️ [CHROME] Настройка профиля: {user_data_path}")
    driver = uc.Chrome(options=options)
    return driver

def clear_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def blocking_parse(query: str, scrolls: int, max_cards: int, search_type: str = "name"):
    logger.info(f"💬 [WB] Запуск поиска: '{query}', скроллов: {scrolls}, max карточек: {max_cards}, тип поиска: {search_type}")

    clear_folder(SEARCH_DIR)
    clear_folder(PRODUCTS_DIR)

    driver = setup_driver_uc()
    result = {
        "search_file": None,
        "products": []
    }

    try:
        if search_type == "link":
            logger.info(f"➡️ Переход по прямой ссылке: {query}")
            driver.get(query)
            time.sleep(5)

            product_filename = os.path.join(PRODUCTS_DIR, "product_link.html")
            with open(product_filename, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info(f"✅ Сохранён HTML товара (по ссылке): {product_filename}")

            result["products"].append({
                "url": driver.current_url,
                "filename": product_filename
            })

        else:
            url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}"
            driver.get(url)
            logger.info("⚡ Загрузка страницы поиска WB")
            time.sleep(5)

            if search_type == "name":
                last_height = driver.execute_script("return document.body.scrollHeight")
                for i in range(scrolls):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        logger.info(f"⚠️ Скролл остановлен, высота не изменилась на итерации {i+1}")
                        break
                    last_height = new_height
                    logger.info(f"🌀 Выполнен скролл {i+1}/{scrolls}")

                search_html_path = os.path.join(SEARCH_DIR, "search.html")
                with open(search_html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.info(f"✅ Сохранён HTML поиска: {search_html_path}")
                result["search_file"] = search_html_path

                link_elements = driver.find_elements(By.CSS_SELECTOR, "a.product-card__link")
                hrefs = []
                for el in link_elements:
                    try:
                        href = el.get_attribute("href")
                        if href:
                            hrefs.append(href)
                    except Exception:
                        continue

                unique_hrefs = list(dict.fromkeys(hrefs))
                logger.info(f"🔎 Найдено ссылок на карточки: {len(hrefs)}")
                logger.info(f"✅ Уникальных карточек для обработки: {len(unique_hrefs)}")

                count = min(len(unique_hrefs), max_cards)
                for idx, href in enumerate(unique_hrefs[:count], start=1):
                    logger.info(f"➡️ Обработка карточки {idx}/{count}: {href}")
                    driver.get(href)
                    time.sleep(4)

                    product_filename = os.path.join(PRODUCTS_DIR, f"product_{idx}.html")
                    with open(product_filename, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    logger.info(f"✅ Сохранён HTML товара {idx}: {product_filename}")

                    result["products"].append({
                        "url": href,
                        "filename": product_filename
                    })

                logger.info(f"🎯 Обработано карточек: {count}")

            elif search_type == "article":
                time.sleep(5)

                product_filename = os.path.join(PRODUCTS_DIR, "product_article.html")
                with open(product_filename, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.info(f"✅ Сохранён HTML товара (артикул): {product_filename}")

                result["products"].append({
                    "url": driver.current_url,
                    "filename": product_filename
                })

            else:
                logger.warning(f"Неизвестный тип поиска: {search_type}")

    finally:
        driver.quit()
        logger.info("🛑 Браузер закрыт")

    return result

async def async_parse_search(query: str, scrolls: int, max_cards: int, search_type: str = "name"):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, blocking_parse, query, scrolls, max_cards, search_type)
    return result

async def async_parse_by_link(link: str):
    logger.info(f"💬 Запуск парсинга по ссылке: {link}")
    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, blocking_parse, link, 1, 1, "link")
    return result
