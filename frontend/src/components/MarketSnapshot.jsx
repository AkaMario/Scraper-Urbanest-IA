function formatCurrency(value) {
  if (value === null || value === undefined) {
    return "Sin dato";
  }

  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value);
}

function buildSearchLine(parsedQuery) {
  if (!parsedQuery) {
    return "Aun no hay una busqueda activa.";
  }

  const requestedZone = parsedQuery.zone || parsedQuery.neighborhood;
  const scope = requestedZone || parsedQuery.city || "Cartagena";
  const fragments = [
    parsedQuery.property_type || "inmuebles",
    scope,
  ];

  if (parsedQuery.bedrooms) {
    fragments.push(`${parsedQuery.bedrooms} hab`);
  }

  if (parsedQuery.bathrooms) {
    fragments.push(`${parsedQuery.bathrooms} baños`);
  }

  return fragments.join(" · ");
}

function MetricCard({ label, value, accent = "slate" }) {
  const accentStyles = {
    slate: "border-white/10 bg-white/[0.04] text-white",
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
    amber: "border-amber-300/20 bg-amber-300/10 text-amber-100",
  };

  return (
    <div className={`rounded-[20px] border p-3 sm:rounded-[24px] sm:p-4 ${accentStyles[accent] || accentStyles.slate}`}>
      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400 sm:text-[11px] sm:tracking-[0.22em]">{label}</p>
      <p className="mt-2 break-words text-base font-semibold sm:text-lg">{value}</p>
    </div>
  );
}

function InsightPill({ children }) {
  return (
    <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-slate-200">
      {children}
    </span>
  );
}

function MarketSnapshot({ parsedQuery, analysis, results, loading, compact = false }) {
  const resultCount = results?.length || analysis?.total_results || 0;
  const opportunity = analysis?.opportunities?.[0];
  const requestedZone = parsedQuery?.zone || parsedQuery?.neighborhood;
  const scopeLabel = requestedZone || parsedQuery?.city || "Cartagena";

  return (
    <section className="overflow-hidden rounded-[24px] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] sm:rounded-[30px]">
      <div className={`${compact ? "p-3 sm:p-4" : "p-4 sm:p-5"}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-300/80 sm:text-[11px] sm:tracking-[0.28em]">Radar de mercado</p>
            <h3 className="mt-2 text-lg font-semibold text-white sm:text-xl">
              {loading ? "Leyendo la consulta en tiempo real" : "Panorama de la busqueda"}
            </h3>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">
              {loading
                ? "Estoy convirtiendo tu mensaje en criterios de mercado y preparando resultados comparables."
                : buildSearchLine(parsedQuery)}
            </p>
          </div>

          <div className="flex max-w-full flex-wrap gap-2">
            <InsightPill>{resultCount} opciones</InsightPill>
            <InsightPill>
              {parsedQuery?.price_min || parsedQuery?.price_max
                ? `${formatCurrency(parsedQuery?.price_min)} a ${formatCurrency(parsedQuery?.price_max)}`
                : "sin rango definido"}
            </InsightPill>
          </div>
        </div>

        <div className={`mt-5 grid gap-3 ${compact ? "grid-cols-1 sm:grid-cols-2" : "sm:grid-cols-2 xl:grid-cols-4"}`}>
          <MetricCard label="Promedio" value={formatCurrency(analysis?.average_price)} />
          <MetricCard label="Minimo" value={formatCurrency(analysis?.min_price)} accent="emerald" />
          <MetricCard label="Maximo" value={formatCurrency(analysis?.max_price)} />
          <MetricCard
            label="Oportunidades"
            value={`${analysis?.opportunities?.length || 0}`}
            accent={(analysis?.opportunities?.length || 0) > 0 ? "amber" : "slate"}
          />
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[1.25fr_0.95fr]">
          <div className="rounded-[20px] border border-white/10 bg-black/20 p-3 sm:rounded-[24px] sm:p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500 sm:text-[11px] sm:tracking-[0.24em]">Lectura rapida</p>
            <p className="mt-3 text-sm leading-7 text-slate-200">
              {loading
                ? "Todavia no hay lectura final porque sigo esperando anuncios y precios comparables."
                : resultCount === 0
                  ? "Cuando llegue un lote de inmuebles te mostraré aqui el tono del mercado, dispersion de precios y oportunidades claras."
                  : `Estoy viendo ${resultCount} resultado(s) para ${scopeLabel}. El mercado se mueve entre ${formatCurrency(analysis?.min_price)} y ${formatCurrency(analysis?.max_price)}, con una referencia central de ${formatCurrency(analysis?.average_price)}.`}
            </p>
          </div>

          <div className="rounded-[20px] border border-emerald-400/15 bg-emerald-400/8 p-3 sm:rounded-[24px] sm:p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-300 sm:text-[11px] sm:tracking-[0.24em]">Foco sugerido</p>
            <p className="mt-3 text-sm leading-7 text-slate-100">
              {opportunity
                ? `${opportunity.title} aparece como la señal mas atractiva del lote, con precio de ${formatCurrency(opportunity.price)} en ${opportunity.zone || opportunity.neighborhood || "Cartagena"}.`
                : loading
                  ? "Aun no puedo marcar una oportunidad porque sigo procesando el lote."
                  : "Todavia no hay una oportunidad clara marcada por la regla actual. Aun asi, podemos comparar las opciones por precio, zona y tamaño."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default MarketSnapshot;
