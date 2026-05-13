from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScrapingJob, SearchQuery
from app.schemas import ChatRequest, ChatResponse
from app.ollama_client import generate_assistant_reply
from app.services.domain_knowledge import (
    build_real_estate_concept_answer,
    is_real_estate_concept_question,
)
from app.services.query_parser import has_concrete_search_filters, is_greeting_message, is_search_request
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
                    "Hola, soy Urbanest IA. Puedo buscar inmuebles en arriendo en Cartagena, "
                    "comparar opciones y responder preguntas sobre las viviendas que encontremos."
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
                    "Puedo ayudarte con conceptos inmobiliarios, consejos para comparar arriendos o búsquedas concretas. "
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
