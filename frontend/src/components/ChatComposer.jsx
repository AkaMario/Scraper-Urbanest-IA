import { useEffect, useRef, useState } from "react";

function ChatComposer({ onSend, onTyping, loading }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "24px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 176)}px`;
  }, [input]);

  const updateTyping = (value) => {
    setInput(value);
    if (onTyping) {
      onTyping(Boolean(value.trim()));
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!input.trim() || loading) {
      return;
    }
    onSend(input.trim());
    updateTyping("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (input.trim() && !loading) {
        onSend(input.trim());
        updateTyping("");
      }
    }
  };

  return (
    <div className="sticky bottom-0 bg-gradient-to-t from-black via-black to-black/0 px-3 pb-4 pt-5 sm:px-6 sm:pb-6">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
        <div className="rounded-[28px] border border-white/10 bg-[#2f2f2f] px-2 py-2 shadow-[0_18px_60px_rgba(0,0,0,0.45)] transition focus-within:border-white/20 sm:rounded-[32px]">
          <div className="flex min-h-[44px] items-center gap-2">
            <button
              type="button"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-zinc-300 transition hover:bg-white/10 hover:text-white"
              aria-label="Agregar contexto"
            >
              <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
              </svg>
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              className="max-h-44 min-h-6 flex-1 resize-none overflow-y-auto bg-transparent px-1 py-0 text-[15px] leading-6 text-white outline-none placeholder:text-zinc-400"
              value={input}
              onChange={(event) => updateTyping(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Pregunta por zonas, precios o propiedades guardadas..."
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-600 disabled:text-zinc-300"
              aria-label={loading ? "Buscando" : "Enviar"}
            >
              {loading ? (
                <span className="h-3 w-3 animate-pulse rounded-full bg-current" />
              ) : (
                <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5m0 0-6 6m6-6 6 6" />
                </svg>
              )}
            </button>
          </div>
        </div>
        <p className={`mt-2 px-2 text-center text-xs leading-5 text-zinc-600 transition-opacity duration-300 ${input.trim() ? "opacity-0" : "opacity-100"}`}>
          Urbanest IA puede equivocarse. Verifica datos importantes antes de contactar una propiedad.
        </p>
      </form>
    </div>
  );
}

export default ChatComposer;
