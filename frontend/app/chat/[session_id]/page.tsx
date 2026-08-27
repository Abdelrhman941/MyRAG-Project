import { MessageFeed } from '@/components/message-feed';
import { getMessages } from '@/lib/api';

export default async function ChatSessionPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const resolvedParams = await params;
  const sessionId = resolvedParams.session_id;
  const initialMessages = await getMessages(sessionId);

  return (
    <div className="flex flex-col h-full bg-muted/20">
      <MessageFeed initialMessages={initialMessages || []} sessionId={sessionId} />
    </div>
  );
}
