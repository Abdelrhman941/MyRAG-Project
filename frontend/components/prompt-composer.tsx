'use client';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { SendHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface PromptComposerProps {
  onSend: (text: string) => void;
  isPending: boolean;
}

export function PromptComposer({ onSend, isPending }: PromptComposerProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isPending && text.trim()) {
        onSend(text);
        setText('');
      }
    }
  };

  return (
    <div className="relative flex items-end w-full rounded-2xl bg-background border shadow-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 p-1">
      <Textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything about your documents..."
        className="min-h-[44px] max-h-[200px] w-full resize-none border-0 bg-transparent py-3 pl-4 pr-12 focus-visible:ring-0 shadow-none text-base sm:text-sm"
        disabled={isPending}
        rows={1}
      />
      <div className="absolute right-2 bottom-2">
        <Button
          size="icon"
          className="h-8 w-8 rounded-xl shrink-0"
          onClick={() => {
            if (!isPending && text.trim()) {
              onSend(text);
              setText('');
            }
          }}
          disabled={isPending || !text.trim()}
          aria-label="Send message"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
