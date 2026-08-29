'use client';

import { Citations } from '@/components/chat/citations';
import type { SourceCitation } from '@/lib/types';
import { clsx, type ClassValue } from 'clsx';
import { ArrowUp, FileText, Paperclip, Square, X } from 'lucide-react';
import { memo, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type ChatStatus = 'ready' | 'streaming' | 'submitted' | 'idle';

/** Describes the current chat-stream phase derived from SSE events. */
export type RagPhase = 'idle' | 'retrieving' | 'generating';

export type MessagePart =
  | { type: 'text'; text: string }
  | { type: 'error'; title?: string; message: string };

export type AgentMessage = {
  id: string;
  /** Client-generated identity that remains stable when the backend ID arrives. */
  stableId: string;
  role: 'user' | 'assistant';
  parts: MessagePart[];
  sources?: SourceCitation[];
};

export type AttachedImage = {
  id: string;
  filename: string;
  url: string;
  size?: number;
};

export type AttachedFile = {
  id: string;
  filename: string;
  size?: number;
};

function ImageChip({ url, onRemove }: { url: string; onRemove?: () => void }) {
  return (
    <div className="relative group rounded-md overflow-hidden bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt="" className="h-10 w-10 object-cover" />
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute top-0 right-0 p-0.5 bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

function FileChip({
  filename,
  onRemove,
}: {
  filename: string;
  size?: number;
  onRemove?: () => void;
}) {
  return (
    <div className="relative group flex items-center gap-2 px-2 py-1 rounded-md bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-xs text-neutral-600 dark:text-neutral-300">
      <FileText size={14} className="text-neutral-500" />
      <span className="truncate max-w-25">{filename}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 p-0.5 text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

export type AgentChatProps = {
  messages: AgentMessage[];
  onSend?: (message: { role: 'user'; content: string }) => void;
  onStop?: () => void;
  status?: ChatStatus;
  ragPhase?: RagPhase;
  error?: { message: string; title?: string };
  emptyStatePosition?: 'default' | 'center';
  attachments?: {
    onAttach?: () => void;
    isUploading?: boolean;
    onDrop?: (files: File[]) => void;
    images?: AttachedImage[];
    files?: AttachedFile[];
    onRemoveImage?: (id: string) => void;
    onRemoveFile?: (id: string) => void;
  };
  className?: string;
  disabled?: boolean;
  placeholder?: string;
};

const SendIcon = () => <ArrowUp className="w-5 h-5" strokeWidth={2.5} />;
const StopIcon = () => <Square className="w-3 h-3 fill-current" />;
const PaperclipIcon = () => <Paperclip className="w-[18px] h-[18px]" />;

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-br-sm bg-neutral-100 dark:bg-[#303030] text-[15px] text-neutral-900 dark:text-neutral-100 whitespace-pre-wrap break-words border dark:border-transparent">
        {text}
      </div>
    </div>
  );
}

const MARKDOWN_PLUGINS = [remarkGfm];

const AssistantText = memo(function AssistantText({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] text-[15px] leading-relaxed text-neutral-800 dark:text-neutral-200 break-words prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-neutral-100 dark:prose-pre:bg-[#202020] prose-pre:border dark:prose-pre:border-neutral-800">
        <ReactMarkdown remarkPlugins={MARKDOWN_PLUGINS}>{text}</ReactMarkdown>
      </div>
    </div>
  );
});

function ErrorBubble({
  title = 'Something went wrong',
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="flex justify-start">
      <div className="border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm rounded-xl">
        <div className="font-medium text-red-700 dark:text-red-400">{title}</div>
        <div className="mt-0.5 text-red-600/80 dark:text-red-400/80">{message}</div>
      </div>
    </div>
  );
}

/** Map backend phase strings to human-readable status text. */
const PHASE_TEXT: Record<string, string> = {
  idle: 'Thinking...',
  retrieving: 'Searching knowledge base...',
  generating: 'Generating response...',
};

function ThinkingBubble({ ragPhase = 'idle' }: { ragPhase?: string }) {
  const text = PHASE_TEXT[ragPhase] ?? PHASE_TEXT.idle;

  return (
    <div className="flex justify-start">
      <div className="relative text-[14px] flex items-center gap-3 px-1">
        <div className="relative flex items-center justify-center w-2 h-2">
          <div className="absolute inset-0 rounded-full bg-neutral-400/50 dark:bg-neutral-500/50 animate-ping [animation-duration:2.5s]" />
          <div className="relative w-1 h-1 rounded-full bg-neutral-500 dark:bg-neutral-400" />
        </div>
        <div className="relative w-[230px] h-[20px]">
          <div
            key={text}
            className={cn(
              'absolute inset-0 transition-opacity duration-200 font-medium',
              'bg-gradient-to-r from-neutral-400 via-neutral-800 to-neutral-400 dark:from-neutral-500 dark:via-neutral-100 dark:to-neutral-500',
              'bg-[length:200%_auto] text-transparent bg-clip-text animate-shimmerText'
            )}
          >
            {text}
          </div>
        </div>
      </div>
    </div>
  );
}

const MessageItem = memo(
  function MessageItem({ message }: { message: AgentMessage }) {
    return (
      <div className="flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
        {message.parts.map((part, index) => {
          if (part.type === 'error') {
            return <ErrorBubble key={index} title={part.title} message={part.message} />;
          }
          if (message.role === 'user') {
            return <UserBubble key={index} text={part.text} />;
          }
          return <AssistantText key={index} text={part.text} />;
        })}
        {message.role === 'assistant' && (
          <Citations
            content={message.parts.find((part) => part.type === 'text')?.text ?? ''}
            sources={message.sources}
          />
        )}
      </div>
    );
  },
  (previous, next) => {
    const previousMessage = previous.message;
    const nextMessage = next.message;

    return (
      previousMessage.stableId === nextMessage.stableId &&
      previousMessage.role === nextMessage.role &&
      previousMessage.sources === nextMessage.sources &&
      previousMessage.parts.length === nextMessage.parts.length &&
      previousMessage.parts.every((part, index) => {
        const nextPart = nextMessage.parts[index];
        return (
          part.type === nextPart.type &&
          (part.type === 'text'
            ? nextPart.type === 'text' && part.text === nextPart.text
            : nextPart.type === 'error' &&
              part.title === nextPart.title &&
              part.message === nextPart.message)
        );
      })
    );
  }
);

const MessageList = memo(function MessageList({
  messages,
  status,
  ragPhase,
}: {
  messages: AgentMessage[];
  status?: ChatStatus;
  ragPhase?: string;
}) {
  const isThinking = status === 'streaming' && messages[messages.length - 1]?.role === 'user';

  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 scroll-smooth custom-scrollbar">
      <div className="mx-auto max-w-3xl flex flex-col gap-6">
        {messages.map((message) => (
          <MessageItem key={message.stableId} message={message} />
        ))}
        {isThinking && (
          <div className="flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <ThinkingBubble ragPhase={ragPhase} />
          </div>
        )}
      </div>
    </div>
  );
});

function InputBar({
  onSend,
  onStop,
  status = 'ready',
  placeholder = 'Message...',
  attachments,
  className,
  value: controlledValue,
  onChange,
  disabled,
}: {
  onSend?: (m: { role: 'user'; content: string }) => void;
  onStop?: () => void;
  status?: ChatStatus;
  placeholder?: string;
  attachments?: AgentChatProps['attachments'];
  className?: string;
  value?: string;
  onChange?: (v: string) => void;
  disabled?: boolean;
}) {
  const [internal, setInternal] = useState('');
  const isControlled = controlledValue !== undefined;
  const input = isControlled ? controlledValue : internal;
  const setInput = useCallback(
    (v: string) => {
      if (isControlled) onChange?.(v);
      else setInternal(v);
    },
    [isControlled, onChange]
  );
  const ref = useRef<HTMLTextAreaElement>(null);
  const isStreaming = status === 'streaming' || status === 'submitted';
  const hasInput = input.trim().length > 0;

  const images = attachments?.images ?? [];
  const files = attachments?.files ?? [];
  const hasContext = images.length > 0 || files.length > 0;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    const next = Math.min(el.scrollHeight, 200);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > 200 ? 'auto' : 'hidden';
  }, [input]);

  const submit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend?.({ role: 'user', content: trimmed });
    setInput('');
  }, [input, isStreaming, disabled, onSend, setInput]);

  return (
    <div className={cn('shrink-0 px-4 pb-4 w-full', className)}>
      <div className="mx-auto max-w-3xl">
        <div
          className="relative cursor-text rounded-3xl bg-white dark:bg-[#303030] shadow-sm border border-neutral-200 dark:border-transparent transition-all has-[textarea:focus]:ring-2 has-[textarea:focus]:ring-neutral-200 dark:has-[textarea:focus]:ring-[#515151]"
          onClick={(e) => {
            if (
              e.target === e.currentTarget ||
              !(e.target as HTMLElement).closest('button, textarea')
            ) {
              ref.current?.focus();
            }
          }}
        >
          <div
            className={cn(
              'grid transition-[grid-template-rows] duration-200 ease-out',
              hasContext ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
            )}
          >
            <div className="overflow-hidden">
              {hasContext && (
                <div className="flex flex-wrap items-center gap-1.5 px-3 pt-3 pb-1">
                  {images.map((img) => (
                    <ImageChip
                      key={img.id}
                      url={img.url}
                      onRemove={
                        attachments?.onRemoveImage
                          ? () => attachments.onRemoveImage!(img.id)
                          : undefined
                      }
                    />
                  ))}
                  {files.map((f) => (
                    <FileChip
                      key={f.id}
                      filename={f.filename}
                      size={f.size}
                      onRemove={
                        attachments?.onRemoveFile
                          ? () => attachments.onRemoveFile!(f.id)
                          : undefined
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="pt-3 pb-1 pr-3 pl-4 min-h-[52px]">
            <textarea
              ref={ref}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className={cn(
                'w-full resize-none bg-transparent border-0 outline-none text-[15px] leading-relaxed text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-500 overflow-hidden custom-scrollbar max-h-[200px]',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
            />
          </div>
          <div className="flex items-center justify-between gap-3 px-2 pt-1 pb-2">
            <div className="flex items-center gap-1 min-w-0">
              {attachments?.onAttach && (
                <button
                  type="button"
                  onClick={attachments.onAttach}
                  disabled={attachments.isUploading}
                  aria-label="Attach"
                  className="inline-flex items-center justify-center w-9 h-9 rounded-full text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-[#404040] transition-colors disabled:opacity-50"
                >
                  {attachments.isUploading ? (
                    <div className="h-4 w-4 rounded-full border-2 border-neutral-400 border-t-transparent animate-spin" />
                  ) : (
                    <PaperclipIcon />
                  )}
                </button>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                aria-label={isStreaming ? 'Stop' : 'Send'}
                onClick={() => {
                  if (isStreaming) onStop?.();
                  else if (hasInput) submit();
                }}
                disabled={!isStreaming && !hasInput}
                className={cn(
                  'inline-flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200 disabled:opacity-50 active:scale-95',
                  isStreaming || hasInput
                    ? 'bg-black text-white shadow-md hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200'
                    : 'bg-neutral-100 text-neutral-400 dark:bg-[#404040] dark:text-neutral-500'
                )}
              >
                {isStreaming ? <StopIcon /> : <SendIcon />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export const AgentChat = memo(function AgentChat({
  messages,
  onSend,
  onStop,
  status = 'ready',
  ragPhase,
  error,
  emptyStatePosition = 'default',
  attachments,
  className,
  disabled,
  placeholder,
}: AgentChatProps) {
  const [draft, setDraft] = useState('');

  const messagesWithError: AgentMessage[] = useMemo(() => {
    if (!error) return messages;
    return [
      ...messages,
      {
        id: 'agent-chat-error',
        stableId: 'agent-chat-error',
        role: 'assistant' as const,
        parts: [
          {
            type: 'error' as const,
            title: error.title ?? 'Request failed',
            message: error.message,
          },
        ],
      },
    ];
  }, [messages, error]);

  const isEmpty = !error && messages.length === 0;
  const isCenteredEmpty = isEmpty && emptyStatePosition === 'center';

  const inputBarNode: ReactNode = (
    <InputBar
      onSend={onSend}
      onStop={onStop}
      status={status}
      attachments={attachments}
      value={draft}
      onChange={setDraft}
      disabled={disabled}
      placeholder={placeholder}
      className={isCenteredEmpty ? 'px-0 pb-0' : undefined}
    />
  );

  return (
    <div className={cn('flex flex-col h-full min-h-0 bg-transparent', className)}>
      {isCenteredEmpty ? (
        <div className="flex-1 min-h-0 flex items-center justify-center px-4 py-4">
          <div className="w-full max-w-3xl flex flex-col gap-8">
            <h1 className="text-3xl font-semibold text-center text-foreground">
              How can I help you?
            </h1>
            {inputBarNode}
          </div>
        </div>
      ) : (
        <>
          <MessageList messages={messagesWithError} status={status} ragPhase={ragPhase} />
          {inputBarNode}
        </>
      )}
    </div>
  );
});

export default AgentChat;
