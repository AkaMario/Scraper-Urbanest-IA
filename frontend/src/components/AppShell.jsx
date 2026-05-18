function AppShell({
  sidebar,
  main,
  sidebarOpen,
  onOpenSidebar,
  onCloseSidebar,
}) {
  const gridColumns = sidebarOpen ? "lg:grid-cols-[260px_minmax(0,1fr)]" : "grid-cols-1";

  const PanelIcon = () => (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 5.5h16M4 12h16M4 18.5h16" />
    </svg>
  );

  const CloseIcon = () => (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m6 6 12 12M18 6 6 18" />
    </svg>
  );

  return (
    <div className="min-h-screen bg-black text-white">
      {sidebarOpen ? (
        <button
          type="button"
          aria-label="Cerrar historial"
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={onCloseSidebar}
        />
      ) : null}

      <div className={`grid min-h-screen ${gridColumns}`}>
        {sidebarOpen ? (
          <aside className="fixed inset-y-0 left-0 z-40 w-[min(86vw,320px)] border-r border-white/[0.07] bg-[#070707] lg:static lg:z-auto lg:block lg:w-auto">
            <div className="relative h-screen overflow-y-auto lg:sticky lg:top-0">
              <button
                type="button"
                onClick={onCloseSidebar}
                aria-label="Cerrar historial"
                title="Cerrar historial"
                className="absolute right-3 top-3 z-20 flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-white/10 hover:text-white lg:hidden"
              >
                <CloseIcon />
              </button>
              {sidebar}
            </div>
          </aside>
        ) : null}
        <main className="min-w-0 bg-black">{main}</main>
      </div>

      <div className="fixed left-3 top-3 z-50 flex max-w-[calc(100vw-1.5rem)] flex-wrap gap-2 sm:left-4 sm:top-4">
        {!sidebarOpen ? (
          <button
            type="button"
            onClick={onOpenSidebar}
            aria-label="Abrir historial"
            title="Abrir historial"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-[#111]/95 text-zinc-200 shadow-lg shadow-black/30 transition hover:bg-white/10 hover:text-white"
          >
            <PanelIcon />
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default AppShell;
