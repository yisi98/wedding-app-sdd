import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  // True once the persisted session has been read back from storage. Route guards must
  // wait for this before redirecting on a missing token, or a fresh page load / refresh
  // sees the pre-hydration `null` and bounces a logged-in guest to /login.
  hasHydrated: boolean;
  setTokens: (access: string, refresh: string) => void;
  setSession: (access: string, refresh: string, user: User) => void;
  setUser: (user: User) => void;
  clear: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      hasHydrated: false,
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setSession: (access, refresh, user) =>
        set({ accessToken: access, refreshToken: refresh, user }),
      setUser: (user) => set({ user }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "wmp-auth",
      onRehydrateStorage: () => (state) => state?.setHasHydrated(true),
    }
  )
);
