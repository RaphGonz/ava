import { useEffect, useState } from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import ModeIndicator from "./ModeIndicator";
import SettingsPopup from "./SettingsPopup";
import { useChatStore } from "../../store/chatStore";
import { useAuthStore } from "../../store/authStore";
import api from "../../api/client";

function CogIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default function ChatWindow() {
  const mode = useChatStore((s) => s.mode);
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);
  const setMode = useChatStore((s) => s.setMode);
  const setLoadingHistory = useChatStore((s) => s.setLoadingHistory);
  const logout = useAuthStore((s) => s.logout);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [showSettings, setShowSettings] = useState(false);

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
        const loaded = data.map((m: { id: string; role: string; content: string; mode: string; image_urls: string[] | null }) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          images: m.image_urls || undefined,
        }));
        if (loaded.length > 0) {
          setMessages(loaded);
          const lastMode = data[data.length - 1]?.mode;
          if (lastMode) setMode(lastMode as "jarvis" | "her");
        }
      })
      .catch(() => {
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
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(true)}
            className="text-gray-400 hover:text-white p-1.5 rounded border border-gray-700 hover:border-gray-500 transition-colors"
            title="Settings"
          >
            <CogIcon />
          </button>
          <button
            onClick={logout}
            className="text-xs text-gray-400 hover:text-white px-3 py-1 rounded border border-gray-700 hover:border-gray-500 transition-colors"
          >
            Logout
          </button>
        </div>
      </header>
      <MessageList />
      <MessageInput />
      {showSettings && <SettingsPopup onClose={() => setShowSettings(false)} />}
    </div>
  );
}
