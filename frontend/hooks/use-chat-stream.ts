'use client';

import { streamChatAnswer, type ChatStreamEvent } from '@/lib/api/stream';
import type { Message, SourceCitation } from '@/lib/types';
import { useCallback, useRef, useState } from 'react';

export type StreamPhase = 'idle' | 'retrieving' | 'generating';

export type ChatStreamMessage = Message & {
  clientId: string;
  stopped?: boolean;
};

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
  return error instanceof DOMException && error.name === 'AbortError';
}

export function useChatStream(initialMessages: Message[], sessionId: string) {
  const [messages, setMessages] = useState<ChatStreamMessage[]>(() =>
    withClientIds(initialMessages)
  );
  const [phase, setPhase] = useState<StreamPhase>('idle');
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const activeAssistantRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    const assistantClientId = activeAssistantRef.current;
    if (assistantClientId) {
      setMessages((current) =>
        current.map((message) =>
          message.clientId === assistantClientId ? { ...message, stopped: true } : message
        )
      );
    }
    controllerRef.current?.abort();
  }, []);

  const send = useCallback(
    async (question: string) => {
      if (!question.trim() || controllerRef.current) return;

      const controller = new AbortController();
      const userClientId = makeClientId('user');
      const assistantClientId = makeClientId('assistant');
      let pendingSources: SourceCitation[] = [];
      let streamStarted = false;
      let assistantCreated = false;

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
          setPhase('retrieving');
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
          setMessages((current) =>
            current.map((message) =>
              message.clientId === assistantClientId ? { ...message, id: event.messageId } : message
            )
          );
          return;
        }

        ensureAssistant();
        setMessages((current) =>
          current.map((message) =>
            message.clientId === assistantClientId ? { ...message, error: event.message } : message
          )
        );
      };

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
      activeAssistantRef.current = assistantClientId;
      setPhase('retrieving');
      setIsStreaming(true);

      try {
        await streamChatAnswer(sessionId, question, {
          signal: controller.signal,
          onEvent: handleEvent,
        });
      } catch (error) {
        if (!isAbortError(error) && !streamStarted) {
          setMessages((current) => current.filter((message) => message.clientId !== userClientId));
        } else if (!isAbortError(error)) {
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
          activeAssistantRef.current = null;
          setPhase('idle');
          setIsStreaming(false);
        }
      }
    },
    [sessionId]
  );

  return { messages, phase, isStreaming, send, stop };
}
