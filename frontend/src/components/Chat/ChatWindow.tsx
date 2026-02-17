import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import ModeIndicator from "./ModeIndicator";
import { useChatStore } from "../../store/chatStore";
import { useAuthStore } from "../../store/authStore";

export default function ChatWindow() {
  const mode = useChatStore((s) => s.mode);
  const logout = useAuthStore((s) => s.logout);

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
