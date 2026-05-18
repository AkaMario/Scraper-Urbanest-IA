from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import re
import unicodedata

from app.database import get_db
from app.models import ScrapingJob, SearchQuery
from app.schemas import ChatRequest, ChatResponse
from app.ollama_client import generate_assistant_reply
from app.services.domain_knowledge import (
    build_real_estate_concept_answer,
    is_real_estate_concept_question,
)
from app.services.cartagena_locations import normalize_neighborhood
from app.services.query_parser import fallback_parse_query, has_concrete_search_filters, is_greeting_message, is_search_request
from app.services.web_context import (
    build_function_answer,
    build_web_context,
    build_web_search_answer,
    is_function_question,
    search_web,
    should_search_web,
)
from app.tasks.scraping_tasks import process_search_request


router = APIRouter(prefix="/api", tags=["chat"])


POSITIVE_NEARBY_PATTERNS = (
    "si",
    "si busca",
    "sí",
    "sí busca",
    "dale",
    "ok",
    "okay",
    "hazlo",
    "busca",
    "buscalos",
    "búscalos",
    "busca en barrios cercanos",
)

QUESTION_STARTERS = (
    "que",
    "qué",
    "cuanto",
    "cuánto",
    "cual",
    "cuál",
    "como",
    "cómo",
    "donde",
    "dónde",
    "por que",
    "por qué",
)


def _normalize_intent_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9\s]+", " ", normalized).strip()


def _is_positive_nearby_followup(message: str, parsed_query: dict | None) -> bool:
    if not parsed_query or not parsed_query.get("allow_nearby_followup") or not parsed_query.get("nearby_offer_zones"):
        return False
    normalized = _normalize_intent_text(message)
    if not normalized:
        return False
    if normalized.startswith(QUESTION_STARTERS) and not any(token in normalized for token in ("busca", "dale", "hazlo")):
        return False
    return any(normalized == pattern or normalized.startswith(f"{pattern} ") for pattern in POSITIVE_NEARBY_PATTERNS)


def _build_nearby_followup_query(message: str, parsed_query: dict) -> dict:
    overrides = fallback_parse_query(message)
    normalized_message = _normalize_intent_text(message)
    next_query = dict(parsed_query)
    nearby_zones = [str(zone) for zone in parsed_query.get("nearby_offer_zones") or [] if str(zone).strip()]
    next_query.update(
        {
            "zone": None,
            "neighborhood": None,
            "accepted_zones": nearby_zones,
            "nearby_zones_checked": nearby_zones,
            "location_match_scope": "nearby",
            "fallback_reason": None,
            "fallback_scope": None,
            "allow_nearby_followup": False,
            "__preset": True,
        }
    )
    property_terms = ("apartamento", "apartamentos", "apartaestudio", "apartaestudios", "casa", "casas", "local")
    if any(term in normalized_message for term in property_terms) and overrides.get("property_type") is not None:
        next_query["property_type"] = overrides["property_type"]
    if any(term in normalized_message for term in ("venta", "comprar", "compra", "arriendo", "alquiler")):
        next_query["operation"] = overrides.get("operation") or next_query.get("operation")
    for key, pattern in (
        ("price_min", r"\d|\$|millon|millones|mil"),
        ("price_max", r"\d|\$|millon|millones|mil"),
        ("bedrooms", r"habitacion|habitaciones|alcoba|alcobas"),
        ("bathrooms", r"bano|banos|baño|baños"),
        ("parking_spaces", r"parqueadero|garaje"),
    ):
        if re.search(pattern, normalized_message) and overrides.get(key) is not None:
            next_query[key] = overrides[key]
    keywords = set(next_query.get("keywords") or [])
    keywords.update(overrides.get("keywords") or [])
    next_query["keywords"] = sorted(keyword for keyword in keywords if keyword)
    explicit_zone = normalize_neighborhood(message)
    if explicit_zone and explicit_zone != parsed_query.get("original_zone"):
        next_query["zone"] = explicit_zone
        next_query["neighborhood"] = explicit_zone
        next_query["accepted_zones"] = []
        next_query["nearby_zones_checked"] = []
        next_query["location_match_scope"] = "exact"
    return next_query


def _compose_followup_search_message(message: str, parsed_query: dict | None) -> str:
    if not parsed_query:
        return message

    lowered = message.lower()
    zone = None if "cualquier barrio" in lowered or "cualquier zona" in lowered else parsed_query.get("zone")
    property_type = parsed_query.get("property_type") or "inmueble"
    city = parsed_query.get("city") or "Cartagena"
    parts = [f"Busca {property_type} en {city}"]
    if zone:
        parts.append(f"en {zone}")
    else:
        parts.append("en cualquier barrio")
    if parsed_query.get("price_min") and parsed_query.get("price_max"):
        parts.append(f"entre {parsed_query['price_min']} y {parsed_query['price_max']} pesos")
    elif parsed_query.get("price_max"):
        parts.append(f"hasta {parsed_query['price_max']} pesos")
    if parsed_query.get("bedrooms"):
        parts.append(f"con {parsed_query['bedrooms']} habitaciones")
    if parsed_query.get("bathrooms"):
        parts.append(f"y {parsed_query['bathrooms']} baños")
    return " ".join(parts)


