"use client";
import useSWR from "swr";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8088";

const fetcher = (url: string) => fetch(API_BASE + url).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
});

export function useApi<T>(url: string, refreshInterval = 0) {
  return useSWR<T>(url, fetcher, { refreshInterval, revalidateOnFocus: false });
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(API_BASE + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`HTTP ${r.status}: ${err}`);
  }
  return r.json();
}

export async function putJson<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(API_BASE + url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`HTTP ${r.status}: ${err}`);
  }
  return r.json();
}
