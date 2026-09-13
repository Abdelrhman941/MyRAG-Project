'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { getBackendUrl } from './backend-url';
import { Document, Message, Session } from './types';

const BACKEND_URL = getBackendUrl();

interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string;
  };
}

function normalizeApiError(value: unknown): ApiError {
  if (
    value &&
    typeof value === 'object' &&
    'error' in value &&
    value.error &&
    typeof value.error === 'object'
  ) {
    const error = value.error as Record<string, unknown>;
    if (typeof error.code !== 'string' || typeof error.message !== 'string') {
      return { error: { code: 'unknown', message: 'An unknown error occurred' } };
    }

    return {
      error: {
        code: error.code,
        message: error.message,
        ...(typeof error.details === 'string' ? { details: error.details } : {}),
      },
    };
  }

  return { error: { code: 'unknown', message: 'An unknown error occurred' } };
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
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    const apiError = normalizeApiError(errorData);
    // Server Actions can serialize normal Errors but not custom subclasses.
    const e = new Error(apiError.error.message) as Error & {
      status: number;
      data: ApiError;
    };
    e.status = response.status;
    e.data = apiError;
    throw e;
  }

  if (response.status === 204) return null as T;

  return response.json();
}

export async function getSessions(): Promise<Session[]> {
  // Backend failures must reach the route error boundary instead of rendering an empty sidebar.
  const data = await apiFetch<{ sessions: Session[] }>('/api/v1/chat/sessions', {
    next: { tags: ['sessions'], revalidate: 0 },
  });
  return data.sessions;
}

export async function getSession(sessionId: string): Promise<Session | null> {
  try {
    return await apiFetch<Session>(
      `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}`,
      { next: { tags: [`session-${sessionId}`], revalidate: 0 } }
    );
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

export async function getMessages(sessionId: string): Promise<Message[] | null> {
  try {
    // Backend returns { messages: [...] } — unwrap the envelope
    const data = await apiFetch<{ messages: Message[] }>(
      `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
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
    return await apiFetch<Document[]>(
      `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/documents`,
      {
        next: { tags: [`documents-${sessionId}`], revalidate: 0 },
      }
    );
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

export async function createSession(): Promise<Session> {
  return apiFetch<Session>('/api/v1/chat/sessions', {
    method: 'POST',
  });
}

export async function createSessionAction() {
  let session;
  try {
    session = await createSession();
  } catch (e) {
    console.error(e);
    return;
  }
  revalidatePath('/chat');
  redirect(`/chat/${session.id}`);
}

export async function deleteSessionAction(
  sessionId: string,
  currentSessionId: string | undefined,
  otherSessions: Session[],
  force: boolean = false
) {
  try {
    await apiFetch(
      `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}${force ? '?force=true' : ''}`,
      { method: 'DELETE' }
    );
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
      } catch {
        redirect('/');
      }
      redirect(`/chat/${newSession.id}`);
    }
  }
  return { success: true };
}

export async function deleteDocumentAction(documentId: string, sessionId: string) {
  try {
    await apiFetch(`/api/v1/documents/${encodeURIComponent(documentId)}`, { method: 'DELETE' });
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

export async function retryDocumentAction(documentId: string, sessionId: string) {
  try {
    await apiFetch(`/api/v1/documents/${encodeURIComponent(documentId)}/retry`, { method: 'POST' });
    revalidatePath(`/chat/${sessionId}/documents`);
    return { success: true };
  } catch (e: unknown) {
    return {
      success: false,
      error: (e as { data?: ApiError })?.data?.error || {
        code: 'unknown',
        message: 'Failed to retry document',
      },
    };
  }
}

export async function getReadyStatusAction(): Promise<{ status: string; detail?: string }> {
  const url = `${BACKEND_URL}/readyz`;
  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      if (response.status === 503) {
        return await response.json();
      }
      return { status: 'error', detail: `HTTP error ${response.status}` };
    }
    return await response.json();
  } catch (e: unknown) {
    return { status: 'error', detail: (e as Error).message || 'Connection failed' };
  }
}

export async function revalidateSessionsAction() {
  revalidatePath('/chat');
}
