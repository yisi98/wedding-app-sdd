import { create } from "zustand";

export interface Toast {
  id: number;
  event_type: string;
  user: string;
}

interface RealtimeState {
  toasts: Toast[];
  push: (event_type: string, user: string) => void;
  dismiss: (id: number) => void;
}

let counter = 0;

export const useRealtimeStore = create<RealtimeState>((set) => ({
  toasts: [],
  push: (event_type, user) =>
    set((state) => ({ toasts: [...state.toasts, { id: ++counter, event_type, user }] })),
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
