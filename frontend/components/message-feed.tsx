'use client';

import { useDocuments } from '@/hooks/use-documents';
import { sendMessageAction, getRagPhaseAction, getReadyStatusAction } from '@/lib/api';
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
