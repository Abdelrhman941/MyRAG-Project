import { deleteDocumentAction, uploadBatchAction } from '@/lib/api';
import { Document } from '@/lib/types';
import { useEffect, useState, useTransition } from 'react';
import { toast } from 'sonner';

export function useDocuments(sessionId: string | null, initialDocuments: Document[] = []) {
  const [documents, setDocuments] = useState<Document[]>(initialDocuments);
  const [isUploading, setIsUploading] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Listen for cross-component sync events
  useEffect(() => {
    if (!sessionId) return;
    const handleSync = (e: Event) => {
      const customEvent = e as CustomEvent<{ sessionId: string; documents?: Document[] }>;
      if (customEvent.detail.sessionId === sessionId) {
        if (customEvent.detail.documents) {
          setDocuments(customEvent.detail.documents);
        } else {
          // Just refetch
          fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/chat/sessions/${sessionId}/documents`
          )
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
              if (data) setDocuments(data);
            })
            .catch(console.error);
        }
      }
    };
    window.addEventListener('documents-sync', handleSync);
    return () => window.removeEventListener('documents-sync', handleSync);
  }, [sessionId]);

  // Reset state when session changes
  const [prevSessionId, setPrevSessionId] = useState(sessionId);
  if (sessionId !== prevSessionId) {
    setPrevSessionId(sessionId);
    setDocuments(initialDocuments);
  }

  // Initial fetch if we didn't get initialDocuments and have a sessionId
  useEffect(() => {
    if (sessionId && initialDocuments.length === 0) {
      fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/chat/sessions/${sessionId}/documents`
      )
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) setDocuments(data);
        })
        .catch(console.error);
    }
  }, [sessionId, initialDocuments.length]);

  // Polling logic
  useEffect(() => {
    if (!sessionId) return;
    const hasProcessing = documents.some(
      (doc) => doc.status === 'processing' || doc.status === 'uploaded'
    );
    if (!hasProcessing) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/chat/sessions/${sessionId}/documents`
        );
        if (res.ok) {
          const freshDocs: Document[] = await res.json();
          setDocuments(freshDocs);
          // Broadcast so other components stay in sync during polling
          window.dispatchEvent(
            new CustomEvent('documents-sync', { detail: { sessionId, documents: freshDocs } })
          );
        }
      } catch (e: unknown) {
        console.error('Polling error', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents, sessionId]);

  const uploadFiles = async (files: FileList | File[]) => {
    if (!sessionId || !files || files.length === 0) return;

    if (files.length > 10) {
      toast.error('You can only upload a maximum of 10 files at once.');
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      if (files[i].size > 10 * 1024 * 1024) {
        toast.error('One or more files exceed the maximum allowed file size.');
        return;
      }
      formData.append('files', files[i]);
    }

    setIsUploading(true);

    const optimisticDocs: Document[] = Array.from(files).map((f, i) => ({
      id: `temp-${Date.now()}-${i}`,
      original_file_name: f.name,
      status: 'processing',
      created_at: new Date().toISOString(),
    }));

    const newDocs = [...optimisticDocs, ...documents];
    setDocuments(newDocs);
    window.dispatchEvent(
      new CustomEvent('documents-sync', { detail: { sessionId, documents: newDocs } })
    );

    const result = await uploadBatchAction(sessionId, formData);
    setIsUploading(false);

    if (!result.success) {
      const reverted = documents.filter((d) => !d.id.startsWith('temp-'));
      setDocuments(reverted);
      window.dispatchEvent(
        new CustomEvent('documents-sync', { detail: { sessionId, documents: reverted } })
      );

      const code = result.error?.code;
      if (code === 'too_many_files')
        toast.error('You can only upload a maximum of 10 files at once.');
      else if (code === 'file_too_large')
        toast.error('One or more files exceed the maximum allowed file size.');
      else if (code === 'unsupported_document_type')
        toast.error('Unsupported file type. Supported types are PDF, TXT, MD, and DOCX.');
      else if (code === 'duplicate_document')
        toast.error('This document already exists in the current session.');
      else if (code === 'rate_limit_exceeded')
        toast.error("You're moving too fast. Please try again in a moment.");
      else toast.error(result.error?.message || 'Upload failed');
    } else {
      if (result.results) {
        const finalDocs = [
          ...(result.results as Document[]),
          ...documents.filter((d) => !d.id.startsWith('temp-')),
        ];
        setDocuments(finalDocs);
        window.dispatchEvent(
          new CustomEvent('documents-sync', { detail: { sessionId, documents: finalDocs } })
        );
      }
      toast.success('Documents uploaded successfully.');
    }
  };

  const handleDelete = (docId: string) => {
    if (!sessionId) return;
    const newDocs = documents.filter((d) => d.id !== docId);
    setDocuments(newDocs);
    window.dispatchEvent(
      new CustomEvent('documents-sync', { detail: { sessionId, documents: newDocs } })
    );

    startTransition(() => {
      deleteDocumentAction(docId, sessionId).then((res) => {
        if (!res.success) {
          toast.error('Failed to delete document.');
          window.dispatchEvent(new CustomEvent('documents-sync', { detail: { sessionId } })); // Refetch to undo
        }
      });
    });
  };

  return { documents, setDocuments, isUploading, isPending, uploadFiles, handleDelete };
}
