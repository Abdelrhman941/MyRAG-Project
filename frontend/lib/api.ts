'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { Document, Message, Session } from './types';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string;
  };
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { error: { code: 'unknown', message: 'An unknown error occurred' } };
    }
    // We cannot throw instances of custom Error subclasses across the RSC boundary natively
    // in Next.js Server Actions sometimes, but throwing a normal Error with added props works
    const e = new Error(errorData.error?.message || 'Unknown error') as Error & {
      status: number;
      data: ApiError;
    };
    e.status = response.status;
    e.data = errorData;
    throw e;
  }

  if (response.status === 204) return null as T;

  return response.json();
}

export async function getSessions(): Promise<Session[]> {
  try {
    // Backend returns { sessions: [...] } — unwrap the envelope
    const data = await apiFetch<{ sessions: Session[] }>('/api/v1/chat/sessions', {
      next: { tags: ['sessions'], revalidate: 0 },
    });
    return data.sessions;
  } catch (e) {
    console.error('Failed to fetch sessions', e);
    return [];
  }
}

export async function getMessages(sessionId: string): Promise<Message[] | null> {
  try {
    // Backend returns { messages: [...] } — unwrap the envelope
    const data = await apiFetch<{ messages: Message[] }>(
      `/api/v1/chat/sessions/${sessionId}/messages`,
      { next: { tags: [`messages-${sessionId}`], revalidate: 0 } }
    );
    return data.messages;
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

export async function getDocuments(sessionId: string): Promise<Document[] | null> {
  try {
    return await apiFetch<Document[]>(`/api/v1/chat/sessions/${sessionId}/documents`, {
      next: { tags: [`documents-${sessionId}`], revalidate: 0 },
    });
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

export async function createSessionAction() {
  let session;
  try {
    session = await apiFetch<Session>('/api/v1/chat/sessions', {
      method: 'POST',
    });
  } catch (e) {
    console.error(e);
    return;
  }
  revalidatePath('/chat');
  redirect(`/chat/${session.id}`);
}

export async function bootstrapSessionAction() {
  const sessions = await getSessions();
  if (sessions && sessions.length > 0) {
    redirect(`/chat/${sessions[0].id}`);
  } else {
    await createSessionAction();
  }
}

export async function deleteSessionAction(
  sessionId: string,
  currentSessionId: string | undefined,
  otherSessions: Session[]
) {
  try {
    await apiFetch(`/api/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
  } catch (e: unknown) {
    return {
      success: false,
      error: (e as { data?: ApiError })?.data?.error || {
        code: 'unknown',
        message: 'Failed to delete session',
      },
    };
  }

  revalidatePath('/chat');

  if (currentSessionId === sessionId) {
    const remaining = otherSessions.filter((s) => s.id !== sessionId);
    if (remaining.length > 0) {
      redirect(`/chat/${remaining[0].id}`);
    } else {
      let newSession;
      try {
        newSession = await apiFetch<Session>('/api/v1/chat/sessions', { method: 'POST' });
        redirect(`/chat/${newSession.id}`);
      } catch {
        redirect('/');
      }
    }
  }
  return { success: true };
}

export async function deleteDocumentAction(documentId: string, sessionId: string) {
  try {
    await apiFetch(`/api/v1/documents/${documentId}`, { method: 'DELETE' });
    revalidatePath(`/chat/${sessionId}/documents`);
    return { success: true };
  } catch (e: unknown) {
    return {
      success: false,
      error: (e as { data?: ApiError })?.data?.error || {
        code: 'unknown',
        message: 'Failed to delete document',
      },
    };
  }
}

export async function uploadBatchAction(sessionId: string, formData: FormData) {
  try {
    const data = await apiFetch<{ results: { ok: boolean; document?: Document }[] }>(
      `/api/v1/chat/sessions/${sessionId}/documents/batch`,
      {
        method: 'POST',
        body: formData,
      }
    );
    const results = data.results?.filter((r) => r.ok && r.document).map((r) => r.document) || [];
    revalidatePath(`/chat/${sessionId}/documents`);
    return { success: true, results };
  } catch (e: unknown) {
    return {
      success: false,
      error: (e as { data?: ApiError })?.data?.error || {
        code: 'unknown',
        message: 'Upload failed',
      },
    };
  }
}

export async function sendMessageAction(sessionId: string, question: string) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = await apiFetch<any>(`/api/v1/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    const message: Message = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: data.answer,
      sources: data.sources,
      created_at: new Date().toISOString(),
    };

    revalidatePath('/chat', 'layout');
    return { success: true, response: message };
  } catch (e: unknown) {
    return {
      success: false,
      error: (e as { data?: ApiError })?.data?.error || {
        code: 'unknown',
        message: 'Failed to send message',
      },
    };
  }
}
