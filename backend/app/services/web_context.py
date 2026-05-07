from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests

from app.config import settings


SYSTEM_CONTEXT = """
Urbanest IA es un asistente inmobiliario local para arriendos en Cartagena.
El backend decide que puede consultar la IA: Ollama no navega por internet por su cuenta.
Para busquedas de inmuebles, el backend usa scrapers propios y fuentes permitidas.
Para preguntas generales o actuales, el backend puede hacer busqueda web y entregarle extractos a Ollama como contexto.
Fuentes configuradas:
- FincaRaiz: spider Scrapy fincaraiz.
- Metrocuadrado: spider Scrapy metrocuadrado.
- OLX Colombia: spider Scrapy olx.
- Facebook Marketplace: no se consulta automaticamente porque requiere login y no se automatiza evasion.
Si el scraping real falla, esta desactivado o una fuente no entrega datos utilizables, el sistema devuelve cero resultados en vez de inventar anuncios.
El backend respeta la configuracion ENABLE_LIVE_SCRAPING, delays y evita automatizar logins, captchas o evasiones.
""".strip()


FUNCTION_QUESTION_HINTS = [
    "como funciona",
    "cómo funciona",
    "que haces",
    "qué haces",
    "quien eres",
    "quién eres",
    "de donde",
    "de dónde",
    "donde buscas",
    "dónde buscas",
    "fuentes",
    "paginas",
    "páginas",
    "scraper",
    "scrapers",
    "ollama",
    "modelo",
    "model",
    "llm",
    "ia",
    "internet",
    "informacion",
    "información",
    "datos",
    "actual",
    "actualidad",
    "reciente",
    "recientes",
    "hoy",
    "noticias",
    "buscar en internet",
    "busca en internet",
    "web",
]

WEB_SEARCH_HINTS = [
    "internet",
    "actual",
    "actualidad",
    "reciente",
    "recientes",
    "hoy",
    "noticias",
    "web",
    "google",
    "buscar",
    "busca",
    "consulta",
]


def _allowed_domains() -> list[str]:
    return [domain.strip().lower() for domain in settings.allowed_web_domains.split(",") if domain.strip()]


def is_allowed_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return False
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in _allowed_domains())


def extract_urls(message: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)>\]]+", message)
    return [url.rstrip(".,;") for url in urls]


def should_search_web(message: str) -> bool:
    lowered = message.lower()
    return settings.enable_general_web_search and any(hint in lowered for hint in WEB_SEARCH_HINTS)


def clean_web_search_query(message: str) -> str:
    query = message.lower()
    for phrase in (
        "busca en internet",
        "buscar en internet",
        "consulta en internet",
        "busca",
        "buscar",
        "consulta",
        "en internet",
        "en la web",
        "resume lo importante",
        "resumen",
    ):
        query = query.replace(phrase, " ")
    query = re.sub(r"\s+", " ", query).strip()
    return query or message


def is_function_question(message: str) -> bool:
    lowered = message.lower()
    return any(hint in lowered for hint in FUNCTION_QUESTION_HINTS)


def _clean_result_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.query:
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return url


