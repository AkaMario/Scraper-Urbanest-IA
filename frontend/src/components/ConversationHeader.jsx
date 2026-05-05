function ConversationHeader({ loading, jobId, resultCount }) {
  return (
    <header className="sticky top-0 z-10 border-b border-white/5 bg-[#343541]/90 backdrop-blur">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-3 sm:px-6 md:flex-row md:items-center md:justify-between md:py-4">
        <div className="min-w-0 pr-24 md:pr-0">
          <p className="truncate text-[10px] uppercase tracking-[0.22em] text-slate-500 sm:text-xs sm:tracking-[0.28em]">
            Powered by DNAMYK
          </p>
          <h2 className="mt-1 text-lg font-semibold text-white">Urbanest IA</h2>
        </div>
      </div>
    </header>
  );
}

export default ConversationHeader;
