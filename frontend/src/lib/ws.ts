import { API_BASE } from "./api";

export function connectActivitySocket(
  token: string,
  onMessage: (data: Record<string, unknown>) => void
): WebSocket | null {
  if (typeof window === "undefined") return null;
  const wsBase = API_BASE.replace(/^http/, "ws");
  const socket = new WebSocket(`${wsBase}/ws?token=${encodeURIComponent(token)}`);
  socket.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      /* ignore malformed frames */
    }
  };
  return socket;
}
