import { useState } from "react";

function Sidebar({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
  onClearHistory,
  onOpenAdmin,
  loading,
}) {
  const [developmentPanel, setDevelopmentPanel] = useState(null);
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

  const HomeIcon = () => (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10.5 12 3l9 7.5M5 10v10h14V10" />
    </svg>
  );

  const DotsIcon = () => (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h.01M12 12h.01M19 12h.01" />
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

  const toggleDevelopmentPanel = (label) => {
    setDevelopmentPanel((current) => (current === label ? null : label));
  };

  return (
    <div className="flex h-full flex-col bg-[#070707] px-3 py-3 text-sm text-zinc-200">
      <div className="mb-4 flex items-center justify-between gap-3 px-2 py-1">
        <h2 className="text-xl font-semibold tracking-tight text-white">Urbanest IA</h2>
        {/* <button
          type="button"
          onClick={onClearHistory}
          disabled={loading || conversations.length === 0}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          title="Borrar historial"
        >
          <TrashIcon />
        </button> */}
      </div>

      <div className="mb-4 grid gap-1">
        <button
          type="button"
          onClick={onNewConversation}
          disabled={loading}
          className="inline-flex w-full items-center justify-start gap-3 rounded-xl bg-[#2f2f2f] px-3 py-2.5 text-sm font-medium text-white transition hover:bg-[#3a3a3a] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <NewChatIcon />
          <span>Nuevo chat</span>
        </button>
        <button
          type="button"
          onClick={() => toggleDevelopmentPanel("Buscar chats")}
          className="inline-flex w-full items-center justify-start gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/10"
        >
          <SearchIcon />
          <span>Buscar chats</span>
        </button>
        <button type="button" onClick={onOpenAdmin} className="inline-flex w-full items-center justify-start gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/10">
          <HomeIcon />
          <span>Inventario</span>
        </button>
        <button type="button" onClick={() => toggleDevelopmentPanel("Más")} className="inline-flex w-full items-center justify-start gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/10">
          <DotsIcon />
          <span>Más</span>
        </button>
      </div>

      {developmentPanel ? (
        <div className="mb-4 rounded-2xl border border-white/10 bg-[#151515] p-4 shadow-xl shadow-black/20">
          <p className="text-sm font-medium text-white">{developmentPanel}</p>
          <p className="mt-1 text-sm leading-5 text-zinc-400">En desarrollo.</p>
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto pr-1">
        <div className="mb-2 px-3 pt-3">
          <p className="text-xs font-semibold text-zinc-400">Recientes</p>
        </div>

        {recentConversations.length === 0 ? (
          <div className="mx-1 rounded-2xl border border-dashed border-white/10 p-3 text-sm leading-5 text-zinc-500">
            No hay conversaciones recientes.
            <div className="mt-2 text-xs text-zinc-600">
              Empieza una búsqueda para guardarla aquí y volver luego.
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            {recentConversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;

              return (
              <div
                key={conversation.id}
                role="button"
                tabIndex={0}
                onClick={() => !loading && onSelectConversation?.(conversation.id)}
                onKeyDown={(event) => {
                  if (!loading && (event.key === "Enter" || event.key === " ")) {
                    event.preventDefault();
                    onSelectConversation?.(conversation.id);
                  }
                }}
                className={`group w-full rounded-xl px-3 py-2.5 text-left transition ${
                  loading ? "cursor-not-allowed opacity-60" : ""
                } ${
                  isActive
                    ? "bg-[#2f2f2f] text-white"
                    : "text-zinc-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm leading-5">{conversation.title}</p>
                  </div>
                      <button
                        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-zinc-500 opacity-0 transition hover:bg-white/10 hover:text-red-300 group-hover:opacity-100"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onDeleteConversation?.(conversation.id);
                        }}
                      >
                        <TrashIcon />
                      </button>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-3 border-t border-white/[0.07] px-2 pb-1 pt-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-700 text-xs font-semibold text-white">U</div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-white">Urbanest</p>
          <p className="text-xs text-zinc-500">IA inmobiliaria</p>
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
