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

const createId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const getConversationTitle = (message) => {
  const trimmed = message.trim();
  return trimmed.length > 56 ? `${trimmed.slice(0, 56)}...` : trimmed;
};

const getStoredState = () => {
  const fallback = {
    conversations: [],
    activeConversationId: null,
  };

  if (typeof window === "undefined") {
    return fallback;
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return fallback;
    }

    const saved = JSON.parse(stored);
    if (Array.isArray(saved.conversations)) {
      return {
        conversations: saved.conversations,
        activeConversationId: saved.activeConversationId || saved.conversations[0]?.id || null,
      };
    }

    if (Array.isArray(saved.messages) && saved.messages.length > 0) {
      const firstUserMessage = saved.messages.find((message) => message.role === "user");
      const id = createId();
      return {
        conversations: [
          {
            id,
            title: firstUserMessage?.content ? getConversationTitle(firstUserMessage.content) : "Conversación guardada",
            messages: saved.messages,
            results: saved.results || [],
            analysis: saved.analysis || null,
            parsedQuery: saved.parsedQuery || null,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        ],
        activeConversationId: id,
      };
    }
  } catch (error) {
    console.warn("No se pudo cargar el historial de chat:", error);
  }

  return fallback;
};

function App() {
  const [storedState] = useState(getStoredState);
  const [conversations, setConversations] = useState(storedState.conversations);
  const [activeConversationId, setActiveConversationId] = useState(storedState.activeConversationId);
  const activeConversationIdRef = useRef(storedState.activeConversationId);
  const activeConversation = storedState.conversations.find(
    (conversation) => conversation.id === storedState.activeConversationId,
  );
  const [messages, setMessages] = useState(activeConversation?.messages || []);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [results, setResults] = useState(activeConversation?.results || []);
  const [analysis, setAnalysis] = useState(activeConversation?.analysis || null);
  const [parsedQuery, setParsedQuery] = useState(activeConversation?.parsedQuery || null);
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
    activeConversationIdRef.current = activeConversationId;
  }, [activeConversationId]);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ conversations, activeConversationId }),
      );
    } catch (error) {
      console.warn("No se pudo guardar el historial de chat:", error);
    }
  }, [conversations, activeConversationId]);

  useEffect(() => {
    const node = conversationRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  const updateConversation = (conversationId, patch) => {
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              ...patch,
              updatedAt: Date.now(),
            }
          : conversation,
      ),
    );
  };

  const createConversation = (firstMessage) => {
    const id = createId();
    const now = Date.now();
    const conversation = {
      id,
      title: getConversationTitle(firstMessage),
      messages: [],
      results: [],
      analysis: null,
      parsedQuery: null,
      createdAt: now,
      updatedAt: now,
    };

    setConversations((prev) => [conversation, ...prev]);
    setActiveConversationId(id);
    activeConversationIdRef.current = id;
    setMessages([]);
    setResults([]);
    setAnalysis(null);
    setParsedQuery(null);
    return id;
  };

  const appendMessage = (message, conversationId = activeConversationId) => {
    const nextMessage = {
      id: createId(),
      kind: "text",
      ...message,
    };

    if (conversationId === activeConversationIdRef.current) {
      setMessages((prev) => [
        ...prev,
        nextMessage,
      ]);
    }

    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              messages: [...(conversation.messages || []), nextMessage],
              updatedAt: Date.now(),
            }
          : conversation,
      ),
    );

    return nextMessage.id;
  };

  const updateMessage = (messageId, patch, conversationId = activeConversationId) => {
    const patchMessages = (currentMessages) =>
      currentMessages.map((message) =>
        message.id === messageId ? { ...message, ...patch } : message,
      );

    if (conversationId === activeConversationIdRef.current) {
      setMessages(patchMessages);
    }

    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              messages: patchMessages(conversation.messages || []),
              updatedAt: Date.now(),
            }
          : conversation,
      ),
    );
  };

  const pollJob = (currentJobId, pendingMessageId, conversationId) => {
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
          }, conversationId);
        }

        if (data.status === "scraping") {
          updateMessage(pendingMessageId, {
            content: "",
            subtle: true,
          }, conversationId);
        }

        if (data.status === "completed") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          const nextResults = data.results || [];
          const nextAnalysis = data.analysis || null;
          const nextParsedQuery = data.parsed_query || null;
          if (conversationId === activeConversationIdRef.current) {
            setResults(nextResults);
            setAnalysis(nextAnalysis);
            setParsedQuery(nextParsedQuery);
          }
          updateConversation(conversationId, {
            results: nextResults,
            analysis: nextAnalysis,
            parsedQuery: nextParsedQuery,
          });
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
                    results: nextResults,
                  }
                : null,
          }, conversationId);
        }

        if (data.status === "failed") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          updateMessage(pendingMessageId, {
            content: `El rastreo falló: ${data.error_message || "error desconocido"}.`,
            subtle: false,
          }, conversationId);
        }
      } catch {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setLoading(false);
        updateMessage(pendingMessageId, {
          content: "No pude consultar el estado del job. Revisa si el backend sigue arriba.",
          subtle: false,
        }, conversationId);
      }
    }, 2500);
  };

  const handleSearch = async (message) => {
    const conversationId = activeConversationId || createConversation(message);
    appendMessage({ role: "user", content: message }, conversationId);
    setLoading(true);
    const pendingMessageId = appendMessage({
      role: "assistant",
      content: "",
      subtle: true,
    }, conversationId);

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
        const nextParsedQuery = data.parsed_query || null;
        if (conversationId === activeConversationIdRef.current) {
          setResults([]);
          setAnalysis(null);
          setParsedQuery(nextParsedQuery);
        }
        updateConversation(conversationId, {
          results: [],
          analysis: null,
          parsedQuery: nextParsedQuery,
        });
        updateMessage(pendingMessageId, {
          content: "",
          subtle: true,
        }, conversationId);
        pollJob(data.job_id, pendingMessageId, conversationId);
        return;
      }

      setLoading(false);
      setJobId(null);
      updateMessage(pendingMessageId, {
        content: data.reply,
        subtle: false,
      }, conversationId);
    } catch {
      setLoading(false);
      setJobId(null);
      updateMessage(pendingMessageId, {
        content: "No pude iniciar la búsqueda. Revisa la conexión con el backend.",
        subtle: false,
      }, conversationId);
    }
  };

  const handleSelectConversation = (conversationId) => {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) {
      return;
    }

    setActiveConversationId(conversation.id);
    activeConversationIdRef.current = conversation.id;
    setMessages(conversation.messages || []);
    setResults(conversation.results || []);
    setAnalysis(conversation.analysis || null);
    setParsedQuery(conversation.parsedQuery || null);
    setIsTyping(false);
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    activeConversationIdRef.current = null;
    setMessages([]);
    setResults([]);
    setAnalysis(null);
    setParsedQuery(null);
    setJobId(null);
    setIsTyping(false);
  };

  const handleDeleteConversation = (conversationId) => {
    setConversations((current) => {
      const updated = current.filter((conversation) => conversation.id !== conversationId);
      if (activeConversationIdRef.current === conversationId) {
        const nextConversation = updated[0] || null;
        setActiveConversationId(nextConversation?.id || null);
        activeConversationIdRef.current = nextConversation?.id || null;
        setMessages(nextConversation?.messages || []);
        setResults(nextConversation?.results || []);
        setAnalysis(nextConversation?.analysis || null);
        setParsedQuery(nextConversation?.parsedQuery || null);
        setJobId(null);
        setIsTyping(false);
      }
      return updated;
    });
  };

  const handleClearConversations = () => {
    setConversations([]);
    handleNewConversation();
    window.localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <AppShell
      sidebar={
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onNewConversation={handleNewConversation}
          onClearHistory={handleClearConversations}
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
            className="flex-1 overflow-y-auto"
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
