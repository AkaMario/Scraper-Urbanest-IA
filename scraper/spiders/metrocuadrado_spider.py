import json
import re
from urllib.parse import quote_plus

import scrapy


class MetroCuadradoSpider(scrapy.Spider):
    name = "metrocuadrado"
    allowed_domains = ["metrocuadrado.com"]

    def __init__(self, query_json="{}", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = json.loads(query_json)

    def start_requests(self):
        city = quote_plus((self.query.get("city") or "Cartagena").lower())
        zone = quote_plus((self.query.get("zone") or self.query.get("neighborhood") or "").lower())
        url = f"https://www.metrocuadrado.com/arriendo/{city}/{zone}/" if zone else f"https://www.metrocuadrado.com/arriendo/{city}/"
        yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        yielded_count = 0
        script_chunks = re.findall(r"<script>(.*?)</script>", response.text, re.S)
        for chunk in script_chunks:
            if "initialResults" not in chunk:
                continue

            decoded = bytes(chunk, "utf-8").decode("unicode_escape")
            items = _extract_results_array(decoded)
            if not items:
                continue

            for item in items[:20]:
                listing = {
                    "title": item.get("title") or "Inmueble en arriendo",
                    "description": item.get("sector") or item.get("subtitle") or item.get("title"),
                    "city": self.query.get("city", "Cartagena"),
                    "zone": item.get("mnombrecomunbarrio") or item.get("mbarrio"),
                    "neighborhood": item.get("mnombrecomunbarrio") or item.get("mbarrio"),
                    "property_type": (item.get("mtipoinmueble") or {}).get("nombre"),
                    "price": item.get("mvalorarriendo") or item.get("mvalorventa"),
                    "bedrooms": _to_int(item.get("mnrocuartos")),
                    "bathrooms": _to_int(item.get("mnrobanos")),
                    "area_m2": _to_float(item.get("marea") or item.get("mareac") or item.get("areaconstruida")),
                    "source": "Metrocuadrado",
                    "url": response.urljoin(item.get("link") or ""),
                    "image_url": item.get("imageLink"),
                }
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
            return

        for card in response.css("article, div[class*='property']")[:10]:
            title = "".join(card.css("h2 *::text, h3 *::text").getall()).strip()
            href = card.css("a::attr(href)").get()
            listing = {
                "title": title or "Inmueble en arriendo",
                "description": " ".join(card.css("p *::text").getall()).strip(),
                "city": self.query.get("city", "Cartagena"),
                "zone": None,
                "price_text": "".join(card.css("span *::text").getall()).strip(),
                "bedrooms": None,
                "bathrooms": None,
                "area_m2": None,
                "source": "Metrocuadrado",
                "url": response.urljoin(href) if href else response.url,
                "image_url": card.css("img::attr(src)").get(),
            }
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
    if value in (None, ""):
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits.isdigit() else None


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


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
        "[class*='caracter'] ::text, [class*='Caracter'] ::text, "
        "li::text"
    ).getall()

    return {
        "description": description,
        "features": _unique_texts(feature_values, limit=12),
    }


def _extract_results_array(decoded_text: str):
    marker = '"results":['
    start = decoded_text.find(marker)
    if start == -1:
        return []

    i = start + len(marker) - 1
    depth = 0
    in_string = False
    escape = False

    for pos in range(i, len(decoded_text)):
        char = decoded_text[pos]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(decoded_text[i : pos + 1])
                except Exception:
                    return []

    return []
