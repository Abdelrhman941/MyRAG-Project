import type { Document } from '@/lib/types';
import { create } from 'zustand';

// Stable reference to prevent unnecessary re-renders in selectors
export const EMPTY_DOCUMENTS: Document[] = [];

interface DocumentStore {
  documentsBySession: Record<string, Document[]>;
  setDocuments: (sessionId: string, docs: Document[]) => void;
  applyUploadOptimistic: (sessionId: string, newDocs: Document[]) => void;
  confirmUpload: (sessionId: string, confirmedDocs: Document[], tempIds: string[]) => void;
  revertUpload: (sessionId: string, tempIds: string[]) => void;
  removeOptimistic: (sessionId: string, documentId: string) => void;
  markDeleting: (sessionId: string, documentId: string) => void;
}

export const useDocumentStore = create<DocumentStore>()((set) => ({
  documentsBySession: {},

  setDocuments: (sessionId, docs) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      const tempDocs = existing.filter((d) => d.id.startsWith('temp-'));

      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: [...tempDocs, ...docs],
        },
      };
    }),

  applyUploadOptimistic: (sessionId, newDocs) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: [...newDocs, ...existing],
        },
      };
    }),

  confirmUpload: (sessionId, confirmedDocs, tempIds) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      const filtered = existing.filter(
        (d) => !(d.id.startsWith('temp-') && tempIds.includes(d.id))
      );
      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: [...confirmedDocs, ...filtered],
        },
      };
    }),

  revertUpload: (sessionId, tempIds) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: existing.filter((d) => !tempIds.includes(d.id)),
        },
      };
    }),

  removeOptimistic: (sessionId, documentId) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: existing.filter((d) => d.id !== documentId),
        },
      };
    }),

  markDeleting: (sessionId, documentId) =>
    set((state) => {
      const existing = state.documentsBySession[sessionId] || [];
      return {
        documentsBySession: {
          ...state.documentsBySession,
          [sessionId]: existing.map((d) =>
            d.id === documentId ? { ...d, status: 'deleting' } : d
          ),
        },
      };
    }),
}));
