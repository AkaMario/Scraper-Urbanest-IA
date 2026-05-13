import ResultCard from "./ResultCard";

function ResultsPanel({ parsedQuery, analysis, results, loading }) {
  const requestedZone = parsedQuery?.zone || parsedQuery?.neighborhood;
  const title = requestedZone || parsedQuery?.city || "Cartagena";

  return (
    <div className="flex h-full flex-col text-slate-200">
      <div className="border-b border-white/5 px-4 py-4 sm:px-5">
        <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500 sm:text-xs sm:tracking-[0.28em]">Inspector</p>
        <h2 className="mt-1 text-lg font-semibold text-white">Lote activo</h2>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-3 py-4 sm:px-5 sm:py-5">
        <section className="rounded-[22px] border border-white/8 bg-white/[0.03] p-3 sm:rounded-[28px] sm:p-4">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500 sm:text-[11px] sm:tracking-[0.24em]">Consulta activa</p>
              <h3 className="mt-1 text-sm font-medium text-white">
                {parsedQuery ? `${parsedQuery.property_type || "Inmuebles"} en ${title}` : "Esperando búsqueda"}
              </h3>
            </div>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
              {results.length}
            </span>
          </div>

          <div className="mb-4 rounded-[22px] border border-white/10 bg-black/10 p-4 text-sm leading-6 text-slate-300">
            {loading
              ? "Estoy llenando este lote con anuncios comparables."
              : results.length > 0
                ? `Aquí tienes el lote activo para inspección rápida. El análisis de mercado y la lectura inteligente viven dentro del chat del asistente.`
                : "Cuando lleguen resultados, este panel quedará como vista de apoyo para revisar tarjetas y abrir anuncios."}
          </div>

          <div className="space-y-3">
            {results.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-black/10 p-4 text-sm leading-6 text-slate-400">
                {loading
                  ? "Estoy esperando que termine el job para poblar el lote."
                  : "Aquí aparecerán los inmuebles encontrados para la consulta activa."}
              </div>
            ) : (
              results.map((property) => (
                <ResultCard key={`${property.source}-${property.url}`} property={property} />
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default ResultsPanel;
