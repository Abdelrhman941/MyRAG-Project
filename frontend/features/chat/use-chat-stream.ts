'use client';

import { revalidateSessionsAction } from '@/lib/api';
import { streamChatAnswer, type ChatStreamEvent } from '@/lib/api/stream';
import type { Message, SourceCitation } from '@/lib/types';
import { useCallback, useEffect, useRef, useState } from 'react';

// --- Types ---

export type StreamPhase = 'idle' | 'retrieving' | 'generating';

export type ChatStreamMessage = Message & {
  clientId: string;
};

// --- Helpers ---

function makeClientId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function withClientIds(messages: Message[]): ChatStreamMessage[] {
  return messages.map((message, index) => ({
    ...message,
    clientId: `message-${message.id ?? index}`,
  }));
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

// --- Hook ---

export function useChatStream(initialMessages: Message[], sessionId: string) {
  const [messages, setMessages] = useState<ChatStreamMessage[]>(() =>
    withClientIds(initialMessages)
  );
  const [phase, setPhase] = useState<StreamPhase>('idle');
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  // Stop the current stream
  const stop = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  // Send a new message and handle the streaming lifecycle
  const send = useCallback(
    async (question: string) => {
      if (!question.trim() || controllerRef.current) return;

      const controller = new AbortController();
      const userClientId = makeClientId('user');
      const assistantClientId = makeClientId('assistant');

      let pendingSources: SourceCitation[] = [];
      let streamStarted = false;
      let assistantCreated = false;

      // Track if this is the very first message in the session for sidebar revalidation
      const isFirstExchange = messages.length === 0;

      const ensureAssistant = () => {
        if (assistantCreated) return;
        setMessages((current) => [
          ...current,
          {
            id: assistantClientId,
            clientId: assistantClientId,
            role: 'assistant',
            content: '',
            sources: pendingSources,
            created_at: new Date().toISOString(),
          },
        ]);
        assistantCreated = true;
      };

      const handleEvent = (event: ChatStreamEvent) => {
        streamStarted = true;

        if (event.type === 'sources') {
          pendingSources = event.sources;
          setPhase('generating');
          return;
        }

        if (event.type === 'token') {
          ensureAssistant();
          setPhase('generating');
          setMessages((current) =>
            current.map((message) =>
              message.clientId === assistantClientId
                ? { ...message, content: message.content + event.text, sources: pendingSources }
                : message
            )
          );
          return;
        }

        if (event.type === 'done') {
          ensureAssistant();
          setMessages((current) => {
            // Revalidate sidebar only for the first exchange to fetch the auto-generated title
            if (isFirstExchange) {
              void revalidateSessionsAction().catch(() => {
                // Fire-and-forget: sidebar will update on next navigation
              });
            }
            return current.map((message) =>
              message.clientId === assistantClientId ? { ...message, id: event.messageId } : message
            );
          });
          return;
        }

        // Handle stream errors
        ensureAssistant();
        setMessages((current) =>
          current.map((message) =>
            message.clientId === assistantClientId ? { ...message, error: event.message } : message
          )
        );
      };

      // Optimistic UI: Add user message immediately
      setMessages((current) => [
        ...current,
        {
          id: userClientId,
          clientId: userClientId,
          role: 'user',
          content: question,
          created_at: new Date().toISOString(),
        },
      ]);

      controllerRef.current = controller;
      setPhase('retrieving');
      setIsStreaming(true);

      try {
        await streamChatAnswer(sessionId, question, {
          signal: controller.signal,
          onEvent: handleEvent,
        });
      } catch (error) {
        if (!isAbortError(error) && !streamStarted) {
          // Remove user message if stream failed before starting
          setMessages((current) => current.filter((message) => message.clientId !== userClientId));
        } else if (!isAbortError(error)) {
          // Show error on the assistant message if stream was interrupted
          ensureAssistant();
          setMessages((current) =>
            current.map((message) =>
              message.clientId === assistantClientId
                ? { ...message, error: 'Connection failed or stream interrupted.' }
                : message
            )
          );
        }
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null;
          setPhase('idle');
          setIsStreaming(false);
        }
      }
    },
    [sessionId, messages.length] // Added messages.length to accurately track isFirstExchange
  );

  // Cleanup: Abort ongoing stream if sessionId changes (e.g., user switches chats)
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
        controllerRef.current = null;
      }
    };
  }, [sessionId]);

  return { messages, phase, isStreaming, send, stop };
}
