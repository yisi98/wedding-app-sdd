"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/stores/auth";

// Client-side route guard. `ready` stays false until we've confirmed a session,
// which also keeps SSR and first client render in sync (both render nothing).
export function useAuthGuard(requireAdmin = false) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const token = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);

  useEffect(() => {
    // Wait for the persisted session to load before judging the token — otherwise a
    // fresh load/refresh reads the pre-hydration `null` and logs a valid session out.
    if (!hasHydrated) return;
    if (!token) {
      router.replace("/login");
      return;
    }
    if (requireAdmin && user?.role !== "admin") {
      router.replace("/gallery");
      return;
    }
    setReady(true);
  }, [hasHydrated, token, user, requireAdmin, router]);

  return { ready, user };
}
