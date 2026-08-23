import os
import logging
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import importlib

log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "server.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "frontend"))

frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if not os.path.exists(frontend_path):
    logger.warning(f"Папка фронтенда не найдена по пути: {frontend_path}")
else:
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")

PARSERS = {
    "ozon": "parsers.ozon",
    "wildberries": "parsers.wildberries",
    "yandex": "parsers.yandex",
}

from parsers.parser_service import ParserService

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.info(f"Главная страница запрошена: {request.client.host}")

    service_instance = ParserService()
    parsed_results = service_instance.process_products()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": parsed_results,
            "search_type": "name",
            "query": "",
            "marketplace": "ozon",
        }
    )

@app.post("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    query: str = Form(...),
    search_type: str = Form('name'),
    scrolls: int = Form(1),
    max_cards: int = Form(3),
    marketplace: str = Form("ozon")
):
    logger.info(f"Получен запрос поиска: query={query}, type={search_type}, scrolls={scrolls}, max_cards={max_cards}, marketplace={marketplace} от {request.client.host}")

    parser_module_name = PARSERS.get(marketplace.lower())
    if not parser_module_name:
        error_msg = f"Парсер для маркетплейса '{marketplace}' не найден"
        logger.error(error_msg)
        return templates.TemplateResponse("index.html", {"request": request, "results": None, "query": query, "search_type": search_type, "error": error_msg, "marketplace": marketplace})

    try:
        parser_module = importlib.import_module(parser_module_name)

        if search_type == "link":
            parse_func = getattr(parser_module, "async_parse_by_link", None)
            if not parse_func:
                error_msg = f"Функция парсинга по ссылке не найдена в модуле {parser_module_name}"
                logger.error(error_msg)
                return templates.TemplateResponse("index.html", {"request": request, "results": None, "query": query, "search_type": search_type, "error": error_msg, "marketplace": marketplace})

            await parse_func(query)

        else:
            if marketplace.lower() == "ozon" and search_type == "article":
                scrolls = 1
                max_cards = 1

            if marketplace.lower() == "ozon":
                parse_func = getattr(parser_module, "async_parse_ozon_search", None)
            else:
                parse_func = getattr(parser_module, "async_parse_search", None)

            if not parse_func:
                error_msg = f"Функция парсинга не найдена в модуле {parser_module_name}"
                logger.error(error_msg)
                return templates.TemplateResponse("index.html", {"request": request, "results": None, "query": query, "search_type": search_type, "error": error_msg, "marketplace": marketplace})

            await parse_func(query, scrolls, max_cards, search_type)

        service_instance = ParserService()
        parsed_results = service_instance.process_products()

        logger.info(f"Перепарсинг завершён: найдено {len(parsed_results)} продуктов")

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": parsed_results,
                "query": query,
                "search_type": search_type,
                "marketplace": marketplace
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}", exc_info=True)
        return templates.TemplateResponse("index.html", {"request": request, "results": None, "query": query, "search_type": search_type, "error": "Ошибка при выполнении поиска", "marketplace": marketplace})

@app.post("/api/search-all")
async def api_search_all(
    query: str = Form(...),
    search_type: str = Form('name'),
    scrolls: int = Form(1),
    max_cards: int = Form(3)
):
    logger.info(f"API-запрос поиска на всех МП: query={query}, type={search_type}, scrolls={scrolls}, max_cards={max_cards}")

    if search_type != "name":
        return JSONResponse({"error": "Поиск по всем МП доступен только для поиска по названию"}, status_code=400)

    marketplaces_to_search = ["ozon", "wildberries", "yandex"]
    results_all = []

    for mkt in marketplaces_to_search:
        parser_module_name = PARSERS.get(mkt.lower())
        if not parser_module_name:
            logger.error(f"Парсер для маркетплейса '{mkt}' не найден")
            continue

        parser_module = importlib.import_module(parser_module_name)

        if mkt == "ozon":
            parse_func = getattr(parser_module, "async_parse_ozon_search", None)
        else:
            parse_func = getattr(parser_module, "async_parse_search", None)

        if not parse_func:
            logger.error(f"Функция парсинга не найдена в модуле {parser_module_name}")
            continue

        await parse_func(query, scrolls, max_cards, search_type)

        service_instance = ParserService()
        parsed_results = service_instance.process_products()

        for res in parsed_results:
            res["marketplace"] = mkt.capitalize()

        results_all.extend(parsed_results)

    logger.info(f"🎉 API поиск на всех МП завершён, найдено всего: {len(results_all)} товаров")
    return JSONResponse({"success": True, "total_products": len(results_all), "results": results_all})

@app.get("/last-results-parse", response_class=HTMLResponse)
async def last_results_parse(request: Request, marketplace: str = "ozon"):
    logger.info(f"Запрошен перепарсинг последнего результата для маркетплейса: {marketplace}")

    if marketplace.lower() != "ozon":
        error_msg = "Перепарсинг поддерживается только для маркетплейса Ozon"
        logger.error(error_msg)
        return templates.TemplateResponse("index.html", {"request": request, "results": None, "error": error_msg, "query": "", "search_type": "name", "marketplace": marketplace})

    try:
        service_instance = ParserService()
        parsed_results = service_instance.process_products()

        for res in parsed_results:
            logger.debug(f"Результат парсинга: {res}")

        logger.info(f"Перепарсинг завершён: найдено {len(parsed_results)} продуктов")

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": parsed_results,
                "query": "",
                "search_type": "name",
                "marketplace": marketplace
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при перепарсинге последнего результата: {e}", exc_info=True)
        return templates.TemplateResponse("index.html", {"request": request, "results": None, "error": "Ошибка при перепарсинге последнего результата", "query": "", "search_type": "name", "marketplace": marketplace})

@app.on_event("startup")
async def startup_event():
    logger.info("⚡ [INFO] 🚀 Сервер запущен и готов принимать запросы")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("⚡ [INFO] 🛑 Сервер остановлен")

