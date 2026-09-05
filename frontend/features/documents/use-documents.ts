'use client';

import { deleteDocumentAction, getDocuments, retryDocumentAction } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Document } from '@/lib/types';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { useDocumentStore } from './document-store';

const EMPTY_DOCUMENTS: Document[] = [];
const pollingRefs = new Map<string, number>();
const pollingIntervals = new Map<string, ReturnType<typeof setTimeout>>();
const pollingStartTimes = new Map<string, number>();
const documentRequests = new Map<string, Promise<Document[] | null>>();

type BatchUploadResult = {
  filename: string;
  ok: boolean;
  document?: Document;
  error?: { code?: string; message?: string };
};

type BatchUploadResponse = {
  results?: BatchUploadResult[];
  error?: { code?: string; message?: string };
};

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

function ensurePolling(sessionId: string) {
  pollingStartTimes.set(sessionId, Date.now());

  if (pollingIntervals.has(sessionId)) return;

  const refCount = (pollingRefs.get(sessionId) ?? 0) + 1;
  pollingRefs.set(sessionId, refCount);

  if (refCount === 1) {
    const poll = () => {
      const docs = useDocumentStore.getState().documentsBySession[sessionId] ?? [];
      const stillProcessing = docs.some(
        (d) => d.status === 'processing' || d.status === 'uploaded'
      );
      if (!stillProcessing) {
        pollingIntervals.delete(sessionId);
        pollingRefs.delete(sessionId);
        pollingStartTimes.delete(sessionId);
        return;
      }
      void refreshDocuments(sessionId).catch(() => {});

      const startTime = pollingStartTimes.get(sessionId) ?? Date.now();
      const elapsed = Date.now() - startTime;
      const delay = elapsed < 15000 ? 1000 : 3000;
      pollingIntervals.set(sessionId, setTimeout(poll, delay));
    };

    pollingIntervals.set(sessionId, setTimeout(poll, 1000));
  }
}

export function useDocuments(sessionId: string | null, initialDocuments?: Document[]) {
  const router = useRouter();
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
  const [uploadingCount, setUploadingCount] = useState(0);
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

    const currentDocs = useDocumentStore.getState().documentsBySession[sessionId] ?? [];
    const hasProcessing = currentDocs.some(
      (document) => document.status === 'processing' || document.status === 'uploaded'
    );
    if (!hasProcessing) return;

    ensurePolling(sessionId);

    return () => {
      const nextRefCount = (pollingRefs.get(sessionId) ?? 1) - 1;
      if (nextRefCount > 0) {
        pollingRefs.set(sessionId, nextRefCount);
        return;
      }

      const interval = pollingIntervals.get(sessionId);
      if (interval) clearTimeout(interval);
      pollingIntervals.delete(sessionId);
      pollingRefs.delete(sessionId);
      pollingStartTimes.delete(sessionId);
    };
  }, [sessionId]);

  const uploadFiles = async (files: FileList | File[]) => {
    if (!sessionId || !files.length || !config) return;

    if (files.length > config.max_files_per_request) {
      toast.error(
        `You can only upload a maximum of ${config.max_files_per_request} files at once.`
      );
      return;
    }

    const formData = new FormData();

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
    setUploadingCount(files.length);
    applyUploadOptimistic(sessionId, optimisticDocuments);
    ensurePolling(sessionId);

    try {
      const response = await fetch(`/api/upload?session=${sessionId}`, { method: 'POST', body: formData });
      const result: BatchUploadResponse = await response.json().catch(() => ({}));

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

      const results = result.results ?? [];
      const confirmedDocuments = results.flatMap((result) =>
        result.ok && result.document ? [result.document] : []
      );
      const failedTemporaryIds = temporaryIds.filter(
        (_, index) => !results[index]?.ok || !results[index]?.document
      );

      if (confirmedDocuments.length) {
        const confirmedTempIds = temporaryIds.filter(
          (_, index) => results[index]?.ok && results[index]?.document
        );
        confirmUpload(sessionId, confirmedDocuments, confirmedTempIds);
        toast.success(
          confirmedDocuments.length === 1 ? 'Document uploaded successfully.' : 'Documents uploaded successfully.'
        );
        router.refresh();
      }

      if (failedTemporaryIds.length) {
        revertUpload(sessionId, failedTemporaryIds);
        const failedResults = results.filter((result) => !result.ok || !result.document);
        const count = failedResults.length;
        const messages = failedResults.map(r => `${r.filename} (${r.error?.message || 'unknown error'})`);
        toast.error(`${count} file${count === 1 ? '' : 's'} failed: ${messages.join(', ')}`);
      }
    } catch {
      revertUpload(sessionId, temporaryIds);
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadingCount(0);
    }
  };

  const deleteDocument = async (documentId: string): Promise<boolean> => {
    if (!sessionId) return false;

    markDeleting(sessionId, documentId);
    const result = await deleteDocumentAction(documentId, sessionId);
    if (result.success) {
      removeOptimistic(sessionId, documentId);
      router.refresh();
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

  const handleRetry = (documentId: string) => {
    startTransition(async () => {
      const result = await retryDocumentAction(documentId, sessionId!);
      if (!result.success) {
        toast.error(result.error?.message || 'Failed to retry document.');
      } else {
        toast.success('Document re-queued for processing.');
        void refreshDocuments(sessionId!).catch(() => {});
        router.refresh();
      }
    });
  };

  return { documents, isUploading, uploadingCount, isPending, uploadFiles, handleDelete, handleRetry, deleteDocument };
}
