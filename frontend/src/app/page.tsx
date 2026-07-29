"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/stores/auth";

export default function Home() {
  const router = useRouter();
  const token = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    router.replace(token ? "/gallery" : "/login");
  }, [token, router]);

  return null;
}
