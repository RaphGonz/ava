import { useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useChatStore } from "../store/chatStore";

export function useChat() {
  const {
    addUserMessage,
    addAssistantMessage,
    appendToken,
    finishStreaming,
    setSessionId,
    sessionId,
    isStreaming,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreaming) return;

      const userMsgId = crypto.randomUUID();
      addUserMessage(userMsgId, content);

      const assistantMsgId = crypto.randomUUID();
      addAssistantMessage(assistantMsgId);

      const token = localStorage.getItem("access_token");

      await fetchEventSource("/api/v1/chat/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content,
          session_id: sessionId,
        }),
        onmessage(event) {
          if (!event.data) return;
          try {
            const data = JSON.parse(event.data);
            if (data.token) {
              appendToken(assistantMsgId, data.token);
            }
            if (data.session_id && !sessionId) {
              setSessionId(data.session_id);
            }
          } catch {
            // ignore parse errors
          }
        },
        onclose() {
          finishStreaming(assistantMsgId);
        },
        onerror(err) {
          finishStreaming(assistantMsgId);
          throw err;
        },
      });
    },
    [
      isStreaming,
      sessionId,
      addUserMessage,
      addAssistantMessage,
      appendToken,
      finishStreaming,
      setSessionId,
    ]
  );

  return { sendMessage };
}
