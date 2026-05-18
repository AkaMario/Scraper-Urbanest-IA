function EmptyConversation({ prompts, onPromptClick, isTyping }) {
  return (
    <section className={`flex min-h-[calc(100vh-220px)] items-center px-4 py-10 transition-opacity duration-300 sm:px-6 ${isTyping ? "opacity-40" : "opacity-100"}`}>
      <div className="mx-auto w-full max-w-4xl">
        <div className="mb-8 text-center">
          <h3 className="text-2xl font-semibold leading-tight text-zinc-100 sm:text-3xl md:text-4xl">
            ¿En qué estás trabajando?
          </h3>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-zinc-500 sm:text-base">
            Busca inmuebles en Cartagena o Barranquilla, compara precios y pregúntame por oportunidades usando la base de datos local.
          </p>
        </div>

        <div className="mx-auto flex max-w-2xl flex-wrap justify-center gap-2.5">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onPromptClick(prompt)}
              className="rounded-full border border-white/10 bg-black px-4 py-2.5 text-sm leading-5 text-zinc-300 transition hover:border-white/20 hover:bg-[#1f1f1f] hover:text-white"
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
