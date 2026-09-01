"use client";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
});

export function useApi<T>(url: string, refreshInterval = 0) {
  return useSWR<T>(url, fetcher, { refreshInterval, revalidateOnFocus: false });
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
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
  const r = await fetch(url, {
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
