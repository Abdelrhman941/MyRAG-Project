'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { deleteDocumentAction, uploadBatchAction } from '@/lib/api';
import { Document } from '@/lib/types';
import { File, Loader2, Trash2, UploadCloud } from 'lucide-react';
import { useEffect, useRef, useState, useTransition } from 'react';
import { toast } from 'sonner';

export function DocumentManager({
  initialDocuments,
  sessionId,
}: {
  initialDocuments: Document[];
  sessionId: string;
}) {
  const [documents, setDocuments] = useState<Document[]>(initialDocuments);
  const [prevInitial, setPrevInitial] = useState<Document[]>(initialDocuments);
  const [isUploading, setIsUploading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Derived state to sync with server updates without useEffect cascading
  if (initialDocuments !== prevInitial) {
    setPrevInitial(initialDocuments);
    setDocuments(initialDocuments);
  }

  // Polling logic
  useEffect(() => {
    const hasProcessing = documents.some(
      (doc) => doc.status === 'processing' || doc.status === 'uploaded'
    );
    if (!hasProcessing) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/chat/sessions/${sessionId}/documents`);
        if (res.ok) {
          const freshDocs: Document[] = await res.json();
          setDocuments(freshDocs);
        }
      } catch (e: unknown) {
        console.error('Polling error', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents, sessionId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

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
    setDocuments((prev) => [...optimisticDocs, ...prev]);

    const result = await uploadBatchAction(sessionId, formData);
    setIsUploading(false);

    if (!result.success) {
      setDocuments((prev) => prev.filter((d) => !d.id.startsWith('temp-')));

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
        setDocuments((prev) => {
          const clean = prev.filter((d) => !d.id.startsWith('temp-'));
          return [...(result.results as Document[]), ...clean];
        });
      }
      toast.success('Documents uploaded successfully.');
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDelete = (docId: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));

    startTransition(() => {
      deleteDocumentAction(docId, sessionId).then((res) => {
        if (!res.success) {
          toast.error('Failed to delete document.');
        }
      });
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-muted/30 p-6 rounded-2xl border border-border/50 border-dashed">
        <div className="flex flex-col gap-1">
          <h3 className="font-medium text-foreground">Add Documents</h3>
          <p className="text-sm text-muted-foreground">
            Upload PDFs, TXTs, MDs, or DOCXs to your knowledge base.
          </p>
        </div>
        <div>
          <input
            type="file"
            multiple
            className="hidden"
            ref={fileInputRef}
            onChange={handleUpload}
            accept=".pdf,.txt,.md,.docx"
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="gap-2"
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <UploadCloud className="h-4 w-4" />
            )}
            Select Files
          </Button>
        </div>
      </div>

      <div className="border rounded-2xl overflow-hidden bg-background shadow-sm">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Added</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-32 text-center text-muted-foreground">
                  No documents found in this session.
                </TableCell>
              </TableRow>
            ) : (
              documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <File className="h-4 w-4 text-muted-foreground" />
                      {doc.original_file_name}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        doc.status === 'ready'
                          ? 'default'
                          : doc.status === 'failed'
                            ? 'destructive'
                            : 'secondary'
                      }
                      className={
                        doc.status === 'processing'
                          ? 'bg-primary/20 text-primary hover:bg-primary/30 border-none'
                          : ''
                      }
                    >
                      {doc.status === 'processing' && (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      )}
                      {doc.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(doc.id)}
                      disabled={isPending || doc.status === 'processing'}
                      aria-label="Delete document"
                      className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
