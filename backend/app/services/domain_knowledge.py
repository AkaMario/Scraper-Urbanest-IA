from __future__ import annotations

import re


def _normalize(message: str) -> str:
    return message.lower().strip()


def is_real_estate_concept_question(message: str) -> bool:
    lowered = _normalize(message)
    return bool(
        re.search(r"\b(vis|vivienda\s+vis|vivienda\s+de\s+interes\s+social|vivienda\s+de\s+interés\s+social)\b", lowered)
        or re.search(r"\b(no\s+vis|vip|subsidio|canon|administracion|administración|avaluo|avalúo)\b", lowered)
    )


def build_real_estate_concept_answer(message: str) -> str | None:
    lowered = _normalize(message)

    if re.search(r"\b(vis|vivienda\s+vis|vivienda\s+de\s+interes\s+social|vivienda\s+de\s+interés\s+social)\b", lowered):
        return (
            "Una vivienda VIS es una Vivienda de Interés Social. En Colombia se refiere a una vivienda pensada "
            "para hogares de ingresos bajos o medios, con un precio máximo definido por la normativa vigente.\n\n"
            "En la práctica, importa por tres cosas:\n"
            "1. Suele permitir acceso a subsidios o beneficios de financiación, si el comprador cumple requisitos.\n"
            "2. Tiene topes de precio, así que no cualquier proyecto puede venderse como VIS.\n"
            "3. Normalmente está orientada a compra de vivienda nueva, aunque las condiciones dependen del programa, "
            "la ciudad y la entidad financiera.\n\n"
            "Si estás mirando un inmueble, lo clave es confirmar si el proyecto realmente está clasificado como VIS, "
            "cuál es el valor en salarios mínimos o pesos, y qué subsidios aplican para tu caso."
        )

    if "vip" in lowered:
        return (
            "VIP significa Vivienda de Interés Prioritario. Es una categoría más enfocada en hogares de menores ingresos "
            "y suele tener un tope de precio menor que la VIS. Sirve para identificar proyectos con condiciones de acceso "
            "más sociales y posibles subsidios, según la normativa y programas vigentes."
        )

    if "canon" in lowered:
        return (
            "El canon de arriendo es el valor que el arrendatario paga periódicamente, normalmente cada mes, por usar un inmueble. "
            "No siempre incluye administración, servicios públicos, parqueadero u otros cobros, así que conviene confirmar qué está "
            "incluido antes de comparar dos anuncios."
        )

    if "administracion" in lowered or "administración" in lowered:
        return (
            "La administración es una cuota que se paga en edificios o conjuntos para cubrir servicios comunes como vigilancia, "
            "aseo, mantenimiento, zonas sociales y operación del inmueble. En arriendos puede estar incluida en el canon o cobrarse aparte."
        )

    return None


def build_fast_real_estate_reply(message: str) -> str:
    lowered = _normalize(message)

    if "compar" in lowered:
        return (
            "Para comparar dos apartamentos, mira primero el costo total mensual: canon, administración, servicios estimados y parqueadero. "
            "Luego compara ubicación, área útil, estado del inmueble, ventilación, ruido, seguridad y tiempo de transporte. "
            "Si uno es más caro, debería compensarlo con mejor ubicación, menos gastos ocultos o mejor calidad de vida."
        )

    if "negoci" in lowered:
        return (
            "Para negociar un arriendo, llega con comparables reales de la zona, pregunta qué incluye el canon y ofrece claridad: fecha de inicio, "
            "perfil del arrendatario y capacidad de pago. Si el precio no baja, intenta negociar administración incluida, parqueadero o ajustes menores."
        )

    if "consejo" in lowered or "recomienda" in lowered or "recomendacion" in lowered or "recomendación" in lowered:
        return (
            "Mi recomendación rápida: no compares solo por precio. Compara costo total, ubicación, estado del inmueble y fricciones diarias "
            "como transporte, ruido, seguridad y gastos incluidos. El mejor arriendo suele ser el que reduce costos ocultos."
        )

    return (
        "Puedo ayudarte con conceptos inmobiliarios, consejos para comparar arriendos o búsquedas concretas. "
        "Para buscar, dime zona, presupuesto, tipo de inmueble y número de habitaciones."
    )
