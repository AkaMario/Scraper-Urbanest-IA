import re
from typing import Any


def normalize_location_text(value: Any) -> str:
    normalized = str(value or "").strip().lower()
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


NEIGHBORHOOD_ALIASES = {
    "alto bosque": "Alto Bosque",
    "albornoz": "Albornoz",
    "amberes": "Amberes",
    "arroz barato": "Arroz Barato",
    "bellavista": "Bellavista",
    "blas de lezo": "Blas de Lezo",
    "bocagrande": "Bocagrande",
    "bruselas": "Bruselas",
    "canapote": "Canapote",
    "castillogrande": "Castillogrande",
    "centro": "Centro",
    "chambacu": "Chambacu",
    "crespo": "Crespo",
    "el bosque": "El Bosque",
    "bosque": "El Bosque",
    "el cabrero": "El Cabrero",
    "cabrero": "El Cabrero",
    "el campestre": "El Campestre",
    "campestre": "El Campestre",
    "el laguito": "El Laguito",
    "laguito": "El Laguito",
    "el pozon": "El Pozon",
    "pozon": "El Pozon",
    "espana": "Espana",
    "getsemani": "Getsemani",
    "la boquilla": "La Boquilla",
    "boquilla": "La Boquilla",
    "la concepcion": "La Concepcion",
    "la esperanza": "La Esperanza",
    "la maria": "La Maria",
    "los alpes": "Los Alpes",
    "manga": "Manga",
    "marbella": "Marbella",
    "martinez martelo": "Martinez Martelo",
    "nuevo bosque": "Nuevo Bosque",
    "olaya": "Olaya Herrera",
    "olaya herrera": "Olaya Herrera",
    "pie de la popa": "Pie de la Popa",
    "recreo": "Recreo",
    "san diego": "San Diego",
    "serena del mar": "Serena del Mar",
    "ternera": "Ternera",
    "torices": "Torices",
    "zaragocilla": "Zaragocilla",
}


NEARBY_NEIGHBORHOODS = {
    "Alto Bosque": ["El Bosque", "Nuevo Bosque", "Martinez Martelo"],
    "Albornoz": ["El Bosque", "Arroz Barato", "Bellavista"],
    "Blas de Lezo": ["El Campestre", "Los Alpes", "Ternera"],
    "Bocagrande": ["Castillogrande", "El Laguito", "Centro"],
    "Bruselas": ["Espana", "Amberes", "Pie de la Popa"],
    "Canapote": ["Torices", "Crespo", "Marbella"],
    "Castillogrande": ["Bocagrande", "El Laguito"],
    "Centro": ["San Diego", "Getsemani", "Bocagrande"],
    "Chambacu": ["Pie de la Popa", "Manga", "Centro"],
    "Crespo": ["Marbella", "Canapote", "La Boquilla"],
    "El Bosque": ["Alto Bosque", "Nuevo Bosque", "Albornoz"],
    "El Cabrero": ["Marbella", "Centro", "Torices"],
    "El Campestre": ["Blas de Lezo", "Los Alpes", "Ternera"],
    "El Laguito": ["Bocagrande", "Castillogrande"],
    "El Pozon": ["Olaya Herrera", "La Maria", "La Esperanza"],
    "Espana": ["Bruselas", "Pie de la Popa", "Zaragocilla"],
    "Getsemani": ["Centro", "Manga", "Chambacu"],
    "La Boquilla": ["Crespo", "Serena del Mar"],
    "La Concepcion": ["Ternera", "Recreo", "Los Alpes"],
    "La Esperanza": ["La Maria", "Olaya Herrera", "El Pozon"],
    "La Maria": ["Olaya Herrera", "La Esperanza", "El Pozon"],
    "Los Alpes": ["El Campestre", "Blas de Lezo", "La Concepcion"],
    "Manga": ["Pie de la Popa", "Getsemani", "Chambacu"],
    "Marbella": ["El Cabrero", "Crespo", "Torices"],
    "Martinez Martelo": ["Alto Bosque", "El Bosque", "Pie de la Popa"],
    "Nuevo Bosque": ["Alto Bosque", "El Bosque", "Los Alpes"],
    "Olaya Herrera": ["La Maria", "La Esperanza", "El Pozon", "Zaragocilla"],
    "Pie de la Popa": ["Manga", "Chambacu", "Espana"],
    "Recreo": ["Ternera", "La Concepcion", "Blas de Lezo"],
    "San Diego": ["Centro", "El Cabrero", "Getsemani"],
    "Serena del Mar": ["La Boquilla"],
    "Ternera": ["Recreo", "La Concepcion", "Blas de Lezo"],
    "Torices": ["Canapote", "Marbella", "El Cabrero"],
    "Zaragocilla": ["Espana", "Olaya Herrera", "Pie de la Popa"],
}


ZONE_CANDIDATES = tuple(sorted(NEIGHBORHOOD_ALIASES))


def normalize_neighborhood(value: Any) -> str | None:
    normalized = normalize_location_text(value)
    if not normalized:
        return None
    if normalized in NEIGHBORHOOD_ALIASES:
        return NEIGHBORHOOD_ALIASES[normalized]
    for alias, canonical in sorted(NEIGHBORHOOD_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
            return canonical
    return None


def nearby_neighborhoods(value: Any, limit: int = 3) -> list[str]:
    canonical = normalize_neighborhood(value) or str(value or "").strip()
    if not canonical:
        return []
    return NEARBY_NEIGHBORHOODS.get(canonical, [])[:limit]


def location_search_terms(value: Any, *, include_nearby: bool = False) -> list[str]:
    canonical = normalize_neighborhood(value) or str(value or "").strip()
    if not canonical:
        return []
    terms = [canonical]
    if include_nearby:
        terms.extend(nearby_neighborhoods(canonical))
    seen = set()
    output = []
    for term in terms:
        key = normalize_location_text(term)
        if key and key not in seen:
            seen.add(key)
            output.append(term)
    return output
