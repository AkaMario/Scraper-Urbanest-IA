import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_ROOT = PROJECT_ROOT / "scraper"


def _url_slug(value: str) -> str:
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    slug = value.strip().lower()
    for original, replacement in replacements.items():
        slug = slug.replace(original, replacement)
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")


def _fincaraiz_property_segment(property_type: str | None) -> str:
    normalized = (property_type or "").strip().lower()
    if normalized in {"casa", "casas"}:
        return "casas"
    if normalized in {"apartamento", "apartamentos", "apartaestudio", "apartaestudios"}:
        return "apartamentos"
    return "casas-y-apartamentos"


def normalize_property_type(property_type: str | None) -> str | None:
    normalized = (property_type or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"apartamento", "apartamentos"}:
        return "apartamento"
    if normalized in {"apartaestudio", "apartaestudios"}:
        return "apartaestudio"
    if normalized in {"casa", "casas"}:
        return "casa"
    return normalized


def build_fincaraiz_search_url(query: dict) -> str:
    city = _url_slug(query.get("city") or "Cartagena")
    property_segment = _fincaraiz_property_segment(query.get("property_type"))
    path_parts = ["https://www.fincaraiz.com.co", "arriendo", property_segment]

    path_parts.append(city)

    if query.get("price_min"):
        path_parts.append(f"desde-{int(query['price_min'])}")
    if query.get("price_max"):
        path_parts.append(f"hasta-{int(query['price_max'])}")

    return "/".join(path_parts) + "?&IDmoneda=4"


def build_source_search_url(source: str, query: dict) -> str:
    city = (query.get("city") or "Cartagena").strip()
    city_slug = quote_plus(city.lower())
    source_key = source.lower()

    if "finca" in source_key:
        return build_fincaraiz_search_url(query)
    if "metro" in source_key:
        return f"https://www.metrocuadrado.com/arriendo/{city_slug}/"
    if "olx" in source_key:
        return f"https://www.olx.com.co/inmuebles_c378/{city_slug.lower()}"
    if "facebook" in source_key:
        return f"https://www.facebook.com/marketplace/cartagena/search/?query={quote_plus(f'arriendo {city}')}"
    return build_fincaraiz_search_url(query)


def _price_from_text(price_text: str | None, fallback: int) -> int:
    if not price_text:
        return fallback
    digits = re.sub(r"[^\d]", "", price_text)
    if digits.isdigit():
        return int(digits)
    return fallback


def normalize_property(item: dict, query: dict) -> dict:
    default_price = int(query.get("price_max") or query.get("price_min") or 2_000_000)
    zone = item.get("zone") or item.get("neighborhood") or "Cartagena"
    property_type = normalize_property_type(item.get("property_type") or query.get("property_type")) or "apartamento"
    return {
        "title": item.get("title") or f"Inmueble en {zone}",
        "description": item.get("description") or "Propiedad listada en arriendo en Cartagena.",
        "city": item.get("city") or query.get("city") or "Cartagena",
        "zone": zone,
        "neighborhood": item.get("neighborhood") or zone,
        "property_type": property_type,
        "price": int(item.get("price") or _price_from_text(item.get("price_text"), default_price)),
        "bedrooms": item.get("bedrooms") if item.get("bedrooms") is not None else query.get("bedrooms"),
        "bathrooms": item.get("bathrooms") if item.get("bathrooms") is not None else query.get("bathrooms"),
        "area_m2": item.get("area_m2"),
        "source": item.get("source") or "Mock",
        "url": item.get("url") or build_source_search_url(item.get("source") or "FincaRaiz", query),
        "image_url": item.get("image_url"),
        "scraped_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }


def property_matches_query(property_item: dict, query: dict) -> bool:
    if query.get("price_min") and property_item.get("price") and property_item["price"] < int(query["price_min"]):
        return False
    if query.get("price_max") and property_item.get("price") and property_item["price"] > int(query["price_max"]):
        return False
    if query.get("bedrooms") and property_item.get("bedrooms") and int(property_item["bedrooms"]) < int(query["bedrooms"]):
        return False
    if query.get("bathrooms") and property_item.get("bathrooms") and int(property_item["bathrooms"]) < int(query["bathrooms"]):
        return False
    return True


def _run_spider(spider_name: str, query: dict) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        output_path = temp_file.name

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{PROJECT_ROOT / 'backend'}:{env.get('PYTHONPATH', '')}"

    try:
        spider_timeout = {"fincaraiz": 8, "metrocuadrado": 8, "olx": 4}.get(spider_name, 6)
        subprocess.run(
            [
                "scrapy",
                "crawl",
                spider_name,
                "-a",
                f"query_json={json.dumps(query)}",
                "-O",
                output_path,
            ],
            cwd=str(SCRAPER_ROOT),
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=spider_timeout,
        )
        raw = Path(output_path).read_text(encoding="utf-8").strip()
        if not raw:
            return []
        return json.loads(raw)
    except Exception:
        return []
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def run_live_property_search(query: dict) -> list[dict]:
    live_results: list[dict] = []
    seen_urls: set[str] = set()
    spider_names = ("fincaraiz", "metrocuadrado", "olx")

    with ThreadPoolExecutor(max_workers=len(spider_names)) as executor:
        future_map = {
            executor.submit(_run_spider, spider_name, query): spider_name
            for spider_name in spider_names
        }
        for future in as_completed(future_map):
            for item in future.result():
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                if item.get("title") in {"Inmueble en arriendo", "Inmueble OLX"} and item.get("url") == build_source_search_url(item.get("source", ""), query):
                    continue
                live_results.append(item)

    return live_results


def build_source_weight(source: str) -> int:
    mapping = {
        "FincaRaiz": 10,
        "Metrocuadrado": 9,
        "OLX": 8,
    }
    return mapping.get(source, 1)


def run_property_search(query: dict) -> list[dict]:
    delay = float(os.getenv("SCRAPING_DELAY_SECONDS", "1"))
    time.sleep(max(delay, 0.5))

    enable_live_scraping = os.getenv("ENABLE_LIVE_SCRAPING", "true").lower() == "true"
    if enable_live_scraping:
        live_results = run_live_property_search(query)
        if live_results:
            live_results.sort(key=lambda item: build_source_weight(item.get("source", "")), reverse=True)
            return live_results

    return []
