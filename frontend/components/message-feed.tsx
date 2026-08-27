'use client';

import { ScrollArea } from '@/components/ui/scroll-area';
import { sendMessageAction } from '@/lib/api';
import { BotIcon, UserIcon } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PromptComposer } from './prompt-composer';

export function MessageFeed({
  initialMessages,
  sessionId,
}: {
  initialMessages: import('@/lib/types').Message[];
  sessionId: string;
}) {
  const [messages, setMessages] = useState(initialMessages);
  const [isPending, setIsPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isPending]);

  const handleSend = async (question: string) => {
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
        // Find if Next.js already injected the message via revalidatePath
        // Actually, since we don't clear state on revalidatePath directly, we manually append
        // the response so the UI updates instantly. The next hard reload will fetch from server.
        // It's safer to just append it.
        const exists = prev.find((m) => m.id === result.response?.id);
        if (exists) return prev;
        return result.response ? [...prev, result.response] : prev;
      });
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      <ScrollArea className="flex-1 px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-8 pb-24 pt-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[50vh] text-muted-foreground">
              <h2 className="text-xl font-medium mb-2 text-foreground">How can I help you?</h2>
              <p className="text-sm">Upload some documents in the Knowledge Base to get started.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={msg.id || idx}
                className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div className="flex-shrink-0 mt-1">
                  {msg.role === 'user' ? (
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
                      <UserIcon className="h-5 w-5" />
                    </div>
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-muted border flex items-center justify-center">
                      <BotIcon className="h-5 w-5 text-foreground" />
                    </div>
                  )}
                </div>

                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3 ${
                    msg.role === 'user'
                      ? 'bg-muted/50 text-foreground border shadow-sm'
                      : msg.error
                        ? 'bg-destructive/10 text-destructive border border-destructive/20'
                        : 'bg-background border shadow-sm prose prose-sm dark:prose-invert max-w-none'
                  }`}
                >
                  {msg.role === 'assistant' && !msg.error ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}

                  {msg.error && (
                    <div className="mt-2 text-xs font-mono opacity-80 border-t border-destructive/20 pt-2">
                      Error: {msg.error}
                    </div>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-border/50 flex flex-wrap gap-2">
                      {msg.sources.map((src: { document_name: string }, i: number) => (
                        <div
                          key={i}
                          className="text-xs bg-muted/80 border text-muted-foreground px-2 py-1 rounded-md flex items-center gap-1"
                        >
                          <span className="font-medium">{src.document_name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {isPending && (
            <div className="flex gap-4">
              <div className="flex-shrink-0 mt-1">
                <div className="h-8 w-8 rounded-full bg-muted border flex items-center justify-center">
                  <BotIcon className="h-5 w-5 text-foreground" />
                </div>
              </div>
              <div className="max-w-[85%] rounded-2xl px-5 py-4 bg-background border shadow-sm flex gap-1 items-center h-[52px]">
                <span className="h-2 w-2 rounded-full bg-primary/40 animate-pulse"></span>
                <span className="h-2 w-2 rounded-full bg-primary/40 animate-pulse delay-75"></span>
                <span className="h-2 w-2 rounded-full bg-primary/40 animate-pulse delay-150"></span>
              </div>
            </div>
          )}
          <div ref={scrollRef} className="h-1" />
        </div>
      </ScrollArea>

      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-background via-background/90 to-transparent pt-10 pb-6 px-4">
        <div className="max-w-3xl mx-auto">
          <PromptComposer onSend={handleSend} isPending={isPending} />
        </div>
      </div>
    </div>
  );
}
