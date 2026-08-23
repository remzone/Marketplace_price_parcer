import os
import logging
import re
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("parser_service")
logger.setLevel(logging.DEBUG)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Пути к папкам с последними продуктами
OZON_SNAPSHOTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "ozon", "html_snapshots", "last_products"))
WB_SNAPSHOTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "wb", "html_snapshots", "last_products"))
YANDEX_SNAPSHOTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "yandex", "html_snapshots", "last_products"))

def extract_prices_from_blocks(raw_prices):
    clean_prices = []

    for block in raw_prices:
        text = block.get_text(strip=True)
        clean = text.replace("\u2009", "").replace("₽", "").replace(" ", "").strip()

        if clean.isdigit():
            clean_prices.append(int(clean))

    if not clean_prices:
        return None, None, None

    sorted_prices = sorted(clean_prices, reverse=True)

    price_before_discount = str(sorted_prices[0]) if len(sorted_prices) >= 1 else None
    price_without_card = str(sorted_prices[1]) if len(sorted_prices) >= 2 else None
    price_with_card = str(sorted_prices[-1]) if len(sorted_prices) >= 1 else None

    return price_with_card, price_without_card, price_before_discount

def extract_seller_name(soup):
    seller_block = soup.find("div", attrs={"data-widget": "webCurrentSeller"})
    if not seller_block:
        return "Ozon"

    for el in seller_block.descendants:
        if isinstance(el, Tag) and el.get("title") and el.get("href"):
            if "https://www.ozon.ru/seller/" in el["href"]:
                return el["title"].strip()

    return "Ozon"

def extract_article(soup):
    sku_button = soup.find("button", attrs={"data-widget": "webDetailSKU"})
    if not sku_button:
        logger.debug("⚠️ Блок webDetailSKU (button) не найден")
        return "—"

    divs = sku_button.find_all("div")
    for div in divs:
        text = div.get_text(strip=True)
        if "Артикул" in text:
            logger.debug(f"🔎 Найден текст в div: {text}")
            match = re.search(r"\d+", text)
            if match:
                return match.group(0)

    logger.debug("⚠️ Артикул не найден внутри button webDetailSKU")
    return "—"

def process_ozon_product(soup):
    title_tag = soup.find("h1")
    name = title_tag.get_text(strip=True) if title_tag else "—"

    article = extract_article(soup)

    canonical_tag = soup.find("link", {"rel": "canonical"})
    link = canonical_tag["href"] if canonical_tag else "—"

    sale_block = soup.find("div", attrs={"data-widget": "webSale"})
    price_container = None

    if sale_block:
        children = sale_block.find_all("div", recursive=False)
        if children:
            first_child = children[0]
            price_container = first_child.find("div", attrs={"data-widget": "webPrice"})
        else:
            price_container = sale_block.find("div", attrs={"data-widget": "webPrice"})

    raw_prices = []
    if price_container:
        raw_prices = price_container.find_all(["span", "div"], string=lambda t: t and "₽" in t)

    price_with_card, price_without_card, price_before_discount = extract_prices_from_blocks(raw_prices)

    seller = extract_seller_name(soup)

    characteristics = {}
    section_char = soup.find("div", id="section-characteristics")
    if section_char:
        dls = section_char.find_all("dl")
        for dl in dls:
            dt = dl.find("dt")
            dd = dl.find("dd")
            if dt and dd:
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                characteristics[key] = value

    return {
        "name": name,
        "article": article,
        "price_without_card": price_without_card or "—",
        "price_with_card": price_with_card or "—",
        "price_before_discount": price_before_discount or "—",
        "seller": seller,
        "link": link,
        "characteristics": characteristics,
    }

def process_wb_product(soup):
    name_tag = soup.find("h1", class_="product-page__title")
    name = name_tag.get_text(strip=True) if name_tag else "—"

    price_tag = soup.find("ins", class_="price-block__final-price red-price")
    if not price_tag:
        price_tag = soup.find("ins", class_="price-block__final-price")
    price_with_card = (
        price_tag.get_text(strip=True).replace("₽", "").replace("\xa0", "").replace(" ", "")
        if price_tag else "—"
    )

    price_without_card = price_with_card

    old_price_tag = soup.find("del", class_="price-block__old-price")
    price_before_discount = (
        old_price_tag.get_text(strip=True).replace("₽", "").replace("\xa0", "").replace(" ", "")
        if old_price_tag else "—"
    )

    article = "—"
    params_table = soup.find("table", class_="product-params__table")
    if params_table:
        rows = params_table.find_all("tr", class_="product-params__row")
        for row in rows:
            th = row.find("th", class_="product-params__cell")
            td = row.find("td", class_="product-params__cell")
            if th and td:
                th_text = th.get_text(strip=True)
                if "Артикул" in th_text:
                    article_span = td.find("span", id="productNmId")
                    if article_span:
                        article = article_span.get_text(strip=True)
                        break

    seller_tag = soup.find("span", class_="seller-info__name")
    seller = seller_tag.get_text(strip=True) if seller_tag else "Wildberries"

    a_tag = soup.find("a", class_="product-line__img img-plug")
    link = a_tag["href"] if a_tag and a_tag.has_attr("href") else "—"

    characteristics = {}
    if params_table:
        rows = params_table.find_all("tr", class_="product-params__row")
        for row in rows:
            th = row.find("th", class_="product-params__cell")
            td = row.find("td", class_="product-params__cell")
            if th and td:
                key = th.get_text(strip=True)
                value = td.get_text(strip=True)
                characteristics[key] = value

    return {
        "name": name,
        "article": article,
        "price_without_card": price_without_card,
        "price_with_card": price_with_card,
        "price_before_discount": price_before_discount,
        "seller": seller,
        "link": link,
        "characteristics": characteristics,
    }

