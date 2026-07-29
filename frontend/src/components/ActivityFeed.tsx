"use client";

import { useEffect } from "react";

import { api } from "@/lib/api";
import { connectActivitySocket } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth";
import { useRealtimeStore } from "@/stores/realtime";

// Opens the WebSocket and surfaces live events as toasts (US6).
export default function ActivityFeed() {
  const token = useAuthStore((s) => s.accessToken);
  const push = useRealtimeStore((s) => s.push);

  useEffect(() => {
    if (!token) return;
    // Prime with recent activity (fire-and-forget).
    api.get("/activity").catch(() => {});
    const socket = connectActivitySocket(token, (data) => {
      if (data.event_type && data.user) {
        push(String(data.event_type), String(data.user));
      }
    });
    return () => socket?.close();
  }, [token, push]);

  return null;
}
