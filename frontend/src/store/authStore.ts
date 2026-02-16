import { create } from "zustand";
import api from "../api/client";

interface AuthState {
  token: string | null;
  user: {
    id: string;
    email: string;
    username: string | null;
    current_mode: string;
    is_age_verified: boolean;
    is_onboarded: boolean;
  } | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username?: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("access_token"),
  user: null,
  isAuthenticated: !!localStorage.getItem("access_token"),

  login: async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({ token: data.access_token, isAuthenticated: true });
  },

  register: async (email, password, username) => {
    const { data } = await api.post("/auth/register", { email, password, username });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({ token: data.access_token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ token: null, user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    const { data } = await api.get("/auth/me");
    set({ user: data });
  },
}));