def _strip_tags(value: str) -> str:
    value = re.sub(r"<(script|style).*?</\1>", " ", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def search_web(message: str) -> list[dict[str, str]]:
    if not settings.enable_general_web_search:
        return []

    try:
        response = requests.get(
            settings.web_search_endpoint,
            params={"q": clean_web_search_query(message)},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 UrbanestIA/0.1",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.5",
            },
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return []

    html = response.text
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
        flags=re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        url = _clean_result_url(unescape(match.group("url")))
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        results.append(
            {
                "title": _strip_tags(match.group("title"))[:180],
                "url": url,
                "snippet": _strip_tags(match.group("snippet"))[:500],
            }
        )
        if len(results) >= settings.web_search_max_results:
            break

    return results


def format_web_results_context(results: list[dict[str, str]]) -> str:
    lines = [
        f"{index}. {item['title']}\nURL: {item['url']}\nExtracto: {item['snippet']}"
        for index, item in enumerate(results, start=1)
    ]
    return "Resultados de busqueda web entregados por backend:\n" + "\n\n".join(lines)


def build_web_search_answer(results: list[dict[str, str]]) -> str:
    if not results:
        return (
            "Intenté consultar la web desde el backend, pero no encontré resultados legibles en este momento. "
            "Puedes probar con una consulta más específica o pegar una URL para revisarla."
        )

    lines = ["Encontré estos resultados web relevantes:"]
    for index, item in enumerate(results[: settings.web_search_max_results], start=1):
        snippet = item["snippet"].rstrip(".")
        lines.append(f"{index}. {item['title']}: {snippet}.")
        lines.append(f"Fuente: {item['url']}")
        lines.append("")

    lines.append(
        "En conjunto, los resultados apuntan a valorización, mayor uso de datos públicos para decidir inversiones "
        "y seguimiento de la dinámica de ventas en Cartagena. Conviene revisar las fuentes completas antes de tomar una decisión."
    )

    return "\n".join(lines)


def build_function_answer() -> str:
    return (
        f"Modelo Ollama configurado actualmente: {settings.ollama_model}. "
        "Busco la información desde el backend, no directamente desde Ollama. "
        "El flujo es así: primero interpreto tu mensaje como criterios de búsqueda; luego el backend consulta "
        "fuentes permitidas mediante scrapers propios: FincaRaiz, Metrocuadrado y OLX. "
        "Facebook Marketplace no se consulta automáticamente porque no automatizamos login ni evasión. "
        "Después normalizo los anuncios, filtro por ciudad, precio, habitaciones y baños, guardo el lote y le paso a Ollama "
        "solo el contexto aprobado para que responda, compare y explique. Para preguntas generales, el backend también "
        "puede hacer búsqueda web y pasarle esos resultados a Ollama como contexto. "
        "Si una fuente real no responde o el scraping está desactivado, devuelvo cero resultados en vez de inventar anuncios."
    )


def fetch_allowed_page_summary(url: str) -> str | None:
    if not settings.enable_web_context or not is_allowed_url(url):
        return None

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "UrbanestIA/0.1 (+local development; responsible context fetch)",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.5",
            },
            timeout=8,
            allow_redirects=True,
        )
        response.raise_for_status()
    except Exception:
        return None

    content_type = response.headers.get("content-type", "")
    if "text" not in content_type and "html" not in content_type:
        return None

    text = re.sub(r"<(script|style).*?</\1>", " ", response.text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return f"URL: {url}\nExtracto visible permitido: {text[:1200]}"


def build_web_context(
    message: str,
    properties: list[dict[str, Any]] | None = None,
    web_results: list[dict[str, str]] | None = None,
) -> str:
    context_blocks = [
        SYSTEM_CONTEXT,
        f"Modelo Ollama configurado para responder: {settings.ollama_model}.",
    ]

    if should_search_web(message):
        results = web_results if web_results is not None else search_web(message)
        if results:
            context_blocks.append(format_web_results_context(results))
        else:
            context_blocks.append("Busqueda web solicitada, pero no hubo resultados legibles desde el backend.")

    urls = extract_urls(message)
    if properties:
        mentioned_sources = [
            item.get("url")
            for item in properties[:3]
            if item.get("url")
        ]
        urls.extend(str(url) for url in mentioned_sources)

    seen: set[str] = set()
    page_blocks: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        summary = fetch_allowed_page_summary(url)
        if summary:
            page_blocks.append(summary)
        elif is_allowed_url(url):
            page_blocks.append(f"URL permitida pero no legible en este momento: {url}")
        else:
            page_blocks.append(f"URL no permitida por el backend: {url}")

    if page_blocks:
        context_blocks.append("Contexto web aprobado por backend:\n" + "\n\n".join(page_blocks[:3]))

    return "\n\n".join(context_blocks)
