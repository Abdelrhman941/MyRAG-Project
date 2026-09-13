'use client';

import { deleteDocumentAction, getDocuments, retryDocumentAction } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Document } from '@/lib/types';
import { useEffect, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { EMPTY_DOCUMENTS, useDocumentStore } from './document-store';

const pollingIntervals = new Map<string, ReturnType<typeof setTimeout>>();
const pollingStartTimes = new Map<string, number>();
const documentRequests = new Map<string, Promise<Document[] | null>>();

const POLLING_FAST_INTERVAL_MS = 1000;
const POLLING_SLOW_INTERVAL_MS = 3000;
const POLLING_FAST_WINDOW_MS = 15000;

function hasPendingProcessing(documents: Document[]): boolean {
  return documents.some(
    (document) => document.status === 'processing' || document.status === 'uploaded'
  );
}

/** Shares one in-flight document request between multiple consumers. */
function refreshDocuments(sessionId: string): Promise<Document[] | null> {
  const inFlight = documentRequests.get(sessionId);
  if (inFlight) return inFlight;

  const request = getDocuments(sessionId)
    .then((documents) => {
      if (documents) {
        useDocumentStore.getState().setDocuments(sessionId, documents);
      }

      return documents;
    })
    .finally(() => {
      documentRequests.delete(sessionId);
    });

  documentRequests.set(sessionId, request);
  return request;
}

/**
 * Starts one polling loop per session while documents are being processed.
 *
 * Polling is intentionally session-scoped and independent from component
 * lifetime so uploads/retries can start it directly without maintaining
 * artificial consumer reference counts.
 */
function ensurePolling(sessionId: string): void {
  if (pollingIntervals.has(sessionId)) return;

  pollingStartTimes.set(sessionId, Date.now());

  const poll = () => {
    const documents = useDocumentStore.getState().documentsBySession[sessionId] ?? EMPTY_DOCUMENTS;

    if (!hasPendingProcessing(documents)) {
      pollingIntervals.delete(sessionId);
      pollingStartTimes.delete(sessionId);
      return;
    }

    void refreshDocuments(sessionId).catch(() => {
      // Keep polling; a transient refresh failure should not stop processing tracking.
    });

    const startTime = pollingStartTimes.get(sessionId) ?? Date.now();
    const elapsed = Date.now() - startTime;
    const delay =
      elapsed < POLLING_FAST_WINDOW_MS ? POLLING_FAST_INTERVAL_MS : POLLING_SLOW_INTERVAL_MS;

    pollingIntervals.set(sessionId, setTimeout(poll, delay));
  };

  pollingIntervals.set(sessionId, setTimeout(poll, POLLING_FAST_INTERVAL_MS));
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
  const [uploadingCount, setUploadingCount] = useState(0);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!sessionId) return;

    if (initialDocuments) {
      setDocuments(sessionId, initialDocuments);
      return;
    }

    void refreshDocuments(sessionId).catch(() => {
      // Preserve the last known store value.
    });
  }, [initialDocuments, sessionId, setDocuments]);

  useEffect(() => {
    if (!sessionId || !hasPendingProcessing(documents)) return;

    ensurePolling(sessionId);
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
    const selectedFiles = Array.from(files);

    for (const file of selectedFiles) {
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

    const optimisticDocuments: Document[] = selectedFiles.map((file, index) => ({
      id: `temp-${timestamp}-${index}`,
      original_file_name: file.name,
      status: 'processing',
      created_at: new Date().toISOString(),
    }));

    const temporaryIds = optimisticDocuments.map((document) => document.id);

    setIsUploading(true);
    setUploadingCount(selectedFiles.length);
    applyUploadOptimistic(sessionId, optimisticDocuments);
    ensurePolling(sessionId);

    try {
      const response = await fetch(`/api/upload?session=${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        body: formData,
      });

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

      const confirmedTempIds = temporaryIds.filter(
        (_, index) => results[index]?.ok && results[index]?.document
      );

      const failedTemporaryIds = temporaryIds.filter(
        (_, index) => !results[index]?.ok || !results[index]?.document
      );

      if (confirmedDocuments.length > 0) {
        confirmUpload(sessionId, confirmedDocuments, confirmedTempIds);

        toast.success(
          confirmedDocuments.length === 1
            ? 'Document uploaded successfully.'
            : 'Documents uploaded successfully.'
        );
      }

      if (failedTemporaryIds.length > 0) {
        revertUpload(sessionId, failedTemporaryIds);

        const failedResults = results.filter((result) => !result.ok || !result.document);

        const count = failedResults.length;
        const messages = failedResults.map(
          (result) => `${result.filename} (${result.error?.message || 'unknown error'})`
        );

        toast.error(`${count} file${count === 1 ? '' : 's'} failed: ${messages.join(', ')}`);
      }

      if (hasPendingProcessing(confirmedDocuments)) {
        ensurePolling(sessionId);
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
      return true;
    }

    void refreshDocuments(sessionId).catch(() => {
      toast.error('Unable to refresh documents after the failed deletion.');
    });

    return false;
  };

  const handleDelete = (documentId: string) => {
    startTransition(async () => {
      if (!(await deleteDocument(documentId))) {
        toast.error('Failed to delete document.');
      }
    });
  };

  const handleRetry = (documentId: string) => {
    if (!sessionId) return;

    startTransition(async () => {
      const result = await retryDocumentAction(documentId, sessionId);

      if (!result.success) {
        toast.error(result.error?.message || 'Failed to retry document.');
        return;
      }

      toast.success('Document re-queued for processing.');

      ensurePolling(sessionId);

      void refreshDocuments(sessionId).catch(() => {
        // Polling will retry the refresh automatically.
      });
    });
  };

  return {
    documents,
    isUploading,
    uploadingCount,
    isPending,
    uploadFiles,
    handleDelete,
    handleRetry,
    deleteDocument,
  };
}

type BatchUploadResult = {
  filename: string;
  ok: boolean;
  document?: Document;
  error?: {
    code?: string;
    message?: string;
  };
};

type BatchUploadResponse = {
  results?: BatchUploadResult[];
  error?: {
    code?: string;
    message?: string;
  };
};
