import ResultCard from "./ResultCard";
import MarketSnapshot from "./MarketSnapshot";

function ChatResultsBlock({ parsedQuery, analysis, results, onPromptClick }) {
  return (
    <div className="space-y-4">
      <MarketSnapshot
        parsedQuery={parsedQuery}
        analysis={analysis}
        results={results}
        loading={false}
        compact
      />

      <div className="rounded-[22px] border border-white/10 bg-[#202123] p-3 sm:rounded-[28px] sm:p-4">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500 sm:text-xs sm:tracking-[0.24em]">
              Opciones encontradas
            </p>
            <h4 className="mt-1 text-base font-semibold text-white">
              {results.length} inmuebles para revisar
            </h4>
          </div>
          <span className="w-fit rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
            Lote actual
          </span>
        </div>

        <div className="space-y-3">
          {results.map((property) => (
            <ResultCard key={`${property.source}-${property.url}`} property={property} compact />
          ))}
        </div>
      </div>

      <div className="rounded-[22px] border border-emerald-400/15 bg-emerald-400/5 p-3 sm:rounded-[24px] sm:p-4">
        <p className="text-sm font-medium text-emerald-300">Preguntas sugeridas</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            "¿Cuál es la opción más barata?",
            "¿Cuál parece mejor oportunidad?",
            "¿Cómo está el promedio del mercado?",
          ].map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPromptClick(prompt)}
              className="rounded-full border border-emerald-400/15 bg-black/10 px-3 py-2 text-xs text-slate-200 transition hover:bg-black/20"
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
