import { useEffect } from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import ModeIndicator from "./ModeIndicator";
import { useChatStore } from "../../store/chatStore";
import { useAuthStore } from "../../store/authStore";
import api from "../../api/client";

export default function ChatWindow() {
  const mode = useChatStore((s) => s.mode);
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);
  const setMode = useChatStore((s) => s.setMode);
  const setLoadingHistory = useChatStore((s) => s.setLoadingHistory);
  const logout = useAuthStore((s) => s.logout);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  // Fetch user profile on mount (to get current_mode)
  useEffect(() => {
    fetchUser().then(() => {
      const currentUser = useAuthStore.getState().user;
      if (currentUser?.current_mode) {
        setMode(currentUser.current_mode as "jarvis" | "her");
      }
    });
  }, [fetchUser, setMode]);

  // Load chat history on mount if we have a session
  useEffect(() => {
    if (!sessionId || messages.length > 0) return;

    let cancelled = false;
    setLoadingHistory(true);

    api
      .get(`/chat/history?session_id=${sessionId}`)
      .then(({ data }) => {
        if (cancelled) return;
        const loaded = data.map((m: { id: string; role: string; content: string; mode: string }) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
        }));
        if (loaded.length > 0) {
          setMessages(loaded);
          // Sync mode from last message
          const lastMode = data[data.length - 1]?.mode;
          if (lastMode) setMode(lastMode as "jarvis" | "her");
        }
      })
      .catch(() => {
        // Session may have been deleted — clear stale ID
        localStorage.removeItem("session_id");
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => { cancelled = true; };
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="flex flex-col h-screen max-w-3xl mx-auto transition-colors duration-500"
      style={
        { "--mode-accent": mode === "her" ? "#d9607a" : "#4a90d9" } as React.CSSProperties
      }
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors duration-500"
            style={{ backgroundColor: "var(--mode-accent)" }}
          >
            A
          </div>
          <span className="font-semibold text-sm">AVA</span>
          <ModeIndicator />
        </div>
        <button
          onClick={logout}
          className="text-xs text-gray-400 hover:text-white px-3 py-1 rounded border border-gray-700 hover:border-gray-500 transition-colors"
        >
          Logout
        </button>
      </header>
      <MessageList />
      <MessageInput />
    </div>
  );
}