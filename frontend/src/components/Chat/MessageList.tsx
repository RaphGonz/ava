import { useEffect, useRef } from "react";
import { useChatStore, ChatMessage } from "../../store/chatStore";
import ImageMessage from "./ImageMessage";

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-gray-800 text-gray-100 rounded-bl-md"
        }`}
      >
        {message.images && message.images.length > 0 ? (
          <ImageMessage images={message.images} />
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
        {message.isStreaming && !message.images && (
          <span className="inline-block w-1.5 h-4 ml-0.5 bg-white/70 animate-pulse" />
        )}
      </div>
    </div>
  );
}

export default function MessageList() {
  const messages = useChatStore((s) => s.messages);
  const isLoadingHistory = useChatStore((s) => s.isLoadingHistory);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {isLoadingHistory && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <p className="text-sm animate-pulse">Loading conversation...</p>
        </div>
      )}
      {!isLoadingHistory && messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-2xl font-semibold mb-2">AVA</p>
            <p className="text-sm">Start a conversation</p>
          </div>
        </div>
      )}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
