'use client';

import { useDocuments } from '@/hooks/use-documents';
import { sendMessageAction, getRagPhaseAction } from '@/lib/api';
import { useEffect, useRef, useState } from 'react';
import { AgentChat, AgentMessage, RagPhase } from './ui/agent-chat';

export function MessageFeed({
  initialMessages,
  sessionId,
}: {
  initialMessages: import('@/lib/types').Message[];
  sessionId: string;
}) {
  const [messages, setMessages] = useState<import('@/lib/types').Message[]>(initialMessages);
  const [isPending, setIsPending] = useState(false);

  const { uploadFiles, isUploading } = useDocuments(sessionId);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Poll the backend RAG phase while a response is in-flight.
  // Stops automatically when isPending becomes false (response arrived).
  const [polledPhase, setPolledPhase] = useState<RagPhase>('idle');
  // Derive displayed phase: always 'idle' when not waiting for a response
  const ragPhase: RagPhase = isPending ? polledPhase : 'idle';

  useEffect(() => {
    if (!isPending) return;

    const poll = async () => {
      try {
        const phase = await getRagPhaseAction(sessionId);
        setPolledPhase(phase as RagPhase);
      } catch {
        // Network blip — keep previous phase, will retry
      }
    };

    // Poll immediately then every 300ms
    poll();
    const interval = setInterval(poll, 300);
    return () => clearInterval(interval);
  }, [isPending, sessionId]);

  // Convert internal messages to AgentMessage format
  const agentMessages: AgentMessage[] = messages.map((m, idx) => {
    let content = m.content;
    if (m.sources && m.sources.length > 0) {
      content +=
        '\n\n**Sources:**\n' +
        m.sources.map((s: { document_name: string }) => `- ${s.document_name}`).join('\n');
    }

    if (m.error) {
      return {
        id: m.id || `msg-${idx}`,
        role: m.role,
        parts: [{ type: 'error', title: 'Error', message: m.error }],
      };
    }

    return {
      id: m.id || `msg-${idx}`,
      role: m.role,
      parts: [{ type: 'text', text: content }],
    };
  });

  const handleSend = async (message: { role: 'user'; content: string }) => {
    const question = message.content;
    if (!question.trim()) return;

    const tempUserMessage = {
      id: `temp-${Date.now()}`,
      role: 'user' as const,
      content: question,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMessage]);
    setIsPending(true);

    const result = await sendMessageAction(sessionId, question);

    setIsPending(false);
    if (!result.success) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant' as const,
          content: 'Sorry, I encountered an error generating the response.',
          error: result.error?.message,
        },
      ]);
    } else {
      setMessages((prev) => {
        const exists = prev.find((m) => m.id === result.response?.id);
        if (exists) return prev;
        return result.response ? [...prev, result.response] : prev;
      });
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await uploadFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="flex flex-col h-full bg-background dark:bg-[#212121]">
      <input
        type="file"
        multiple
        className="hidden"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.txt,.md,.docx"
      />
      <AgentChat
        messages={agentMessages}
        status={isPending ? 'streaming' : 'ready'}
        ragPhase={ragPhase}
        onSend={handleSend}
        emptyStatePosition="center"
        attachments={{
          onAttach: () => fileInputRef.current?.click(),
          isUploading,
        }}
      />
    </div>
  );
}
