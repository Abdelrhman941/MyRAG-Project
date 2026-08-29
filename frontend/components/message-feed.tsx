'use client';

import { useDocuments } from '@/hooks/use-documents';
import { useChatStream } from '@/hooks/use-chat-stream';
import { useReadiness } from '@/hooks/use-readiness';
import type { Message } from '@/lib/types';
import { useMemo, useRef } from 'react';
import { AgentChat, type AgentMessage } from './ui/agent-chat';

export function MessageFeed({
  initialMessages,
  sessionId,
}: {
  initialMessages: Message[];
  sessionId: string;
}) {
  const { messages, phase, isStreaming, send, stop } = useChatStream(initialMessages, sessionId);

  const { uploadFiles, isUploading } = useDocuments(sessionId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { status: readinessStatus, detail: readinessDetail, retry } = useReadiness();
  const modelReady = readinessStatus === 'ready';
  const modelError = readinessStatus === 'error' ? readinessDetail || 'Failed to load model' : null;
  const isSearchEngineStarting = readinessStatus === 'qdrant_not_ready';

  const agentMessages: AgentMessage[] = useMemo(
    () =>
      messages.map((message) => ({
        id: message.id ?? message.clientId,
        stableId: message.clientId,
        role: message.role,
        sources: message.sources,
        parts: [
          ...(message.content.trim() ? [{ type: 'text' as const, text: message.content }] : []),
          ...(message.error
            ? [{ type: 'error' as const, title: 'Error', message: message.error }]
            : []),
        ],
      })),
    [messages]
  );

  const handleSend = async (message: { role: 'user'; content: string }) => {
    void send(message.content);
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

      {(readinessStatus === 'connecting' || readinessStatus === 'warming') && (
        <div className="absolute top-0 left-0 right-0 bg-blue-500/10 text-blue-700 dark:text-blue-400 p-3 text-center text-sm flex items-center justify-center gap-3 z-10 border-b border-blue-500/20 backdrop-blur-sm">
          <div className="w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
          {readinessStatus === 'connecting'
            ? 'Connecting to server…'
            : 'Loading the AI model — first boot can take a minute…'}
        </div>
      )}

      {modelError && (
        <div className="absolute top-0 left-0 right-0 bg-red-500/10 text-red-700 dark:text-red-400 p-3 text-center text-sm flex items-center justify-center gap-3 z-10 border-b border-red-500/20 backdrop-blur-sm">
          <span>Failed to load AI model: {modelError}</span>
          <button
            onClick={() => {
              retry();
            }}
            className="underline font-semibold hover:text-red-800 dark:hover:text-red-300"
          >
            Retry
          </button>
        </div>
      )}

      {isSearchEngineStarting && (
        <div className="absolute top-0 left-0 right-0 bg-blue-500/10 text-blue-700 dark:text-blue-400 p-3 text-center text-sm z-10 border-b border-blue-500/20 backdrop-blur-sm">
          Search engine is starting…
        </div>
      )}

      <AgentChat
        messages={agentMessages}
        status={isStreaming ? 'streaming' : 'ready'}
        ragPhase={phase}
        onSend={handleSend}
        onStop={stop}
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
