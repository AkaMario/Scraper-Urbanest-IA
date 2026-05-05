function Sidebar({ history = [], onPromptClick, onClearHistory, loading }) {
  const userMessages = history.filter((message) => message.role === "user");
  const recentSearches = userMessages.slice().reverse();

  const SearchIcon = () => (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" />
    </svg>
  );

  const NewChatIcon = () => (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
    </svg>
  );

  const TrashIcon = () => (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 7h12M10 11v6M14 11v6M9 7l1-2h4l1 2M8 7l1 13h6l1-13" />
    </svg>
  );

  return (
    <div className="flex h-full flex-col px-3 py-3 text-sm text-slate-300">
      <div className="pr-11">
        <div className="flex h-9 items-center px-2 text-sm font-semibold text-white">
          Urbanest IA
        </div>
      </div>

      <button
        type="button"
        onClick={onClearHistory}
        disabled={loading}
        className="mt-3 flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm text-slate-100 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <NewChatIcon />
        <span>Nuevo chat</span>
      </button>

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <div className="mb-2 flex items-center justify-between gap-3 px-2">
          <p className="text-xs font-medium text-slate-500">Recientes</p>
          <button
            type="button"
            onClick={onClearHistory}
            disabled={loading || userMessages.length === 0}
            aria-label="Borrar historial"
            title="Borrar historial"
            className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            <TrashIcon />
          </button>
        </div>

        {recentSearches.length === 0 ? (
          <div className="px-2 py-3 text-sm text-slate-500">
            Sin conversaciones
          </div>
        ) : (
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
            {recentSearches.map((message) => (
              <button
                key={message.id}
                type="button"
                onClick={() => onPromptClick?.(message.content)}
                disabled={loading}
                className="group flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left text-sm text-slate-300 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="mt-0.5 text-slate-500 transition group-hover:text-slate-300">
                  <SearchIcon />
                </span>
                <span className="line-clamp-2 leading-5">
                  {message.content}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Sidebar;
