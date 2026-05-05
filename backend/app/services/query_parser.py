import re
from typing import Any

from app.ollama_client import parse_query_with_ollama
from app.services.web_context import is_function_question


ZONE_CANDIDATES = [
    "manga",
    "bocagrande",
    "castillogrande",
    "crespo",
    "serena del mar",
    "marbella",
    "el laguito",
    "pie de la popa",
    "alto bosque",
    "blas de lezo",
    "torices",
]


PROPERTY_TYPES = {
    "apartamento": "apartamento",
    "apartamentos": "apartamento",
    "casa": "casa",
    "casas": "casa",
    "apartaestudio": "apartaestudio",
    "local": "local",
}

SEARCH_HINTS = [
    "busca",
    "buscar",
    "quiero",
    "necesito",
    "muestrame",
    "muéstrame",
    "encuentra",
    "arriendo",
    "alquiler",
    "apartamento",
    "apartamentos",
    "casa",
    "casas",
    "apartaestudio",
    "habitacion",
    "habitaciones",
    "alcoba",
    "alcobas",
    "baño",
    "baños",
    "bano",
    "banos",
    "millones",
    "millon",
    "hasta",
    "entre",
    "presupuesto",
    "cartagena",
]

GREETING_MESSAGES = {
    "hola",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "hey",
    "hi",
}

EXPLANATION_HINTS = [
    "que es",
    "qué es",
    "explica",
    "explicame",
    "explícame",
    "define",
    "definicion",
    "definición",
    "diferencia",
    "compara",
    "comparar",
    "recomienda",
    "recomendacion",
    "recomendación",
    "consejo",
    "aconseja",
    "como funciona",
    "cómo funciona",
]


def _extract_price_values(message: str) -> list[int]:
    normalized = (
        message.lower()
        .replace(",", ".")
        .replace("millones", "millon")
        .replace("millón", "millon")
        .replace("millones.", "millon")
    )
    values: list[int] = []
    for match in re.findall(r"(\d+(?:\.\d+)?)\s*millon", normalized):
        values.append(int(float(match) * 1_000_000))
    for match in re.findall(r"(\d+(?:\.\d+)?)\s*mil\b", normalized):
        values.append(int(float(match) * 1_000))
    for match in re.findall(r"\$\s*([\d\.]+)", normalized):
        clean = match.replace(".", "")
        if clean.isdigit():
            values.append(int(clean))
    for match in re.findall(r"(\d{6,8})", normalized):
        values.append(int(match))
    return sorted(set(values))


def _extract_first_int(pattern: str, message: str) -> int | None:
    found = re.search(pattern, message.lower())
    return int(found.group(1)) if found else None


def _contains_term(message: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", message))


def _extract_property_type(message: str) -> str | None:
    return next(
        (normalized for token, normalized in PROPERTY_TYPES.items() if _contains_term(message, token)),
        None,
    )


def fallback_parse_query(message: str) -> dict[str, Any]:
    lowered = message.lower()
    prices = _extract_price_values(lowered)
    zone = next((candidate.title() for candidate in ZONE_CANDIDATES if candidate in lowered), None)
    if "cualquier barrio" in lowered or "cualquier zona" in lowered or "en cualquier barrio" in lowered:
        zone = None
    property_type = _extract_property_type(lowered) or "apartamento"

    bedrooms = _extract_first_int(r"(\d+)\s*habitacion", lowered) or _extract_first_int(r"(\d+)\s*alcoba", lowered)
    bathrooms = _extract_first_int(r"(\d+)\s*ba", lowered)

    if "hasta" in lowered and prices:
        price_min, price_max = None, prices[-1]
    elif "entre" in lowered and len(prices) >= 2:
        price_min, price_max = prices[0], prices[1]
    elif len(prices) >= 2:
        price_min, price_max = prices[0], prices[1]
    elif len(prices) == 1:
        price_min, price_max = None, prices[0]
    else:
        price_min, price_max = None, None

    keywords = []
    for token in ["arriendo", "amoblado", "balcon", "vista al mar", "parqueadero", "mascotas"]:
        if token in lowered:
            keywords.append(token)

    return {
        "city": "Cartagena",
        "zone": zone,
        "neighborhood": zone,
        "property_type": property_type,
        "price_min": price_min,
        "price_max": price_max,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "keywords": keywords,
    }


def should_skip_ollama_for_query(message: str, fallback_payload: dict[str, Any]) -> bool:
    lowered = message.lower()
    if "cualquier barrio" in lowered or "cualquier zona" in lowered:
        return True

    extracted_signals = [
        fallback_payload.get("zone"),
        fallback_payload.get("price_min"),
        fallback_payload.get("price_max"),
        fallback_payload.get("bedrooms"),
        fallback_payload.get("bathrooms"),
    ]
    if any(value is not None for value in extracted_signals):
        return True

    return bool(fallback_payload.get("keywords"))


def normalize_query_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = fallback_parse_query("")
    normalized.update({key: value for key, value in payload.items() if key in normalized})
    normalized["city"] = normalized.get("city") or "Cartagena"
    if normalized.get("zone") and not normalized.get("neighborhood"):
        normalized["neighborhood"] = normalized["zone"]
    keywords = normalized.get("keywords") or []
    normalized["keywords"] = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
    return normalized


def is_search_request(message: str) -> bool:
    lowered = message.lower().strip()
    if not lowered:
        return False
    if lowered in GREETING_MESSAGES:
        return False
    if any(hint in lowered for hint in EXPLANATION_HINTS) and not any(
        action in lowered for action in ("busca", "buscar", "encuentra", "muestrame", "muéstrame", "quiero", "necesito")
    ):
        return False
    if is_function_question(lowered):
        search_action = any(
            hint in lowered
            for hint in ("busca", "buscar", "encuentra", "muestrame", "muéstrame", "quiero", "necesito")
        )
        concrete_filters = bool(
            re.search(r"\d+\s*(millon|millones|habitacion|habitaciones|ba|bano|banos)", lowered)
            or re.search(r"\$\s*[\d\.]+|\d{6,8}", lowered)
            or any(candidate in lowered for candidate in ZONE_CANDIDATES)
        )
        if not search_action or not concrete_filters:
            return False

    score = 0
    if any(hint in lowered for hint in SEARCH_HINTS):
        score += 2
    if any(candidate in lowered for candidate in ZONE_CANDIDATES):
        score += 1
    if _extract_property_type(lowered):
        score += 1
    if re.search(r"\d+\s*(millon|millones|habitacion|habitaciones|ba|bano|banos)", lowered):
        score += 2
    if re.search(r"\$\s*[\d\.]+|\d{6,8}", lowered):
        score += 1

    return score >= 2


def has_concrete_search_filters(message: str) -> bool:
    lowered = message.lower().strip()
    if not lowered:
        return False

    return bool(
        re.search(r"\d+\s*(millon|millones|habitacion|habitaciones|ba|bano|banos)", lowered)
        or re.search(r"\$\s*[\d\.]+|\d{6,8}", lowered)
        or any(candidate in lowered for candidate in ZONE_CANDIDATES)
        or _extract_property_type(lowered)
    )


def is_greeting_message(message: str) -> bool:
    return message.lower().strip() in GREETING_MESSAGES


def parse_user_query(message: str) -> tuple[dict[str, Any], str]:
    fallback_payload = fallback_parse_query(message)
    if should_skip_ollama_for_query(message, fallback_payload):
        return fallback_payload, "fallback-fast"

    try:
        ollama_payload = parse_query_with_ollama(message)
        return normalize_query_payload(ollama_payload), "ollama"
    except Exception:
        return fallback_payload, "fallback"
