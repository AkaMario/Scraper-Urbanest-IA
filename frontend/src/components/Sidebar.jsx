function Sidebar({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onClearHistory,
  loading,
}) {
  const recentConversations = conversations
    .slice()
    .sort((first, second) => (second.updatedAt || 0) - (first.updatedAt || 0));

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
    <div className="flex h-full flex-col border-r border-white/10 bg-[#1f232f] px-4 py-4 text-sm text-slate-300 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.02)]">
      <div className="mb-5 flex items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Historial</p>
          <h2 className="mt-2 text-lg font-semibold text-white">Conversaciones</h2>
        </div>
        {/* <div className="rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-300">
          {recentSearches.length}
        </div> */}
      </div>

      <div className="mb-4 grid gap-3">
        <button
          type="button"
          onClick={onNewConversation}
          disabled={loading}
          className="inline-flex w-full items-center justify-start gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm font-medium text-emerald-100 transition hover:border-emerald-300/40 hover:bg-emerald-500/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <NewChatIcon />
          <span>Nuevo chat</span>
        </button>
        <button
          type="button"
          onClick={onClearHistory}
          disabled={loading || conversations.length === 0}
          className="inline-flex w-full items-center justify-start gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <TrashIcon />
          <span>Borrar conversaciones</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        <div className="mb-3 flex items-center justify-between gap-3 px-1">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-500">Recientes</p>
          </div>
        </div>

        {recentConversations.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-slate-500">
            No hay conversaciones recientes.
            <div className="mt-2 text-[11px] text-slate-500">
              Empieza una búsqueda para guardarla aquí y volver luego.
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {recentConversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;

              return (
              <button
                key={conversation.id}
                type="button"
                onClick={() => onSelectConversation?.(conversation.id)}
                disabled={loading}
                className={`group w-full rounded-3xl border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                  isActive
                    ? "border-emerald-400/40 bg-emerald-500/10"
                    : "border-white/10 bg-[#262c3d] hover:border-emerald-400/30 hover:bg-[#2e3449]"
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl bg-white/5 text-slate-300 transition group-hover:bg-emerald-400/15 group-hover:text-emerald-200">
                    <SearchIcon />
                  </span> */}
                  <div className="min-w-0">
                    <p className="line-clamp-2 text-sm leading-6 text-slate-100">{conversation.title}</p>
                    <p className="mt-2 text-[11px] text-slate-500">
                      {conversation.messages?.length || 0} mensajes.
                    </p>
                  </div>
                </div>
              </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default Sidebar;
