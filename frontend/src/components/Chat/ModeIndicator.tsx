import { useChatStore } from "../../store/chatStore";

export default function ModeIndicator() {
  const mode = useChatStore((s) => s.mode);
  const isHer = mode === "her";

  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full transition-colors duration-500 ${
        isHer ? "bg-rose-900/50 text-rose-300" : "bg-gray-800 text-gray-500"
      }`}
    >
      {isHer ? "Her" : "Jarvis"}
    </span>
  );
}
