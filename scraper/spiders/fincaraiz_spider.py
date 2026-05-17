import json
import re

import scrapy

from scraper.normalizer import build_fincaraiz_search_url


DETAIL_LINK_PATTERN = re.compile(r"/(?:apartamento|casa|apartaestudio)-en-(?:arriendo|venta)-[^\"?#]+/\d+")


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
        yielded_count = 0

        for item in _extract_next_data_items(response):
            listing = _serialize_next_data_item(item, response, self.query)
            if not listing or listing["url"] in yielded_urls:
                continue
            yielded_urls.add(listing["url"])
            yielded_count += 1
            yield scrapy.Request(
                listing["url"],
                callback=self.parse_detail,
                errback=self.detail_failed,
                meta={"listing": listing},
                dont_filter=True,
            )
            if yielded_count >= 12:
                return

        for listing in _extract_visible_card_items(response, self.query):
            if listing["url"] in yielded_urls:
                continue
            yielded_urls.add(listing["url"])
            yielded_count += 1
            yield scrapy.Request(
                listing["url"],
                callback=self.parse_detail,
                errback=self.detail_failed,
                meta={"listing": listing},
                dont_filter=True,
            )
            if yielded_count >= 12:
                return

    def parse_detail(self, response):
        listing = response.meta["listing"]
        detail_data = _extract_detail_data(response)
        yield {**listing, **detail_data}

    def detail_failed(self, failure):
        yield failure.request.meta["listing"]


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


def _unique_texts(values, limit=12):
    output = []
    seen = set()
    for value in values:
        text = _clean_text(value)
        key = text.lower()
        if not text or len(text) < 3 or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


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
        "operation": query.get("operation") or "rent",
        "price": (item.get("price") or {}).get("amount"),
        "bedrooms": _to_int(technical_sheet.get("bedrooms") or item.get("bedrooms")),
        "bathrooms": _to_int(technical_sheet.get("bathrooms") or item.get("bathrooms")),
        "parking_spaces": _to_int(technical_sheet.get("parking") or technical_sheet.get("garages") or item.get("garages")),
        "stratum": _to_int(technical_sheet.get("stratum") or technical_sheet.get("estrato")),
        "area_m2": _area_to_float(technical_sheet.get("m2Built") or technical_sheet.get("m2apto") or item.get("m2")),
        "source": "FincaRaiz",
        "url": response.urljoin(href),
        "image_url": image_url,
        "image_urls": [str((image or {}).get("image")) for image in item.get("images") or [] if (image or {}).get("image")],
        "raw_data": item,
    }


def _extract_visible_card_items(response, query: dict):
    for card in response.css("div.listingCard")[:20]:
        href = _detail_href(card.css("a[href*='-en-arriendo']::attr(href), a[href*='-en-venta']::attr(href)").get())
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
            "operation": query.get("operation") or "rent",
            "price_text": price,
            "bedrooms": _to_int(_match_first(r"(\d+)\s*(?:hab|habitacion)", typology_text.lower())),
            "bathrooms": _to_int(_match_first(r"(\d+)\s*(?:baño|ban[oó])", typology_text.lower())),
            "area_m2": _area_to_float(_match_first(r"(\d+(?:[\.,]\d+)?)\s*m", typology_text.lower())),
            "source": "FincaRaiz",
            "url": response.urljoin(href),
            "image_url": card.css("img::attr(src)").get(),
            "image_urls": [url for url in [card.css("img::attr(src)").get()] if url],
        }


def _extract_detail_data(response) -> dict:
    description_candidates = [
        response.css("meta[name='description']::attr(content)").get(),
        response.css("[class*='description']::text, [class*='Description']::text").get(),
        response.css("section p::text, main p::text").get(),
    ]
    description = next((_clean_text(item) for item in description_candidates if _clean_text(item)), None)
    page_text = _clean_text(" ".join(response.css("main ::text, body ::text").getall()))
    if (not description or len(description) < 80) and page_text:
        description = page_text[:500]

    feature_values = response.css(
        "[class*='feature'] ::text, [class*='Feature'] ::text, "
        "[class*='amenit'] ::text, [class*='Amenit'] ::text, "
        "[class*='characteristic'] ::text, [class*='Characteristic'] ::text, "
        "li::text"
    ).getall()

    json_features = []
    for script in response.css("script[type='application/ld+json']::text").getall():
        try:
            payload = json.loads(script)
        except Exception:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("amenityFeature", "description"):
                value = item.get(key)
                if isinstance(value, list):
                    json_features.extend(str(entry.get("name") or entry) for entry in value)
                elif value:
                    json_features.append(str(value))

    return {
        "description": description,
        "features": _unique_texts([*feature_values, *json_features], limit=12),
        "raw_text": page_text[:2000],
    }


def _match_first(pattern: str, value: str) -> str | None:
    found = re.search(pattern, value)
    return found.group(1) if found else None
