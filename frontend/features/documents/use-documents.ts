'use client';

import { deleteDocumentAction, getDocuments } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Document } from '@/lib/types';
import { useEffect, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { useDocumentStore } from './document-store';

const EMPTY_DOCUMENTS: Document[] = [];
const pollingRefs = new Map<string, number>();
const pollingIntervals = new Map<string, ReturnType<typeof setInterval>>();
const documentRequests = new Map<string, Promise<Document[] | null>>();

/** Shares one in-flight document request between the sidebar and document manager. */
function refreshDocuments(sessionId: string): Promise<Document[] | null> {
  const inFlight = documentRequests.get(sessionId);
  if (inFlight) return inFlight;

  const request = getDocuments(sessionId)
    .then((documents) => {
      if (documents) useDocumentStore.getState().setDocuments(sessionId, documents);
      return documents;
    })
    .finally(() => {
      documentRequests.delete(sessionId);
    });

  documentRequests.set(sessionId, request);
  return request;
}

export function useDocuments(sessionId: string | null, initialDocuments?: Document[]) {
  const config = useConfig();
  const documents = useDocumentStore((state) =>
    sessionId ? (state.documentsBySession[sessionId] ?? EMPTY_DOCUMENTS) : EMPTY_DOCUMENTS
  );
  const setDocuments = useDocumentStore((state) => state.setDocuments);
  const applyUploadOptimistic = useDocumentStore((state) => state.applyUploadOptimistic);
  const confirmUpload = useDocumentStore((state) => state.confirmUpload);
  const revertUpload = useDocumentStore((state) => state.revertUpload);
  const removeOptimistic = useDocumentStore((state) => state.removeOptimistic);
  const markDeleting = useDocumentStore((state) => state.markDeleting);
  const [isUploading, setIsUploading] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!sessionId) return;

    if (initialDocuments) {
      setDocuments(sessionId, initialDocuments);
      return;
    }

    void refreshDocuments(sessionId).catch(() => {
      // Preserve the last known store value. Route boundaries handle navigation failures.
    });
  }, [initialDocuments, sessionId, setDocuments]);

  useEffect(() => {
    if (!sessionId) return;

    const hasProcessing = documents.some(
      (document) => document.status === 'processing' || document.status === 'uploaded'
    );
    if (!hasProcessing) return;

    const refCount = (pollingRefs.get(sessionId) ?? 0) + 1;
    pollingRefs.set(sessionId, refCount);

    if (refCount === 1) {
      pollingIntervals.set(
        sessionId,
        setInterval(() => {
          void refreshDocuments(sessionId).catch(() => {
            // The next interval retries; stale document state remains visible meanwhile.
          });
        }, 3000)
      );
    }

    return () => {
      const nextRefCount = (pollingRefs.get(sessionId) ?? 1) - 1;
      if (nextRefCount > 0) {
        pollingRefs.set(sessionId, nextRefCount);
        return;
      }

      const interval = pollingIntervals.get(sessionId);
      if (interval) clearInterval(interval);
      pollingIntervals.delete(sessionId);
      pollingRefs.delete(sessionId);
    };
  }, [documents, sessionId]);

  const uploadFiles = async (files: FileList | File[]) => {
    if (!sessionId || !files.length || !config) return;

    if (files.length > config.max_files_per_request) {
      toast.error(
        `You can only upload a maximum of ${config.max_files_per_request} files at once.`
      );
      return;
    }

    const formData = new FormData();
    formData.append('sessionId', sessionId);

    for (const file of Array.from(files)) {
      if (file.size > config.max_file_size_mb * 1024 * 1024) {
        toast.error(
          `One or more files exceed the maximum allowed file size (${config.max_file_size_mb}MB).`
        );
        return;
      }

      const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
      if (!config.accepted_extensions.includes(extension)) {
        toast.error(
          `Unsupported file type. Supported types: ${config.accepted_extensions.join(', ')}.`
        );
        return;
      }

      formData.append('files', file);
    }

    const timestamp = Date.now();
    const optimisticDocuments: Document[] = Array.from(files).map((file, index) => ({
      id: `temp-${timestamp}-${index}`,
      original_file_name: file.name,
      status: 'processing',
      created_at: new Date().toISOString(),
    }));
    const temporaryIds = optimisticDocuments.map((document) => document.id);

    setIsUploading(true);
    applyUploadOptimistic(sessionId, optimisticDocuments);

    try {
      const response = await fetch('/api/upload', { method: 'POST', body: formData });
      const result: { results?: Document[]; error?: { code?: string; message?: string } } =
        await response.json().catch(() => ({}));

      if (!response.ok) {
        revertUpload(sessionId, temporaryIds);
        const code = result.error?.code;
        if (code === 'too_many_files') {
          toast.error(
            `You can only upload a maximum of ${config.max_files_per_request} files at once.`
          );
        } else if (code === 'file_too_large') {
          toast.error(
            `One or more files exceed the maximum allowed file size (${config.max_file_size_mb}MB).`
          );
        } else if (code === 'unsupported_document_type') {
          toast.error(
            `Unsupported file type. Supported types: ${config.accepted_extensions.join(', ')}.`
          );
        } else if (code === 'duplicate_document') {
          toast.error('This document already exists in the current session.');
        } else if (code === 'rate_limit_exceeded') {
          toast.error("You're uploading too fast. Please wait a moment.");
        } else {
          toast.error(result.error?.message || 'Upload failed.');
        }
        return;
      }

      confirmUpload(sessionId, result.results ?? []);
      toast.success('Documents uploaded successfully.');
    } catch {
      revertUpload(sessionId, temporaryIds);
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (documentId: string): Promise<boolean> => {
    if (!sessionId) return false;

    markDeleting(sessionId, documentId);
    const result = await deleteDocumentAction(documentId, sessionId);
    if (result.success) {
      removeOptimistic(sessionId, documentId);
      return true;
    }

    void refreshDocuments(sessionId).catch(() => {
      toast.error('Unable to refresh documents after the failed deletion.');
    });
    return false;
  };

  const handleDelete = (documentId: string) => {
    startTransition(async () => {
      if (!(await deleteDocument(documentId))) toast.error('Failed to delete document.');
    });
  };

  return { documents, isUploading, isPending, uploadFiles, handleDelete, deleteDocument };
}
