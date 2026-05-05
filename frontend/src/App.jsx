import { useEffect, useRef, useState } from "react";
import AppShell from "./components/AppShell";
import ChatComposer from "./components/ChatComposer";
import ChatMessage from "./components/ChatMessage";
import ChatResultsBlock from "./components/ChatResultsBlock";
import ConversationHeader from "./components/ConversationHeader";
import EmptyConversation from "./components/EmptyConversation";
import Sidebar from "./components/Sidebar";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const STORAGE_KEY = "urbanest_ia_state";

const SUGGESTED_PROMPTS = [
  "Busca apartamentos en Manga entre 1.5 y 2.5 millones con 2 habitaciones",
  "Quiero casas en Crespo hasta 3 millones con 3 habitaciones y 2 baños",
  "Muéstrame apartaestudios en Bocagrande amoblados por menos de 2.2 millones",
];

const isLargeScreen = () =>
  typeof window === "undefined" ? true : window.matchMedia("(min-width: 1024px)").matches;

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [results, setResults] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [parsedQuery, setParsedQuery] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(isLargeScreen);
  const [isTyping, setIsTyping] = useState(false);
  const pollRef = useRef(null);
  const conversationRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const saved = JSON.parse(stored);
        setMessages(saved.messages || []);
        setResults(saved.results || []);
        setAnalysis(saved.analysis || null);
        setParsedQuery(saved.parsedQuery || null);
      }
    } catch (error) {
      console.warn("No se pudo cargar el historial de chat:", error);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ messages, results, analysis, parsedQuery }),
      );
    } catch (error) {
      console.warn("No se pudo guardar el historial de chat:", error);
    }
  }, [messages, results, analysis, parsedQuery]);

  useEffect(() => {
    const node = conversationRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  const appendMessage = (message) => {
    const nextMessage = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      kind: "text",
      ...message,
    };
    setMessages((prev) => [
      ...prev,
      nextMessage,
    ]);
    return nextMessage.id;
  };

  const updateMessage = (messageId, patch) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === messageId
          ? {
              ...message,
              ...patch,
            }
          : message,
      ),
    );
  };

  const pollJob = (currentJobId, pendingMessageId) => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
    }

    pollRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/jobs/${currentJobId}`);
        const data = await response.json();

        if (data.status === "parsing") {
          updateMessage(pendingMessageId, {
            content: "",
            subtle: true,
          });
        }

        if (data.status === "scraping") {
          updateMessage(pendingMessageId, {
            content: "",
            subtle: true,
          });
        }

        if (data.status === "completed") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          setResults(data.results || []);
          setAnalysis(data.analysis || null);
          setParsedQuery(data.parsed_query || null);
          updateMessage(pendingMessageId, {
            content:
              data.reply ||
              (data.results?.length > 0
                ? `Encontré ${data.results.length} opciones y ya te las organicé aquí mismo para que podamos compararlas.`
                : "Terminé el rastreo, pero no aparecieron resultados para esos criterios."),
            subtle: false,
            kind: data.results?.length > 0 ? "results" : "text",
            payload:
              data.results?.length > 0
                ? {
                    parsedQuery: data.parsed_query,
                    analysis: data.analysis,
                    results: data.results,
                  }
                : null,
          });
        }

        if (data.status === "failed") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          updateMessage(pendingMessageId, {
            content: `El rastreo falló: ${data.error_message || "error desconocido"}.`,
            subtle: false,
          });
        }
      } catch {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setLoading(false);
        updateMessage(pendingMessageId, {
          content: "No pude consultar el estado del job. Revisa si el backend sigue arriba.",
          subtle: false,
        });
      }
    }, 2500);
  };

  const handleSearch = async (message) => {
    appendMessage({ role: "user", content: message });
    setLoading(true);
    const pendingMessageId = appendMessage({
      role: "assistant",
      content: "",
      subtle: true,
    });

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          properties: results,
          parsed_query: parsedQuery,
          analysis,
        }),
      });
      const data = await response.json();

      if (data.job_id) {
        setJobId(data.job_id);
        setResults([]);
        setAnalysis(null);
        setParsedQuery(data.parsed_query || null);
        updateMessage(pendingMessageId, {
          content: "",
          subtle: true,
        });
        pollJob(data.job_id, pendingMessageId);
        return;
      }

      setLoading(false);
      setJobId(null);
      updateMessage(pendingMessageId, {
        content: data.reply,
        subtle: false,
      });
    } catch {
      setLoading(false);
      setJobId(null);
      updateMessage(pendingMessageId, {
        content: "No pude iniciar la búsqueda. Revisa la conexión con el backend.",
        subtle: false,
      });
    }
  };

  return (
    <AppShell
      sidebar={
        <Sidebar
          history={messages}
          onPromptClick={handleSearch}
          onClearHistory={() => {
            setMessages([]);
            setResults([]);
            setAnalysis(null);
            setParsedQuery(null);
            setIsTyping(false);
            window.localStorage.removeItem(STORAGE_KEY);
          }}
          loading={loading}
        />
      }
      main={
        <div className="flex min-h-screen flex-col bg-[#343541]">
          <ConversationHeader
            loading={loading}
            jobId={jobId}
            resultCount={results.length}
          />

          <div
            ref={conversationRef}
            className="flex-1 overflow-y-auto pb-36"
          >
            <div className="mx-auto flex w-full max-w-3xl flex-col">
{messages.length === 0 && !loading ? (
            <EmptyConversation
              prompts={SUGGESTED_PROMPTS}
              onPromptClick={handleSearch}
              isTyping={isTyping}
            />
              ) : null}

              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id || `${message.role}-${index}`}
                  role={message.role}
                  content={message.content}
                  subtle={message.subtle}
                >
                  {message.kind === "results" ? (
                    <ChatResultsBlock
                      parsedQuery={message.payload?.parsedQuery}
                      analysis={message.payload?.analysis}
                      results={message.payload?.results || []}
                      onPromptClick={handleSearch}
                    />
                  ) : null}
                </ChatMessage>
              ))}
            </div>
          </div>

          <ChatComposer onSend={handleSearch} onTyping={setIsTyping} loading={loading} />
        </div>
      }
      sidebarOpen={sidebarOpen}
      onOpenSidebar={() => setSidebarOpen(true)}
      onCloseSidebar={() => setSidebarOpen(false)}
    />
  );
}

export default App;
