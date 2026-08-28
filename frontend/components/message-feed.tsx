'use client';

import { useDocuments } from '@/hooks/use-documents';
import { getRagPhaseAction, getReadyStatusAction } from '@/lib/api';
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

  const [polledPhase, setPolledPhase] = useState<RagPhase>('idle');
  const ragPhase: RagPhase = isPending ? polledPhase : 'idle';

  const [modelReady, setModelReady] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  useEffect(() => {
    if (modelReady) return;

    let isCancelled = false;
    const pollModelReady = async () => {
      try {
        const res = await getReadyStatusAction();
        if (isCancelled) return;

        if (res.status === 'ready') {
          setModelReady(true);
          setModelError(null);
        } else if (res.status === 'warming') {
          setModelError(null);
        } else {
          setModelError(res.detail || 'Failed to load model');
        }
      } catch (e: unknown) {
        if (!isCancelled) setModelError((e as Error).message || 'Connection failed');
      }
    };

    pollModelReady();
    const interval = setInterval(() => {
      if (!modelReady && !modelError) {
        pollModelReady();
      }
    }, 2000);

    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, [modelReady, modelError]);

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

    poll();
    const interval = setInterval(poll, 300);
    return () => clearInterval(interval);
  }, [isPending, sessionId]);

  const agentMessages: AgentMessage[] = messages.map((m, idx) => {
    let content = m.content;
    if (m.sources && m.sources.length > 0) {
      content +=
        '\n\n**Sources:**\n' +
        m.sources.map((s: any) => {
          const meta = [
            s.page_number ? `p.${s.page_number}` : null,
            s.section ? `§ ${s.section}` : null
          ].filter(Boolean).join(', ');
          const name = s.original_file_name || s.document_name || 'Unknown Document';
          return `- ${name}${meta ? ` (${meta})` : ''}`;
        }).join('\n');
    }

    const parts: any[] = [];
    if (content.trim()) {
      parts.push({ type: 'text', text: content });
    }

    if (m.error) {
      parts.push({ type: 'error', title: 'Error', message: m.error });
    }

    // If we have neither content nor error but it's an assistant message, we should at least have an empty text part so the bubble renders, unless we strictly rely on shimmer.
    if (parts.length === 0) {
      parts.push({ type: 'text', text: '' });
    }

    return {
      id: m.id || `msg-${idx}`,
      role: m.role,
      parts,
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
    const assistantMessageId = `assistant-${Date.now()}`;

    setMessages((prev) => [...prev, tempUserMessage]);
    setIsPending(true);

    let assistantMessageCreated = false;
    const ensureAssistantMessage = () => {
      if (!assistantMessageCreated) {
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            sources: [],
            created_at: new Date().toISOString(),
          }
        ]);
        assistantMessageCreated = true;
      }
    };

    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${BACKEND_URL}/api/v1/chat/sessions/${sessionId}/messages/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error('Failed to start stream');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');

        // Keep the last partial chunk in the buffer
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          const lines = eventBlock.split('\n');
          let eventName = 'message';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventName = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.substring(6).trim();
            } else if (line === ': ping') {
              eventName = 'ping';
            }
          }

          if (eventName === 'ping') continue;

          try {
            const parsed = JSON.parse(eventData);
            if (eventName === 'sources') {
              ensureAssistantMessage();
              setMessages((prev) => prev.map((m) =>
                m.id === assistantMessageId ? { ...m, sources: parsed } : m
              ));
            } else if (eventName === 'token') {
              ensureAssistantMessage();
              setMessages((prev) => prev.map((m) =>
                m.id === assistantMessageId ? { ...m, content: m.content + parsed.text } : m
              ));
            } else if (eventName === 'done') {
              ensureAssistantMessage();
              // Finalize message with actual backend ID
              setMessages((prev) => prev.map((m) =>
                m.id === assistantMessageId ? { ...m, id: parsed.message_id } : m
              ));
            } else if (eventName === 'error') {
              ensureAssistantMessage();
              setMessages((prev) => prev.map((m) =>
                m.id === assistantMessageId ? { ...m, error: parsed.message } : m
              ));
            }
          } catch (e) {
            console.error('Failed to parse SSE JSON:', eventData);
          }
        }
      }
    } catch (e) {
      console.error(e);
      ensureAssistantMessage();
      setMessages((prev) => prev.map((m) =>
        m.id === assistantMessageId
          ? { ...m, error: 'Connection failed or stream interrupted.' }
          : m
      ));
    } finally {
      setIsPending(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await uploadFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="flex flex-col h-full bg-background dark:bg-[#212121] relative">
      <input
        type="file"
        multiple
        className="hidden"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.txt,.md,.docx"
      />

      {!modelReady && !modelError && (
        <div className="absolute top-0 left-0 right-0 bg-blue-500/10 text-blue-700 dark:text-blue-400 p-3 text-center text-sm flex items-center justify-center gap-3 z-10 border-b border-blue-500/20 backdrop-blur-sm">
          <div className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
          Loading the AI model — first boot can take a minute…
        </div>
      )}

      {modelError && (
        <div className="absolute top-0 left-0 right-0 bg-red-500/10 text-red-700 dark:text-red-400 p-3 text-center text-sm flex items-center justify-center gap-3 z-10 border-b border-red-500/20 backdrop-blur-sm">
          <span>Failed to load AI model: {modelError}</span>
          <button onClick={() => { setModelError(null); setModelReady(false); }} className="underline font-semibold hover:text-red-800 dark:hover:text-red-300">
            Retry
          </button>
        </div>
      )}

      <AgentChat
        messages={agentMessages}
        status={isPending ? 'streaming' : 'ready'}
        ragPhase={ragPhase}
        onSend={handleSend}
        emptyStatePosition="center"
        disabled={!modelReady}
        placeholder={!modelReady ? 'Waiting for model...' : 'Message...'}
        attachments={{
          onAttach: () => fileInputRef.current?.click(),
          isUploading,
        }}
      />
    </div>
  );
}
