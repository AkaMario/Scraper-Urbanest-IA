import json
from typing import Any

import requests

from app.config import settings


PROMPT_TEMPLATE = """
Extrae los criterios de busqueda inmobiliaria del siguiente mensaje.
Responde unicamente JSON valido con estas llaves:
city, zone, neighborhood, property_type, price_min, price_max, bedrooms, bathrooms, keywords.
Usa null si un dato no existe. keywords debe ser una lista de strings.
Mensaje: {message}
""".strip()


CHAT_REPLY_TEMPLATE = """
Eres Urbanest IA, asistente inmobiliario para arriendos en Cartagena.
Responde en espanol, en un solo mensaje, tono natural.
Usa solo el contexto dado. No inventes datos.
Si el usuario saluda, saluda y explica brevemente que puedes buscar y comparar inmuebles.
Si hay inmuebles en contexto, puedes compararlos y responder preguntas sobre ellos.
Si falta informacion, dilo.
No respondas en JSON.

Consulta original del usuario: {message}

Busqueda activa:
{parsed_query}

Resumen de mercado actual:
{analysis}

Inmuebles en contexto:
{properties}
""".strip()


SEARCH_REPLY_TEMPLATE = """
Eres Urbanest IA, asistente inmobiliario para arriendos en Cartagena.
Cartagena siempre se refiere a Cartagena de Indias, Colombia.
Redacta una respuesta final en espanol, breve, natural y util.
No listes URLs. No enumeres todos los inmuebles. No digas "España".
Resume la busqueda, di cuantas opciones encontraste, menciona promedio/minimo/maximo si existen
y destaca 1 o 2 opciones por precio o encaje si el contexto lo permite.
Termina invitando a comparar, filtrar o elegir una propiedad.
No inventes datos. No respondas en JSON.

Mensaje original del usuario: {message}

Busqueda interpretada:
{parsed_query}

Analisis:
{analysis}

Inmuebles encontrados:
{properties}
""".strip()


ASSISTANT_REPLY_TEMPLATE = """
Eres Urbanest IA, una IA conversacional real dentro de una app inmobiliaria.
Responde en espanol natural, claro y directo.
No digas que tienes plugins. Si hablas de internet, explica que el backend consulta fuentes permitidas y te entrega contexto.
No inventes resultados, URLs ni capacidades. Si una pagina no esta en el contexto aprobado, dilo.
Puedes responder preguntas sobre tu funcionamiento, fuentes, scrapers, limitaciones, busquedas previas y propiedades en contexto.
Puedes explicar conceptos inmobiliarios generales como VIS, VIP, canon, administración, avalúo, subsidios y financiación.
No rechaces preguntas educativas o definiciones inmobiliarias normales.
Si el usuario pide buscar inmuebles concretos, indicale que puede pedir zona, presupuesto, tipo de inmueble, habitaciones o banos.
Si el contexto incluye "Resultados de busqueda web entregados por backend", responde usando esos resultados:
- resume los puntos principales,
- menciona las fuentes o URLs disponibles de forma breve,
- no digas que necesitas mas detalles para buscar,
- si los resultados son insuficientes, dilo y resume lo que si aparece.
No respondas en JSON.

Pregunta del usuario:
{message}

Contexto de funcionamiento y web permitido:
{system_context}

Busqueda activa:
{parsed_query}

Resumen de mercado actual:
{analysis}

Inmuebles en contexto:
{properties}
""".strip()


SIMPLE_ASSISTANT_REPLY_TEMPLATE = """
Eres Urbanest IA, asistente inmobiliario.
Responde en espanol natural, breve y util.
Puedes explicar conceptos, dar consejos de comparacion, negociacion y busqueda de arriendos.
No rechaces preguntas inmobiliarias normales. No inventes datos concretos ni URLs.

Pregunta:
{message}
""".strip()


def _post_to_ollama(
    *,
    prompt: str,
    timeout: int,
    options: dict[str, Any],
    response_format: str | None = None,
) -> str:
    runtime_options = {
        "num_thread": settings.ollama_num_thread,
        "num_ctx": settings.ollama_num_ctx,
        **options,
    }
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": runtime_options,
        "keep_alive": "10m",
    }
    if response_format:
        payload["format"] = response_format

    response = requests.post(
        f"{settings.ollama_url}/api/generate",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get("response", "")).strip()


