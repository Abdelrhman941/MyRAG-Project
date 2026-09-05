import { getPublicBackendUrl } from '@/lib/public-backend-url';
import type { SourceCitation } from '@/lib/types';

export type ChatStreamEvent =
  | { type: 'sources'; sources: SourceCitation[] }
  | { type: 'token'; text: string }
  | { type: 'done'; messageId: string }
  | { type: 'error'; code: string; message: string };

type StreamChatOptions = {
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
};

/**
 * Parses a single SSE block into a typed event.
 * Returns null if the block is incomplete or malformed.
 */
function parseEvent(block: string): ChatStreamEvent | null {
  let eventName = '';
  const dataLines: string[] = [];

  // Parse SSE fields (event, data, id, etc.)
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

  let parsedData: unknown;
  try {
    parsedData = JSON.parse(dataLines.join('\n'));
  } catch {
    // Ignore malformed JSON to prevent stream crashes
    return null;
  }

  if (!parsedData || typeof parsedData !== 'object') return null;

  // Map parsed data to strongly typed events
  if (eventName === 'sources' && Array.isArray(parsedData)) {
    return { type: 'sources', sources: parsedData as SourceCitation[] };
  }

  const payload = parsedData as Record<string, unknown>;

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

/**
 * Streams chat responses using Server-Sent Events (SSE).
 * Handles buffering to ensure complete event blocks are processed.
 */
export async function streamChatAnswer(
  sessionId: string,
  question: string,
  { signal, onEvent }: StreamChatOptions
): Promise<void> {
  const response = await fetch(
    `${getPublicBackendUrl()}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages/stream`,
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

  // Read stream chunks and buffer them until a complete SSE block is received
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
