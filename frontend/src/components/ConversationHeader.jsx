function ConversationHeader({ loading, jobId, resultCount }) {
  return (
    <header className="sticky top-0 z-10 bg-black/80 backdrop-blur-xl">
      {/* <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="min-w-0 pr-24 md:pr-0">
          <h2 className="truncate text-lg font-semibold tracking-tight text-zinc-100">Urbanest IA</h2>
          <p className="mt-0.5 hidden text-xs text-zinc-500 sm:block">
            {loading ? "Consultando base inmobiliaria" : resultCount > 0 ? `${resultCount} inmuebles en contexto` : "Asistente inmobiliario para la costa colombiana"}
          </p>
        </div>
        {jobId ? (
          <span className="hidden rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-400 sm:inline-flex">
            Job #{jobId}
          </span>
        ) : null}
      </div> */}
    </header>
  );
}

export default ConversationHeader;