def _is_unhelpful_refusal(reply: str) -> bool:
    lowered = reply.lower().strip()
    refusal_fragments = (
        "no puedo ayudarte",
        "no puedo ayudar",
        "lo siento, pero no puedo",
        "no puedo cumplir",
        "no estoy autorizado",
        "sin busqueda activa",
        "sin búsqueda activa",
        "necesito que proporciones",
        "proporciones más detalles",
        "enviame los datos",
        "envíame los datos",
        "si el usuario desea",
    )
    return any(fragment in lowered for fragment in refusal_fragments)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    properties_context = [item.model_dump() for item in request.properties]
    parsed_query_context = request.parsed_query.model_dump() if request.parsed_query else None
    analysis_context = request.analysis.model_dump() if request.analysis else None

    if _is_positive_nearby_followup(request.message, parsed_query_context):
        nearby_query = _build_nearby_followup_query(request.message, parsed_query_context)
        search_query = SearchQuery(
            user_message=request.message,
            parsed_query_json=nearby_query,
        )
        db.add(search_query)
        db.commit()
        db.refresh(search_query)

        job = ScrapingJob(query_id=search_query.id, status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)

        process_search_request.delay(job.id, search_query.id, request.message)
        return ChatResponse(
            reply="Voy a buscar en barrios cercanos manteniendo un presupuesto parecido.",
            parsed_query=None,
            results=[],
            job_id=job.id,
        )

    should_route_to_chat = not is_search_request(request.message)

    if should_route_to_chat:
        concept_answer = build_real_estate_concept_answer(request.message)
        if concept_answer:
            return ChatResponse(
                reply=concept_answer,
                parsed_query=request.parsed_query,
                results=[],
                job_id=None,
            )

        if not properties_context and is_greeting_message(request.message):
            return ChatResponse(
                reply=(
                    "Hola, soy Urbanest IA. Puedo buscar inmuebles en venta o arriendo en Cartagena y Barranquilla, "
                    "comparar opciones y responder preguntas sobre las viviendas guardadas en la base de datos."
                ),
                parsed_query=request.parsed_query,
                results=[],
                job_id=None,
            )

        function_answer = build_function_answer() if is_function_question(request.message) and not should_search_web(request.message) else None
        web_requested = should_search_web(request.message)
        web_results = search_web(request.message) if web_requested else []
        try:
            system_context = build_web_context(request.message, properties_context, web_results=web_results)
            if function_answer:
                system_context = (
                    "Respuesta base obligatoria para esta pregunta de funcionamiento:\n"
                    f"{function_answer}\n\n"
                    "Contexto adicional:\n"
                    f"{system_context}"
                )
            reply = generate_assistant_reply(
                request.message,
                system_context=system_context,
                properties=properties_context,
                parsed_query=parsed_query_context,
                analysis=analysis_context,
            )
            if function_answer and not any(source in reply.lower() for source in ("fincaraiz", "metrocuadrado", "backend")):
                reply = function_answer
            if web_requested and _is_unhelpful_refusal(reply):
                reply = build_web_search_answer(web_results)
            if is_real_estate_concept_question(request.message) and _is_unhelpful_refusal(reply):
                reply = build_real_estate_concept_answer(request.message) or reply
        except Exception:
            if properties_context:
                reply = (
                    "Puedo ayudarte a comparar las viviendas que ya encontramos. "
                    "Pregúntame por precio, ubicación, área, baños, habitaciones o cuál conviene revisar primero."
                )
            else:
                reply = (
                    "Puedo ayudarte con conceptos inmobiliarios, consejos para comparar inmuebles o búsquedas concretas. "
                    "Para buscar, dime zona, presupuesto, tipo de inmueble y habitaciones."
                )
            if web_requested and _is_unhelpful_refusal(reply):
                reply = build_web_search_answer(web_results)
            if is_real_estate_concept_question(request.message) and _is_unhelpful_refusal(reply):
                reply = build_real_estate_concept_answer(request.message) or reply

        return ChatResponse(
            reply=reply,
            parsed_query=request.parsed_query,
            results=[],
            job_id=None,
        )

    search_message = request.message
    if parsed_query_context and not has_concrete_search_filters(request.message):
        search_message = _compose_followup_search_message(request.message, parsed_query_context)

    search_query = SearchQuery(
        user_message=search_message,
        parsed_query_json={},
    )
    db.add(search_query)
    db.commit()
    db.refresh(search_query)

    job = ScrapingJob(query_id=search_query.id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_search_request.delay(job.id, search_query.id, search_message)

    reply = (
        "Estoy analizando tu búsqueda y consultando fuentes inmobiliarias. "
        "Enseguida te respondo con un resumen y las opciones más relevantes."
    )

    return ChatResponse(
        reply=reply,
        parsed_query=None,
        results=[],
        job_id=job.id,
    )
