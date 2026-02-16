import { create } from "zustand";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  images?: string[];
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isStreaming: boolean;
  mode: "jarvis" | "her";
  addUserMessage: (id: string, content: string) => void;
  addAssistantMessage: (id: string) => void;
  appendToken: (id: string, token: string) => void;
  finishStreaming: (id: string) => void;
  setSessionId: (id: string) => void;
  setMode: (mode: "jarvis" | "her") => void;
  setMessageImages: (id: string, images: string[]) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isStreaming: false,
  mode: "jarvis",

  addUserMessage: (id, content) =>
    set((state) => ({
      messages: [...state.messages, { id, role: "user", content }],
    })),

  addAssistantMessage: (id) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "assistant", content: "", isStreaming: true },
      ],
      isStreaming: true,
    })),

  appendToken: (id, token) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    })),

  finishStreaming: (id) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m
      ),
      isStreaming: false,
    })),

  setSessionId: (id) => set({ sessionId: id }),

  setMode: (mode) => set({ mode }),

  setMessageImages: (id, images) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, images } : m
      ),
    })),

  clearMessages: () => set({ messages: [], sessionId: null }),
}));
