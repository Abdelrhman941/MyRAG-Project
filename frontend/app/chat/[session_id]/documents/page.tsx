import { DocumentManager } from '@/components/document-manager';
import { getDocuments } from '@/lib/api';

export default async function DocumentsPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const resolvedParams = await params;
  const sessionId = resolvedParams.session_id;
  const initialDocuments = await getDocuments(sessionId);

  return (
    <div className="flex flex-col h-full bg-background p-6 lg:p-10 max-w-5xl mx-auto overflow-y-auto">
      <div className="flex items-center gap-4 mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">Knowledge Base</h1>
      </div>
      <DocumentManager initialDocuments={initialDocuments || []} sessionId={sessionId} />
    </div>
  );
}