def _truncate_properties(properties: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in properties[:limit]:
        description = item.get("description")
        if description:
            description = str(description)[:180]
        serialized.append(
            {
                "title": item.get("title"),
                "price": item.get("price"),
                "zone": item.get("zone"),
                "neighborhood": item.get("neighborhood"),
                "bedrooms": item.get("bedrooms"),
                "bathrooms": item.get("bathrooms"),
                "area_m2": item.get("area_m2"),
                "source": item.get("source"),
                "url": item.get("url"),
                "description": description,
            }
        )
    return serialized


def _format_parsed_query(parsed_query: dict[str, Any] | None) -> str:
    if not parsed_query:
        return "sin busqueda activa"

    parts = [
        f"ciudad={parsed_query.get('city') or 'Cartagena'}",
        f"zona={parsed_query.get('zone') or '-'}",
        f"tipo={parsed_query.get('property_type') or '-'}",
        f"precio_min={parsed_query.get('price_min') or '-'}",
        f"precio_max={parsed_query.get('price_max') or '-'}",
        f"habitaciones={parsed_query.get('bedrooms') or '-'}",
        f"banos={parsed_query.get('bathrooms') or '-'}",
    ]
    return ", ".join(parts)


def _format_analysis(analysis: dict[str, Any] | None) -> str:
    if not analysis:
        return "sin analisis"

    return ", ".join(
        [
            f"total={analysis.get('total_results') or 0}",
            f"promedio={analysis.get('average_price') or '-'}",
            f"min={analysis.get('min_price') or '-'}",
            f"max={analysis.get('max_price') or '-'}",
            f"debajo_promedio={analysis.get('below_average_count') or 0}",
            f"oportunidades={len(analysis.get('opportunities') or [])}",
        ]
    )


def _format_properties(properties: list[dict[str, Any]]) -> str:
    if not properties:
        return "sin inmuebles"

    lines: list[str] = []
    for index, item in enumerate(properties, start=1):
        lines.append(
            " | ".join(
                [
                    f"{index}. {item.get('title') or 'Inmueble'}",
                    f"zona={item.get('zone') or item.get('neighborhood') or '-'}",
                    f"precio={item.get('price') or '-'}",
                    f"hab={item.get('bedrooms') or '-'}",
                    f"banos={item.get('bathrooms') or '-'}",
                    f"area={item.get('area_m2') or '-'}",
                    f"fuente={item.get('source') or '-'}",
                    f"url={item.get('url') or '-'}",
                ]
            )
        )
    return "\n".join(lines)


def parse_query_with_ollama(message: str) -> dict[str, Any]:
    raw = _post_to_ollama(
        prompt=PROMPT_TEMPLATE.format(message=message),
        timeout=8,
        options={
            "temperature": 0,
            "num_predict": 120,
        },
        response_format="json",
    ) or "{}"
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("Ollama no devolvio un JSON objeto")


def generate_property_chat_reply(
    message: str,
    *,
    properties: list[dict[str, Any]] | None = None,
    parsed_query: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> str:
    safe_properties = _truncate_properties(properties or [])
    prompt = CHAT_REPLY_TEMPLATE.format(
        message=message,
        parsed_query=_format_parsed_query(parsed_query),
        analysis=_format_analysis(analysis),
        properties=_format_properties(safe_properties),
    )
    return _post_to_ollama(
        prompt=prompt,
        timeout=60,
        options={
            "temperature": 0.2,
            "num_predict": 80,
        },
    )


def generate_assistant_reply(
    message: str,
    *,
    system_context: str,
    properties: list[dict[str, Any]] | None = None,
    parsed_query: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> str:
    safe_properties = _truncate_properties(properties or [])
    has_context = bool(safe_properties or parsed_query or analysis or "Resultados de busqueda web" in system_context)
    if has_context:
        prompt = ASSISTANT_REPLY_TEMPLATE.format(
            message=message,
            system_context=system_context,
            parsed_query=_format_parsed_query(parsed_query),
            analysis=_format_analysis(analysis),
            properties=_format_properties(safe_properties),
        )
        num_predict = 140
    else:
        prompt = SIMPLE_ASSISTANT_REPLY_TEMPLATE.format(message=message)
        num_predict = 80
    return _post_to_ollama(
        prompt=prompt,
        timeout=25,
        options={
            "temperature": 0.25,
            "num_predict": num_predict,
        },
    )


def generate_search_reply(
    message: str,
    *,
    properties: list[dict[str, Any]] | None = None,
    parsed_query: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> str:
    safe_properties = _truncate_properties(properties or [])
    prompt = SEARCH_REPLY_TEMPLATE.format(
        message=message,
        parsed_query=_format_parsed_query(parsed_query),
        analysis=_format_analysis(analysis),
        properties=_format_properties(safe_properties),
    )
    return _post_to_ollama(
        prompt=prompt,
        timeout=70,
        options={
            "temperature": 0.2,
            "num_predict": 150,
        },
    )


def build_search_reply(
    *,
    message: str | None = None,
    parsed_query: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    properties: list[dict[str, Any]] | None = None,
) -> str:
    safe_query = parsed_query or {}
    safe_analysis = analysis or {}
    safe_properties = properties or []
    requested_zone = safe_query.get("zone") or safe_query.get("neighborhood")
    city_scope = safe_query.get("city") or "Cartagena"
    zone = (
        f"{city_scope} completa, tomando {requested_zone} solo como referencia"
        if requested_zone
        else f"distintas zonas de {city_scope}"
    )
    property_type = safe_query.get("property_type") or "inmuebles"
    total = len(safe_properties)

    if message and settings.enable_ollama_search_summaries:
        try:
            return generate_search_reply(
                message,
                properties=safe_properties,
                parsed_query=safe_query or None,
                analysis=safe_analysis or None,
            )
        except Exception:
            pass

    if not total:
        return (
            f"No encontré {property_type} que encajen bien con el presupuesto y criterios actuales para {zone}. "
            "La busqueda se hizo sin cerrar el resultado a un solo barrio. "
            "Si quieres, puedo ampliar el rango, cambiar el tipo de inmueble o bajar algun criterio."
        )

    average_price = safe_analysis.get("average_price")
    min_price = safe_analysis.get("min_price")
    max_price = safe_analysis.get("max_price")
    opportunity_count = len(safe_analysis.get("opportunities") or [])

    message = (
        f"Encontré {total} opción(es) de {property_type} para {zone}. "
        f"El mercado del lote quedó entre {min_price or 'sin dato'} y {max_price or 'sin dato'} pesos"
    )
    if average_price:
        message += f", con un promedio cercano a {round(float(average_price))}."
    else:
        message += "."

    if opportunity_count:
        message += f" Detecté {opportunity_count} oportunidad(es) por debajo del promedio del grupo."

    message += " Ya te dejé las propiedades aquí mismo para que me pidas comparar, recomendar o filtrar mejor."
    return message
