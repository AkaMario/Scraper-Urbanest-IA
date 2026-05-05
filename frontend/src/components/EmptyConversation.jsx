function EmptyConversation({ prompts, onPromptClick, isTyping }) {
  return (
    <section className={`px-3 py-10 sm:px-6 sm:py-14 lg:py-16 transition-opacity duration-300 ${isTyping ? "opacity-40" : "opacity-100"}`}>
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 text-center sm:mb-10">
          <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500 sm:text-xs sm:tracking-[0.35em]">
            Urbanest IA
          </p>
          <h3 className="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl">
            ¿Qué arriendo quieres rastrear?
          </h3>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base sm:leading-7">
            Pide zonas, presupuesto, tipo de inmueble, habitaciones, baños o keywords y te devuelvo mercado comparado.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPromptClick(prompt)}
              className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-left text-sm leading-6 text-slate-200 transition hover:bg-white/[0.08] md:min-h-[144px]"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export default EmptyConversation;
