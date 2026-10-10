import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { withDeadline } from "./deadline";

let client: SupabaseClient | null = null;
export const configured = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL &&
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
);
export const apiBase = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
export function supabase() {
  if (!configured)
    throw new Error(
      "Workspace authentication is being configured. Please try again shortly.",
    );
  if (!client)
    client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      },
    );
  return client;
}
export async function authHeaders() {
  const { data, error } = await withDeadline(
    supabase().auth.getSession(),
    15000,
    "Your session is taking too long to respond. Please retry or sign in again.",
  );
  if (error || !data.session) throw new Error("Please sign in to continue.");
  let session = data.session;
  if ((session.expires_at || 0) * 1000 < Date.now() + 60000) {
    const refreshed = await withDeadline(
      supabase().auth.refreshSession(),
      15000,
      "Your session could not be refreshed. Please retry or sign in again.",
    );
    if (refreshed.error || !refreshed.data.session)
      throw new Error("Your session expired. Please sign in again.");
    session = refreshed.data.session;
  }
  return { Authorization: `Bearer ${session.access_token}` };
}
export async function api<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 60000, signal, ...requestOptions } = options;
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener("abort", cancel, { once: true });
  if (signal?.aborted) controller.abort();
  async function request(): Promise<T> {
    const headers = await authHeaders();
    const result = await fetch(apiBase + path, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        ...headers,
        ...(options.body && !(options.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    });
    if (!result.ok) {
      const error = await result.json().catch(() => ({
        detail: "Could not reach your workspace. Please retry.",
      }));
      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : "The request could not be completed.",
      );
    }
    return result.json();
  }
  try {
    return await withDeadline(
      request(),
      timeoutMs,
      "The workspace service is taking too long to respond. Please retry in a moment.",
    );
  } finally {
    controller.abort();
    signal?.removeEventListener("abort", cancel);
  }
}
export type Workspace = {
  id: string;
  name: string;
  role: "admin" | "employee";
  is_demo?: boolean;
  demo_slug?: string;
  demo_region?: "India" | "Global";
};
export type CompanyDocument = {
  id: string;
  name: string;
  mime_type: string;
  size_bytes: number;
  collection: string;
  status: string;
  error_message?: string;
  chunk_count: number;
  total_pages?: number;
  processed_pages?: number;
  index_total_chunks?: number;
  index_completed_chunks?: number;
  indexing_version?: string;
  extraction_note?: string;
  created_at: string;
};
export type Citation = {
  id: string;
  number: number;
  document_id: string;
  document_name: string;
  content: string;
  location: {
    label: string;
    page?: number;
    kind?: string;
    source_url?: string;
    original_page?: number;
    original_document?: string;
  };
  collection: string;
};
export type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  model?: string;
  error?: string;
  workspace_id?: string;
  workspace_name?: string;
  is_demo?: boolean;
};
export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at?: string;
};
export type Member = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
};
