function Avatar({ role }) {
  const isUser = role === "user";
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
        isUser ? "bg-slate-200 text-slate-900" : "bg-emerald-500 text-white"
      }`}
    >
      {isUser ? "Tú" : "IA"}
    </div>
  );
}

function ChatMessage({ role, content, subtle = false, children }) {
  const isUser = role === "user";
  const isTyping = !isUser && subtle && !content && !children;

  return (
    <section className="px-3 py-4 sm:px-6 sm:py-5">
      <div className={`mx-auto flex max-w-3xl items-start gap-2 sm:gap-4 ${isUser ? "justify-end" : "justify-start"}`}>
        {!isUser ? <Avatar role={role} /> : null}
        <div className={`min-w-0 flex-1 pt-1 ${isUser ? "flex justify-end" : ""}`}>
          <div
            className={`rounded-[20px] border px-4 py-3 shadow-[0_10px_24px_rgba(0,0,0,0.14)] sm:rounded-[26px] sm:px-5 sm:py-4 ${
              isUser
                ? "ml-auto inline-block max-w-[92%] border-emerald-400/15 bg-emerald-500/10 text-left sm:max-w-[85%]"
                : subtle
                  ? "inline-block max-w-full border-white/8 bg-[#40414f] sm:max-w-[85%]"
                  : "inline-block max-w-full border-white/10 bg-[#444654] sm:max-w-[85%]"
            }`}
          >
            {isTyping ? (
              <div className="flex items-center gap-1.5 py-1" aria-label="La IA está escribiendo">
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.24s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.12s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300" />
              </div>
            ) : null}
            {content ? (
              <p
                className={`whitespace-pre-wrap text-sm leading-6 sm:text-[15px] sm:leading-7 ${
                  subtle ? "text-slate-300" : "text-slate-100"
                }`}
              >
                {content}
              </p>
            ) : null}
            {children ? <div className={content ? "mt-4" : ""}>{children}</div> : null}
          </div>
        </div>
        {isUser ? <Avatar role={role} /> : null}
      </div>
    </section>
  );
}

export default ChatMessage;
