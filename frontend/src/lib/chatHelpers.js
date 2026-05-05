export function formatCurrency(value) {
  if (value === null || value === undefined) {
    return "Sin datos";
  }

  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value);
}

export function isLikelySearchRequest(message) {
  const lowered = message.toLowerCase();
  const signals = [
    "busca",
    "buscar",
    "apartamento",
    "apartamentos",
    "casa",
    "casas",
    "arriendo",
    "habitaciones",
    "habitacion",
    "baños",
    "baño",
    "bocagrande",
    "manga",
    "crespo",
    "cartagena",
    "millones",
    "hasta",
    "entre",
  ];

  return signals.some((signal) => lowered.includes(signal));
}

function buildPropertyLine(property) {
  return `${property.title} en ${property.zone || property.neighborhood || "Cartagena"} por ${formatCurrency(property.price)}.`;
}

export function createFollowUpReply(message, context) {
  const lowered = message.toLowerCase();
  const { results = [], analysis, parsedQuery } = context;

  if (!results.length) {
    return "Todavía no tengo opciones cargadas para responder sobre inmuebles concretos. Lanza primero una búsqueda.";
  }

  const sortedByPrice = [...results].sort((a, b) => a.price - b.price);
  const cheapest = sortedByPrice[0];
  const priciest = sortedByPrice[sortedByPrice.length - 1];
  const opportunities = analysis?.opportunities || [];

  if (lowered.includes("más barata") || lowered.includes("mas barata") || lowered.includes("más económico") || lowered.includes("mas economico")) {
    return `La opción más barata del lote es ${buildPropertyLine(cheapest)} Puedes abrir el anuncio original desde la tarjeta para validarla en la fuente.`;
  }

  if (lowered.includes("más cara") || lowered.includes("mas cara")) {
    return `La opción más cara del lote es ${buildPropertyLine(priciest)} Eso te ayuda a ver el techo del rango actual.`;
  }

  if (lowered.includes("promedio") || lowered.includes("mercado") || lowered.includes("rango")) {
    return `Para ${parsedQuery?.property_type || "estos inmuebles"} en ${parsedQuery?.zone || "la zona consultada"}, el promedio actual está en ${formatCurrency(analysis?.average_price)}, con mínimo en ${formatCurrency(analysis?.min_price)} y máximo en ${formatCurrency(analysis?.max_price)}.`;
  }

  if (lowered.includes("oportunidad") || lowered.includes("oportunidades") || lowered.includes("conviene")) {
    if (!opportunities.length) {
      return "No marqué oportunidades claras en este lote con la regla actual del 15% por debajo del promedio.";
    }
    return `Detecté ${opportunities.length} oportunidad(es). La más clara es ${buildPropertyLine(opportunities[0])}`;
  }

  if (lowered.includes("recomiendas") || lowered.includes("recomendar") || lowered.includes("mejor opción") || lowered.includes("mejor opcion")) {
    const candidate = opportunities[0] || cheapest;
    return `Si buscas balance entre precio y señal de mercado, miraría primero ${buildPropertyLine(candidate)} Después compararía acabados, administración y ubicación exacta en el anuncio original.`;
  }

  if (lowered.includes("cuántos") || lowered.includes("cuantos")) {
    return `Ahora mismo tengo ${results.length} opciones para ${parsedQuery?.zone || "la búsqueda activa"}.`;
  }

  if (lowered.includes("lista") || lowered.includes("resumen") || lowered.includes("opciones")) {
    const topThree = sortedByPrice.slice(0, 3).map(buildPropertyLine).join(" ");
    return `Las opciones más competitivas por precio son: ${topThree}`;
  }

  return "Puedo ayudarte a comparar estas opciones. Pregúntame cosas como cuál es la más barata, cuál parece mejor oportunidad, cómo está el promedio o cuál te recomendaría revisar primero.";
}
