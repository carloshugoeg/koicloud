import { create } from "zustand";
import type { components } from "@/api/schema";

type User = components["schemas"]["UserOut"];

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  user: User;
}

interface AuthState {
  session: AuthSession | null;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
  updateTokens: (tokens: {
    accessToken: string;
    refreshToken?: string;
  }) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  setSession: (session) => set({ session }),
  clearSession: () => set({ session: null }),
  updateTokens: ({ accessToken, refreshToken }) => {
    const current = get().session;
    if (!current) {
      return;
    }

    set({
      session: {
        ...current,
        accessToken,
        refreshToken: refreshToken ?? current.refreshToken,
      },
    });
  },
}));

export function hasRole(user: User | null | undefined, role: User["role"]) {
  return user?.role === role;
}
