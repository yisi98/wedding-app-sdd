import { create } from "zustand";

export interface Toast {
  id: number;
  event_type: string;
  user: string;
}

interface RealtimeState {
  toasts: Toast[];
  /** Bumped on every new_upload event, so views can refresh themselves rather than
   * telling a guest something arrived and then not showing it until a manual reload. */
  uploadTick: number;
  push: (event_type: string, user: string) => void;
  dismiss: (id: number) => void;
}

let counter = 0;

export const useRealtimeStore = create<RealtimeState>((set) => ({
  toasts: [],
  uploadTick: 0,
  push: (event_type, user) =>
    set((state) => ({
      toasts: [...state.toasts, { id: ++counter, event_type, user }],
      uploadTick: state.uploadTick + (event_type === "new_upload" ? 1 : 0),
    })),
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
