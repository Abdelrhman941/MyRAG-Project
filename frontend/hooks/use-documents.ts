import { deleteDocumentAction, getDocuments, uploadBatchAction } from '@/lib/api';
import { Document } from '@/lib/types';
import { useEffect, useRef, useState, useTransition } from 'react';
import { toast } from 'sonner';

export function useDocuments(sessionId: string | null, initialDocuments: Document[] = []) {
  const [documents, setDocuments] = useState<Document[]>(initialDocuments);
  const [isUploading, setIsUploading] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Track previous sessionId for render-phase reset (avoids setState-in-effect lint error)
  const [prevSessionId, setPrevSessionId] = useState(sessionId);
  if (sessionId !== prevSessionId) {
    setPrevSessionId(sessionId);
    setDocuments(initialDocuments);
  }

  // Always fetch from backend on mount / sessionId change to populate fresh state.
  // This fixes the sidebar "documents disappear after refresh" bug because
  // initialDocuments passed to the sidebar is always [] (sidebar has no server props).
  useEffect(() => {
    if (!sessionId) return;
    getDocuments(sessionId).then((data) => {
      if (data) {
        console.log('FETCHED DOCS FOR', sessionId, data.length);
        setDocuments(data);
      }
    });
  }, [sessionId]);

  // Cross-component sync via CustomEvent (optimistic updates from any uploader)
  useEffect(() => {
    if (!sessionId) return;
    const handleSync = (e: Event) => {
      const ev = e as CustomEvent<{ sessionId: string; documents?: Document[] }>;
      if (ev.detail.sessionId !== sessionId) return;
      if (ev.detail.documents) {
        setDocuments(ev.detail.documents);
      } else {
        getDocuments(sessionId).then((data) => {
          if (data) {
            console.log('FETCHED DOCS FOR', sessionId, data.length);
            setDocuments(data);
          }
        });
      }
    };
    window.addEventListener('documents-sync', handleSync);
    return () => window.removeEventListener('documents-sync', handleSync);
  }, [sessionId]);

  // Keep a ref in sync so upload callbacks always close over the latest documents list
  // without needing documents as a dependency (which would restart polling unnecessarily).
  const documentsRef = useRef(documents);
  useEffect(() => {
    documentsRef.current = documents;
  });

  useEffect(() => {
    if (!sessionId) return;
    const hasProcessing = documents.some(
      (d) => d.status === 'processing' || d.status === 'uploaded'
    );
    if (!hasProcessing) return;

    const interval = setInterval(async () => {
      const fresh = await getDocuments(sessionId);
      if (!fresh) return;
      setDocuments(fresh);
      // Broadcast so sidebar / document-manager stay in sync
      window.dispatchEvent(
        new CustomEvent('documents-sync', { detail: { sessionId, documents: fresh } })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, [documents, sessionId]);

  // ──────────────────────────────────────────────────────────────────────────
  // Upload
  // ──────────────────────────────────────────────────────────────────────────
  const uploadFiles = async (files: FileList | File[]) => {
    if (!sessionId || !files || files.length === 0) return;

    if (files.length > 10) {
      toast.error('You can only upload a maximum of 10 files at once.');
      return;
    }

    const maxFileSizeMB = parseInt(process.env.NEXT_PUBLIC_MAX_FILE_SIZE_MB || '50', 10);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      if (files[i].size > maxFileSizeMB * 1024 * 1024) {
        toast.error(`One or more files exceed the maximum allowed file size (${maxFileSizeMB}MB).`);
        return;
      }
      formData.append('files', files[i]);
    }

    setIsUploading(true);

    // Optimistic placeholders so the UI shows immediately
    const optimisticDocs: Document[] = Array.from(files).map((f, i) => ({
      id: `temp-${Date.now()}-${i}`,
      original_file_name: f.name,
      status: 'processing' as const,
      created_at: new Date().toISOString(),
    }));

    const withOptimistic = [...optimisticDocs, ...documentsRef.current];
    setDocuments(withOptimistic);
    window.dispatchEvent(
      new CustomEvent('documents-sync', { detail: { sessionId, documents: withOptimistic } })
    );

    const result = await uploadBatchAction(sessionId, formData);
    setIsUploading(false);

    if (!result.success) {
      // Revert optimistic placeholders
      const reverted = documentsRef.current.filter((d) => !d.id.startsWith('temp-'));
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
        toast.error('Unsupported file type. Supported types: PDF, TXT, MD, DOCX.');
      else if (code === 'duplicate_document')
        toast.error('This document already exists in the current session.');
      else if (code === 'rate_limit_exceeded')
        toast.error("You're uploading too fast. Please wait a moment.");
      else toast.error(result.error?.message || 'Upload failed');
    } else {
      const confirmed = (result.results as Document[] | undefined) ?? [];
      const existing = documentsRef.current.filter((d) => !d.id.startsWith('temp-'));
      const finalDocs = [...confirmed, ...existing];
      setDocuments(finalDocs);
      window.dispatchEvent(
        new CustomEvent('documents-sync', { detail: { sessionId, documents: finalDocs } })
      );
      toast.success('Documents uploaded successfully.');
    }
  };

  // ──────────────────────────────────────────────────────────────────────────
  // Delete
  // ──────────────────────────────────────────────────────────────────────────
  const handleDelete = (docId: string) => {
    if (!sessionId) return;
    const optimistic = documentsRef.current.filter((d) => d.id !== docId);
    setDocuments(optimistic);
    window.dispatchEvent(
      new CustomEvent('documents-sync', { detail: { sessionId, documents: optimistic } })
    );

    startTransition(() => {
      deleteDocumentAction(docId, sessionId).then((res) => {
        if (!res.success) {
          toast.error('Failed to delete document.');
          // Refetch to restore accurate state
          getDocuments(sessionId).then((data) => {
            if (data) {
              setDocuments(data);
              window.dispatchEvent(
                new CustomEvent('documents-sync', { detail: { sessionId, documents: data } })
              );
            }
          });
        }
      });
    });
  };

  return { documents, setDocuments, isUploading, isPending, uploadFiles, handleDelete };
}
