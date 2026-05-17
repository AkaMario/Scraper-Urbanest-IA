import os
import re
import subprocess
import tempfile
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import json

from app.services.cartagena_locations import location_search_terms, normalize_neighborhood


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_ROOT = PROJECT_ROOT / "scraper"
logger = logging.getLogger(__name__)


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


def _search_text(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for original, replacement in replacements.items():
        normalized = normalized.replace(original, replacement)
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


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
    zone = _url_slug(query.get("zone") or query.get("neighborhood") or "")
    property_segment = _fincaraiz_property_segment(query.get("property_type"))
    operation = "venta" if query.get("operation") == "sale" else "arriendo"
    path_parts = ["https://www.fincaraiz.com.co", operation, property_segment]

    if zone:
        path_parts.append(zone)
    path_parts.append(city)

    if query.get("price_min"):
        path_parts.append(f"desde-{int(query['price_min'])}")
    if query.get("price_max"):
        path_parts.append(f"hasta-{int(query['price_max'])}")

    return "/".join(path_parts) + "?&IDmoneda=4"


def build_source_search_url(source: str, query: dict) -> str:
    city = (query.get("city") or "Cartagena").strip()
    zone = (query.get("zone") or query.get("neighborhood") or "").strip()
    city_slug = quote_plus(city.lower())
    zone_slug = quote_plus(zone.lower())
    source_key = source.lower()

    if "finca" in source_key:
        return build_fincaraiz_search_url(query)
    if "metro" in source_key:
        operation = "venta" if query.get("operation") == "sale" else "arriendo"
        if zone:
            return f"https://www.metrocuadrado.com/{operation}/{city_slug}/{zone_slug}/"
        return f"https://www.metrocuadrado.com/{operation}/{city_slug}/"
    if "olx" in source_key:
        if zone:
            return f"https://www.olx.com.co/inmuebles_c378/{zone_slug}"
        return f"https://www.olx.com.co/inmuebles_c378/{city_slug.lower()}"
    if "facebook" in source_key:
        search_scope = f"{zone} {city}" if zone else city
        operation_text = "venta" if query.get("operation") == "sale" else "arriendo"
        return f"https://www.facebook.com/marketplace/cartagena/search/?query={quote_plus(f'{operation_text} {search_scope}')}"
    return build_fincaraiz_search_url(query)


def _price_from_text(price_text: str | None, fallback: int) -> int:
    if not price_text:
        return fallback
    digits = re.sub(r"[^\d]", "", price_text)
    if digits.isdigit():
        return int(digits)
    return fallback


def _normalize_features(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        raw_values = re.split(r"[,;|\n]+", value)
    elif isinstance(value, list):
        raw_values = value
    else:
        return []

    features: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = re.sub(r"\s+", " ", str(item)).strip(" .:-")
        if not text or len(text) < 3:
            continue
        key = _search_text(text)
        if key in seen:
            continue
        seen.add(key)
        features.append(text[:80])
        if len(features) >= 12:
            break
    return features


def normalize_property(item: dict, query: dict) -> dict:
    default_price = int(query.get("price_max") or query.get("price_min") or 2_000_000)
    raw_zone = item.get("zone") or item.get("neighborhood") or "Cartagena"
    zone = normalize_neighborhood(raw_zone) or raw_zone
    query_zone = normalize_neighborhood(query.get("zone") or query.get("neighborhood"))
    query_zone_text = _search_text(query_zone)
    listing_text = _search_text(
        " ".join(str(item.get(field) or "") for field in ("title", "description", "url"))
    )
    if query_zone and query_zone_text and query_zone_text in listing_text:
        zone = query_zone
    property_type = normalize_property_type(item.get("property_type") or query.get("property_type")) or "apartamento"
    return {
        "title": item.get("title") or f"Inmueble en {zone}",
        "description": item.get("description") or "Propiedad listada en portales inmobiliarios.",
        "city": item.get("city") or query.get("city") or "Cartagena",
        "zone": zone,
        "neighborhood": normalize_neighborhood(item.get("neighborhood") or zone) or item.get("neighborhood") or zone,
        "property_type": property_type,
        "operation": item.get("operation") or query.get("operation") or "rent",
        "price": int(item.get("price") or _price_from_text(item.get("price_text"), default_price)),
        "bedrooms": item.get("bedrooms") if item.get("bedrooms") is not None else query.get("bedrooms"),
        "bathrooms": item.get("bathrooms") if item.get("bathrooms") is not None else query.get("bathrooms"),
        "parking_spaces": item.get("parking_spaces"),
        "stratum": item.get("stratum"),
        "area_m2": item.get("area_m2"),
        "features": _normalize_features(item.get("features")),
        "source": item.get("source") or "Mock",
        "url": item.get("url") or build_source_search_url(item.get("source") or "FincaRaiz", query),
        "image_url": item.get("image_url"),
        "image_urls": item.get("image_urls") or ([item.get("image_url")] if item.get("image_url") else []),
        "raw_text": item.get("raw_text"),
        "raw_data": item,
        "scraped_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }


def property_matches_query(property_item: dict, query: dict) -> bool:
    requested_zones = location_search_terms(query.get("zone") or query.get("neighborhood"))
    if query.get("accepted_zones"):
        requested_zones = [str(zone) for zone in query.get("accepted_zones") or [] if str(zone).strip()]
    requested_zone_terms = [_search_text(zone) for zone in requested_zones if _search_text(zone)]
    if requested_zone_terms:
        haystack = _search_text(
            " ".join(
                str(property_item.get(field) or "")
                for field in ("title", "description", "url")
            )
        )
        location_text = _search_text(
            " ".join(str(property_item.get(field) or "") for field in ("zone", "neighborhood"))
        )
        location_tokens = set(location_text.split())
        known_location = bool(location_tokens) and not location_tokens <= {"cartagena"}
        if known_location and not any(term in location_text or term in haystack for term in requested_zone_terms):
            return False
        if not known_location:
            if not any(term in haystack for term in requested_zone_terms):
                return False
    if query.get("price_min") and property_item.get("price") and property_item["price"] < int(query["price_min"]):
        return False
    if query.get("price_max") and property_item.get("price") and property_item["price"] > int(query["price_max"]):
        return False
    if query.get("bedrooms") and property_item.get("bedrooms") and int(property_item["bedrooms"]) < int(query["bedrooms"]):
        return False
    if query.get("bathrooms") and property_item.get("bathrooms") and int(property_item["bathrooms"]) < int(query["bathrooms"]):
        return False
    if query.get("operation") and property_item.get("operation") and property_item["operation"] != query["operation"]:
        return False
    return True


def _run_spider(spider_name: str, query: dict) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        output_path = temp_file.name

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{PROJECT_ROOT / 'backend'}:{env.get('PYTHONPATH', '')}"

    try:
        spider_timeout = {"fincaraiz": 60, "metrocuadrado": 45}.get(spider_name, 30)
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
    except Exception as exc:
        logger.exception("Spider %s failed for query %s: %s", spider_name, query, exc)
        return []
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def run_live_property_search(query: dict) -> list[dict]:
    live_results: list[dict] = []
    seen_urls: set[str] = set()
    source_spiders = {
        "FincaRaiz": "fincaraiz",
        "Metrocuadrado": "metrocuadrado",
    }
    requested_sources = [
        source
        for source in query.get("sources") or source_spiders
        if source in source_spiders
    ]
    spider_names = tuple(source_spiders[source] for source in requested_sources) or tuple(source_spiders.values())

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
