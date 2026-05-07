import json
import re

import scrapy

from scraper.normalizer import build_fincaraiz_search_url


DETAIL_LINK_PATTERN = re.compile(r"/(?:apartamento|casa|apartaestudio)-en-arriendo-[^\"?#]+/\d+")


class FincaRaizSpider(scrapy.Spider):
    name = "fincaraiz"
    allowed_domains = ["fincaraiz.com.co"]

    def __init__(self, query_json="{}", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = json.loads(query_json)

    def start_requests(self):
        url = build_fincaraiz_search_url(self.query)
        yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        yielded_urls = set()

        for item in _extract_next_data_items(response):
            listing = _serialize_next_data_item(item, response, self.query)
            if not listing or listing["url"] in yielded_urls:
                continue
            yielded_urls.add(listing["url"])
            yield listing

        for listing in _extract_visible_card_items(response, self.query):
            if listing["url"] in yielded_urls:
                continue
            yielded_urls.add(listing["url"])
            yield listing


def _to_int(value):
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits.isdigit() else None


def _area_to_float(value):
    if not value:
        return None
    match = re.search(r"(\d+(?:[\.,]\d+)?)", str(value))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _first_location_name(locations: dict, key: str) -> str | None:
    values = locations.get(key) or []
    if isinstance(values, list) and values:
        return values[0].get("name")
    return None


def _detail_href(value: str | None) -> str | None:
    if not value:
        return None
    found = DETAIL_LINK_PATTERN.search(value)
    return found.group(0) if found else None


def _extract_next_data_items(response):
    next_data = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    if not next_data:
        return []

    try:
        payload = json.loads(next_data)
    except Exception:
        return []

    return (
        payload.get("props", {})
        .get("pageProps", {})
        .get("fetchResult", {})
        .get("searchFast", {})
        .get("data", [])
    ) or []


def _serialize_next_data_item(item: dict, response, query: dict) -> dict | None:
    href = _detail_href(item.get("link"))
    if not href:
        return None

    technical_sheet = {
        entry.get("field"): entry.get("value")
        for entry in item.get("technicalSheet", [])
        if isinstance(entry, dict)
    }
    locations = item.get("locations") or {}
    location_main = locations.get("location_main") or {}
    zone = (
        _first_location_name(locations, "neighbourhood")
        or location_main.get("name")
    )
    image_url = item.get("img")
    if not image_url and item.get("images"):
        image_url = (item["images"][0] or {}).get("image")

    return {
        "title": item.get("title") or "Inmueble en arriendo",
        "description": item.get("description"),
        "city": _first_location_name(locations, "city") or query.get("city", "Cartagena"),
        "zone": zone,
        "neighborhood": zone,
        "property_type": technical_sheet.get("property_type_name") or (item.get("property_type") or {}).get("name"),
        "price": (item.get("price") or {}).get("amount"),
        "bedrooms": _to_int(technical_sheet.get("bedrooms") or item.get("bedrooms")),
        "bathrooms": _to_int(technical_sheet.get("bathrooms") or item.get("bathrooms")),
        "area_m2": _area_to_float(technical_sheet.get("m2Built") or technical_sheet.get("m2apto") or item.get("m2")),
        "source": "FincaRaiz",
        "url": response.urljoin(href),
        "image_url": image_url,
    }


def _extract_visible_card_items(response, query: dict):
    for card in response.css("div.listingCard")[:20]:
        href = _detail_href(card.css("a[href*='-en-arriendo']::attr(href)").get())
        if not href:
            continue

        title = card.css("a.lc-data::attr(title)").get()
        price = card.css("p.main-price::text").get()
        location = _clean_text(" ".join(card.css("strong.lc-location *::text, strong.lc-location::text").getall()))
        card_text = _clean_text(" ".join(card.css("::text").getall()))
        typology_values = [
            _clean_text(value)
            for value in card.css(".lc-typologyTag__item::text, .lc-typologyTag__item *::text").getall()
            if _clean_text(value)
        ]
        typology_text = " ".join(typology_values) or card_text

        yield {
            "title": title or location or "Inmueble en arriendo",
            "description": location or title or "Inmueble publicado en FincaRaiz.",
            "city": query.get("city", "Cartagena"),
            "zone": None,
            "neighborhood": None,
            "property_type": "apartamento" if "apartamento" in href else "casa",
            "price_text": price,
            "bedrooms": _to_int(_match_first(r"(\d+)\s*(?:hab|habitacion)", typology_text.lower())),
            "bathrooms": _to_int(_match_first(r"(\d+)\s*(?:baño|ban[oó])", typology_text.lower())),
            "area_m2": _area_to_float(_match_first(r"(\d+(?:[\.,]\d+)?)\s*m", typology_text.lower())),
            "source": "FincaRaiz",
            "url": response.urljoin(href),
            "image_url": card.css("img::attr(src)").get(),
        }


def _match_first(pattern: str, value: str) -> str | None:
    found = re.search(pattern, value)
    return found.group(1) if found else None
