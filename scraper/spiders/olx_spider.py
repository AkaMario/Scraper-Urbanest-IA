import json
from urllib.parse import quote_plus

import scrapy


class OlxSpider(scrapy.Spider):
    name = "olx"
    allowed_domains = ["olx.com.co", "olx.com"]

    def __init__(self, query_json="{}", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = json.loads(query_json)

    def start_requests(self):
        zone = quote_plus(self.query.get("zone") or "cartagena")
        url = f"https://www.olx.com.co/inmuebles_c378/{zone}"
        yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        for card in response.css("li")[:10]:
            title = "".join(card.css("h6 *::text").getall()).strip()
            href = card.css("a::attr(href)").get()
            if not title and not href:
                continue
            yield {
                "title": title or "Inmueble OLX",
                "description": " ".join(card.css("span *::text").getall()).strip(),
                "city": self.query.get("city", "Cartagena"),
                "zone": self.query.get("zone"),
                "price_text": " ".join(card.css("p *::text").getall()).strip(),
                "bedrooms": None,
                "bathrooms": None,
                "area_m2": None,
                "source": "OLX",
                "url": response.urljoin(href) if href else response.url,
                "image_url": card.css("img::attr(src)").get(),
            }

    def errback_httpbin(self, failure):
        self.logger.warning("OLX no respondió o no resolvió: %s", failure)
