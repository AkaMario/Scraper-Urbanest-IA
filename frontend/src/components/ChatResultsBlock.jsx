import ResultCard from "./ResultCard";
import MarketSnapshot from "./MarketSnapshot";

function ChatResultsBlock({ parsedQuery, analysis, results, onPromptClick }) {
  const isSingleProperty = results.length === 1;

  return (
    <div className="space-y-4 sm:space-y-5">
      <MarketSnapshot
        parsedQuery={parsedQuery}
        analysis={analysis}
        results={results}
        loading={false}
        compact
      />

      <div className="overflow-hidden rounded-[24px] border border-white/10 bg-[#111] sm:rounded-[30px]">
        <div className="border-b border-white/10 bg-white/[0.025] p-3 sm:p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.2em] text-zinc-500 sm:text-xs sm:tracking-[0.24em]">
                Opciones encontradas
              </p>
              <h4 className="mt-1 text-base font-semibold text-white">
                {results.length} inmuebles para revisar
              </h4>
              <p className="mt-1 text-xs leading-5 text-zinc-400 sm:text-sm">
                {isSingleProperty
                  ? "Vista completa de la propiedad encontrada."
                  : "Desliza horizontalmente para comparar sin perder contexto."}
              </p>
            </div>
            <span className="w-fit rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-medium text-zinc-300">
              {isSingleProperty ? "Vista completa" : "Scroll horizontal"}
            </span>
          </div>
        </div>

        <div className="overflow-x-auto px-3 py-4 sm:px-4">
          <div className="flex snap-x snap-mandatory gap-3 pb-2 sm:gap-4">
            {results.map((property) => (
              <div key={`${property.source}-${property.url}`} className={`${isSingleProperty ? "w-full" : "w-[82vw] max-w-[360px] shrink-0 sm:w-[320px] md:w-[340px]"}`}>
                <ResultCard property={property} compact horizontal />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-[22px] border border-white/10 bg-white/[0.03] p-3 sm:rounded-[24px] sm:p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-medium text-zinc-200">Preguntas sugeridas</p>
          <p className="text-xs text-zinc-500">Toca una para comparar el lote</p>
        </div>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
          {[
            "¿Cuál es la opción más barata?",
            "¿Cuál parece mejor oportunidad?",
            "¿Qué características tienen las propiedades?",
            "¿Cuál tiene mejor descripción para visitar?",
            "¿Cómo está el promedio del mercado?",
          ].map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPromptClick(prompt)}
              className="shrink-0 rounded-full border border-white/10 bg-black px-3 py-2 text-xs text-zinc-300 transition hover:bg-[#202020] hover:text-white"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ChatResultsBlock;
