import { MessageFeed } from '@/features/chat/message-feed';
import { getDocuments, getMessages, getSession } from '@/lib/api';
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

  // ✅ Performance Win: Fetch messages and documents in parallel on the server
  const [initialMessages, initialDocuments] = await Promise.all([
    getMessages(sessionId),
    getDocuments(sessionId),
  ]);

  if (!initialMessages) notFound();

  return (
    <div className="flex flex-col h-full bg-muted/20">
      <MessageFeed
        key={sessionId} // ✅ Critical: Resets component state on session switch
        initialMessages={initialMessages}
        initialDocuments={initialDocuments ?? []} // ✅ Prevents client-side refetch
        sessionId={sessionId}
      />
    </div>
  );
}
