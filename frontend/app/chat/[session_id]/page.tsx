import { MessageFeed } from '@/features/chat/message-feed';
import { getMessages, getSession } from '@/lib/api';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

type ChatSessionPageProps = {
  params: Promise<{ session_id: string }>;
};

export async function generateMetadata({ params }: ChatSessionPageProps): Promise<Metadata> {
  const { session_id } = await params;
  const session = await getSession(session_id);

  return { title: session?.title || 'Chat' };
}

export const dynamic = 'force-dynamic';

export default async function ChatSessionPage({ params }: ChatSessionPageProps) {
  const resolvedParams = await params;
  const sessionId = resolvedParams.session_id;
  const initialMessages = await getMessages(sessionId);

  if (!initialMessages) notFound();

  return (
    <div className="flex flex-col h-full bg-muted/20">
      <MessageFeed key={sessionId} initialMessages={initialMessages} sessionId={sessionId} />
    </div>
  );
}
