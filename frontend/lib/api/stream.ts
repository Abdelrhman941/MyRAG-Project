import type { SourceCitation } from '@/lib/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export type ChatStreamEvent =
  | { type: 'sources'; sources: SourceCitation[] }
  | { type: 'token'; text: string }
  | { type: 'done'; messageId: string }
  | { type: 'error'; code: string; message: string };

type StreamChatOptions = {
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
};

function parseEvent(block: string): ChatStreamEvent | null {
  let eventName = '';
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;

    const separator = line.indexOf(':');
    if (separator === -1) continue;

    const field = line.slice(0, separator);
    const value = line.slice(separator + 1).replace(/^ /, '');

    if (field === 'event') eventName = value;
    if (field === 'data') dataLines.push(value);
  }

  if (!eventName || dataLines.length === 0) return null;

  const data: unknown = JSON.parse(dataLines.join('\n'));
  if (!data || typeof data !== 'object') return null;
  const payload = data as Record<string, unknown>;

  if (eventName === 'sources' && Array.isArray(data)) {
    return { type: 'sources', sources: data as SourceCitation[] };
  }

  if (eventName === 'token' && typeof payload.text === 'string') {
    return { type: 'token', text: payload.text };
  }

  if (eventName === 'done' && typeof payload.message_id === 'string') {
    return { type: 'done', messageId: payload.message_id };
  }

  if (
    eventName === 'error' &&
    typeof payload.code === 'string' &&
    typeof payload.message === 'string'
  ) {
    return { type: 'error', code: payload.code, message: payload.message };
  }

  return null;
}

/** Streams one chat answer using the backend's SSE contract. */
export async function streamChatAnswer(
  sessionId: string,
  question: string,
  { signal, onEvent }: StreamChatOptions
): Promise<void> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/chat/sessions/${sessionId}/messages/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to start stream (HTTP ${response.status})`);
  }
  if (!response.body) {
    throw new Error('The stream response has no body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const dispatchBlock = (block: string): boolean => {
    const event = parseEvent(block);
    if (!event) return false;

    onEvent(event);
    return event.type === 'done';
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? '';
    for (const block of blocks) {
      if (dispatchBlock(block)) {
        await reader.cancel();
        return;
      }
    }

    if (done) {
      if (buffer.trim()) dispatchBlock(buffer);
      return;
    }
  }
}
