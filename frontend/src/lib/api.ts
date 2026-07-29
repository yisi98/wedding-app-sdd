import axios, { AxiosRequestConfig } from "axios";

import { useAuthStore } from "@/stores/auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
// Base URL where media objects are served (CDN / OSS in prod). Falls back to key path.
export const MEDIA_BASE = process.env.NEXT_PUBLIC_MEDIA_BASE || "";

export function mediaUrl(key: string | null): string {
  if (!key) return "";
  return MEDIA_BASE ? `${MEDIA_BASE}/${key}` : `${API_BASE}/media-object/${key}`;
}

export const api = axios.create({ baseURL: `${API_BASE}/api/v1` });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });
    setTokens(data.access_token, data.refresh_token);
    return data.access_token as string;
  } catch {
    clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` };
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);
