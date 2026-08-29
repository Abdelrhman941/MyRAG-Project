import { deleteDocumentAction, getDocuments } from '@/lib/api';
import { useConfig } from '@/lib/config';
import { Document } from '@/lib/types';
import { useEffect, useState, useTransition, useMemo } from 'react';
import { toast } from 'sonner';
import { useDocumentStore } from './store';

const pollingRefs: Record<string, number> = {};
const pollingIntervals: Record<string, NodeJS.Timeout> = {};

export function useDocuments(sessionId: string | null, initialDocuments: Document[] = []) {
  const store = useDocumentStore();
  const config = useConfig();

  const documents = useMemo(() => {
    return sessionId ? (store.documentsBySession[sessionId] || []) : [];
  }, [sessionId, store.documentsBySession]);

  const [isUploading, setIsUploading] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Handle mount and refetch
  useEffect(() => {
    if (!sessionId) return;

    // Merge initial if not populated
    if (!store.documentsBySession[sessionId] && initialDocuments.length > 0) {
      store.setDocuments(sessionId, initialDocuments);
    }

    // Fetch fresh
    getDocuments(sessionId).then((data) => {
      if (data) {
        store.setDocuments(sessionId, data);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]); // Do NOT add store.setDocuments/initialDocuments or it loops

  // Polling logic with ref-counting
  useEffect(() => {
    if (!sessionId) return;
    const hasProcessing = documents.some(
      (d) => d.status === 'processing' || d.status === 'uploaded'
    );

    if (hasProcessing) {
      if (!pollingRefs[sessionId]) {
        pollingRefs[sessionId] = 0;
      }
      pollingRefs[sessionId]++;

      if (pollingRefs[sessionId] === 1) {
        pollingIntervals[sessionId] = setInterval(async () => {
          const fresh = await getDocuments(sessionId);
          if (fresh) {
            store.setDocuments(sessionId, fresh);
          }
        }, 3000);
      }

      return () => {
        pollingRefs[sessionId]--;
        if (pollingRefs[sessionId] === 0) {
          clearInterval(pollingIntervals[sessionId]);
          delete pollingIntervals[sessionId];
        }
      };
    }
  }, [documents, sessionId, store]);

  // ──────────────────────────────────────────────────────────────────────────
  // Upload
  // ──────────────────────────────────────────────────────────────────────────
  const uploadFiles = async (files: FileList | File[]) => {
    if (!sessionId || !files || files.length === 0 || !config) return;

    if (files.length > config.max_files_per_request) {
      toast.error(
        `You can only upload a maximum of ${config.max_files_per_request} files at once.`
      );
      return;
    }

    const formData = new FormData();
    formData.append('sessionId', sessionId);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.size > config.max_file_size_mb * 1024 * 1024) {
        toast.error(
          `One or more files exceed the maximum allowed file size (${config.max_file_size_mb}MB).`
        );
        return;
      }
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!config.accepted_extensions.includes(ext)) {
        toast.error(
          `Unsupported file type. Supported types: ${config.accepted_extensions.join(', ')}.`
        );
        return;
      }
      formData.append('files', file);
    }

    setIsUploading(true);

    const tempIds: string[] = [];
    const optimisticDocs: Document[] = Array.from(files).map((f, i) => {
      const id = `temp-${Date.now()}-${i}`;
      tempIds.push(id);
      return {
        id,
        original_file_name: f.name,
        status: 'processing' as const,
        created_at: new Date().toISOString(),
      };
    });

    store.applyUploadOptimistic(sessionId, optimisticDocs);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      setIsUploading(false);

      const result = await response.json();

      if (!response.ok) {
        store.revertUpload(sessionId, tempIds);
        const code = result.error?.code;
        if (code === 'too_many_files')
          toast.error(
            `You can only upload a maximum of ${config.max_files_per_request} files at once.`
          );
        else if (code === 'file_too_large')
          toast.error(
            `One or more files exceed the maximum allowed file size (${config.max_file_size_mb}MB).`
          );
        else if (code === 'unsupported_document_type')
          toast.error(
            `Unsupported file type. Supported types: ${config.accepted_extensions.join(', ')}.`
          );
        else if (code === 'duplicate_document')
          toast.error('This document already exists in the current session.');
        else if (code === 'rate_limit_exceeded')
          toast.error("You're uploading too fast. Please wait a moment.");
        else toast.error(result.error?.message || 'Upload failed');
      } else {
        const confirmed = (result.results as Document[] | undefined) ?? [];
        store.confirmUpload(sessionId, confirmed);
        toast.success('Documents uploaded successfully.');
      }
    } catch {
      setIsUploading(false);
      store.revertUpload(sessionId, tempIds);
      toast.error('Upload failed. Please try again.');
    }
  };

  // ──────────────────────────────────────────────────────────────────────────
  // Delete
  // ──────────────────────────────────────────────────────────────────────────
  const deleteDocument = async (docId: string): Promise<boolean> => {
    if (!sessionId) return false;

    // We can optimistically mark as deleting or remove. The spec says "removeOptimistic" or "markDeleting"
    store.markDeleting(sessionId, docId);

    const res = await deleteDocumentAction(docId, sessionId);
    if (!res.success) {
      getDocuments(sessionId).then((data) => {
        if (data) store.setDocuments(sessionId, data);
      });
      return false;
    }
    store.removeOptimistic(sessionId, docId);
    return true;
  };

  const handleDelete = (docId: string) => {
    startTransition(() => {
      void deleteDocument(docId).then((success) => {
        if (!success) toast.error('Failed to delete document.');
      });
    });
  };

  return { documents, isUploading, isPending, uploadFiles, handleDelete, deleteDocument };
}