def process_yandex_product(soup):
    name_tag = soup.find("h1", attrs={"data-auto": "productCardTitle"})
    name = name_tag.get_text(strip=True) if name_tag else "—"

    canonical_tag = soup.find("link", {"rel": "canonical"})
    link = canonical_tag["href"] if canonical_tag and canonical_tag.has_attr("href") else "—"

    # Цена с картой
    price_card_tag = soup.find("span", attrs={"data-auto": "snippet-price-current"})
    price_with_card = price_card_tag.get_text(strip=True).replace("₽", "").replace("\xa0", "").replace(" ", "") if price_card_tag else "—"

    # Цена без карты
    price_without_card = "—"
    price_old_tag = soup.find("span", attrs={"data-auto": "snippet-price-old"})
    if price_old_tag:
        value_lines = price_old_tag.find_all("span", class_="ds-valueLine")
        if value_lines:
            first_line = value_lines[0]
            spans = first_line.find_all("span")
            if spans:
                price_without_card = spans[0].get_text(strip=True).replace("₽", "").replace("\xa0", "").replace(" ", "")

    # Цена до скидки
    price_before_discount = "—"
    if price_old_tag:
        strike_line = price_old_tag.find("span", class_="ds-text_decoration_line-through")
        if strike_line:
            price_before_discount = strike_line.get_text(strip=True).replace("₽", "").replace("\xa0", "").replace(" ", "")

    # Продавец
    seller = "Яндекс.Маркет"
    shop_block = soup.find("div", attrs={"data-auto": "shop-info-block"})
    if shop_block:
        title_block = shop_block.find("div", attrs={"data-auto": "shop-info-title"})
        if title_block:
            span_tag = title_block.find("span")
            if span_tag:
                seller = span_tag.get_text(strip=True)

    # Характеристики и артикул
    characteristics = {}
    article = "—"
    specs_section = soup.find("div", attrs={"data-zone-name": "ProductSpecsList"})
    if specs_section:
        spec_blocks = specs_section.find_all("div", attrs={"data-auto": "specs-list-minimal"})
        for block in spec_blocks:
            items = block.find_all("div", class_="_3rW2x")
            for item in items:
                key_tag = item.find("span", attrs={"data-auto": "product-spec"})
                value_tag = item.find("div", class_="ds-text")
                if key_tag and value_tag:
                    key = key_tag.get_text(strip=True)
                    value_span = value_tag.find("span")
                    value = value_span.get_text(strip=True) if value_span else value_tag.get_text(strip=True)

                    if "Артикул" in key and article == "—":
                        article = value

                    characteristics[key] = value

    return {
        "name": name,
        "article": article,
        "price_without_card": price_without_card,
        "price_with_card": price_with_card,
        "price_before_discount": price_before_discount,
        "seller": seller,
        "link": link,
        "characteristics": characteristics,
    }


def process_products():
    products = []

    for marketplace_name, base_path in [("Ozon", OZON_SNAPSHOTS_PATH), ("WB", WB_SNAPSHOTS_PATH), ("Yandex", YANDEX_SNAPSHOTS_PATH)]:
        if not os.path.exists(base_path):
            logger.warning(f"📁 Папка не найдена: {base_path}")
            continue

        files = [f for f in os.listdir(base_path) if f.endswith(".html")]
        logger.info(f"🔎 [{marketplace_name}] Найдено HTML файлов: {len(files)}")

        for file_name in files:
            file_path = os.path.join(base_path, file_name)
            logger.info(f"📄 [{marketplace_name}] Обрабатывается файл: {file_name}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "lxml")

            if marketplace_name == "Ozon":
                product_data = process_ozon_product(soup)
            elif marketplace_name == "WB":
                product_data = process_wb_product(soup)
            elif marketplace_name == "Yandex":
                product_data = process_yandex_product(soup)
            else:
                continue

            if product_data:
                product_data["marketplace"] = marketplace_name
                products.append(product_data)

            logger.info("✅ Товар успешно обработан\n" + "-" * 50)

    logger.info(f"🎉 Всего обработано товаров: {len(products)}")
    return products

class ParserService:
    def __init__(self):
        logger.info("🌀 ParserService инициализирован")

    def process_products(self):
        return process_products()

    def parse_categories(self):
        return {"status": "success", "categories": []}

    def update_prices(self):
        return {"status": "success", "updated": True}

__all__ = [
    "process_products",
    "ParserService",
]
