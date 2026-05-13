import { useState } from "react";

function ChatComposer({ onSend, onTyping, loading }) {
  const [input, setInput] = useState("");

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
    <div className="sticky bottom-0 border-t border-white/5 bg-gradient-to-t from-[#343541] via-[#343541] to-[#343541]/60 px-3 pb-4 pt-3 sm:px-6 sm:pb-6 sm:pt-4">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
        <div className="rounded-[22px] border border-white/10 bg-[#40414f] p-2.5 sm:rounded-[30px] sm:p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3 items-center">
            <textarea
              className="flex-1 bg-transparent px-3 pt-4 text-sm text-white outline-none placeholder:text-slate-400 sm:text-[15px] resize-none h-10 sm:h-12 max-h-40"
              value={input}
              onChange={(event) => updateTyping(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe una nueva búsqueda o pregunta sobre las opciones actuales..."
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-600 sm:w-auto"
            >
              {loading ? "Buscando" : "Enviar"}
            </button>
          </div>
        </div>
        <p className={`mt-2 px-2 text-center text-[11px] leading-5 text-slate-500 sm:mt-3 sm:text-xs transition-opacity duration-300 ${input.trim() ? "opacity-0" : "opacity-100"}`}>
          Urbanest IA usa scraping responsable y muestra solo anuncios reales cuando una fuente responde.
        </p>
      </form>
    </div>
  );
}

export default ChatComposer;
