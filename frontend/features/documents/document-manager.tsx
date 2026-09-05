'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
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
import { useConfig } from '@/lib/config';
import type { Document } from '@/lib/types';
import { File, FileUp, Loader2, Trash2, UploadCloud, RotateCcw } from 'lucide-react';
import { useRef, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { useDocuments } from './use-documents';

function formatSize(bytes?: number | null) {
  if (bytes == null) return '—';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const BUSY_STATUSES: Document['status'][] = ['processing', 'uploaded', 'deleting'];

function isBusy(document: Document) {
  return BUSY_STATUSES.includes(document.status);
}

function DocumentStatusBadge({ status }: { status: Document['status'] }) {
  const isWorking = BUSY_STATUSES.includes(status);
  const label = status === 'deleting' ? 'Deleting…' : isWorking ? 'Indexing…' : status;
  const variant =
    status === 'ready' ? 'default' : status === 'failed' ? 'destructive' : 'secondary';

  return (
    <Badge
      variant={variant}
      className={
        status === 'deleting'
          ? 'border-none bg-neutral-500/15 text-neutral-500'
          : status === 'processing'
            ? 'border-none bg-primary/20 text-primary'
            : undefined
      }
    >
      {isWorking && <Loader2 className="mr-1 size-3 animate-spin" />}
      {label}
    </Badge>
  );
}

export function DocumentManager({
  initialDocuments,
  sessionId,
}: {
  initialDocuments: Document[];
  sessionId: string;
}) {
  const { documents, isUploading, isPending, uploadFiles, handleDelete, handleRetry, deleteDocument } =
    useDocuments(sessionId, initialDocuments);
  const config = useConfig();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);
  const [isDeletingAll, startDeleteAll] = useTransition();
  const hasBusyDocuments = documents.some(isBusy);

  const selectFiles = () => fileInputRef.current?.click();

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) await uploadFiles(event.target.files);
    event.target.value = '';
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    await uploadFiles(event.dataTransfer.files);
  };

  const deleteAll = () => {
    setIsDeleteAllOpen(false);
    startDeleteAll(async () => {
      const results = await Promise.all(documents.map((document) => deleteDocument(document.id)));
      toast[results.every(Boolean) ? 'success' : 'error'](
        results.every(Boolean) ? 'All documents deleted.' : 'Some documents could not be deleted.'
      );
    });
  };

  return (
    <div className="space-y-6">
      <div
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (event.currentTarget === event.target) setIsDragging(false);
        }}
        onDrop={handleDrop}
        className={`flex flex-col gap-5 rounded-2xl border border-dashed p-6 transition-colors sm:flex-row sm:items-center sm:justify-between ${
          isDragging ? 'border-primary bg-primary/10' : 'border-border/70 bg-muted/30'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
            <FileUp className="size-5" />
          </div>
          <div>
            <h3 className="font-medium text-foreground">Add Documents</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Drop files here or click Select Files
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {config
                ? `${config.accepted_extensions.join(', ')} · up to ${config.max_file_size_mb}MB`
                : 'Loading upload limits…'}
            </p>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          accept={config?.accepted_extensions.join(',')}
          onChange={handleUpload}
        />
        <Button onClick={selectFiles} disabled={isUploading || !config} className="gap-2">
          {isUploading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <UploadCloud className="size-4" />
          )}
          Select Files
        </Button>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold">Documents</h2>
          <p className="text-sm text-muted-foreground">{documents.length} in this knowledge base</p>
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setIsDeleteAllOpen(true)}
          disabled={!documents.length || hasBusyDocuments || isDeletingAll || isPending}
          className="gap-2"
        >
          <Trash2 className="size-3.5" />
          Delete all documents
        </Button>
      </div>

      <div className="overflow-hidden rounded-2xl border bg-background shadow-sm">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Added</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-48">
                  <div className="flex flex-col items-center justify-center gap-3 text-muted-foreground">
                    <FileUp className="size-8" />
                    <p>Drop files here or click Select Files</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              documents.map((document) => (
                <TableRow key={document.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <File className="size-4 text-muted-foreground" />
                      <span className="max-w-64 truncate">{document.original_file_name}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <DocumentStatusBadge status={document.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatSize(document.file_size_bytes)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(document.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {document.status === 'failed' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRetry(document.id)}
                        disabled={isPending}
                        aria-label="Retry document"
                        className="text-muted-foreground hover:bg-neutral-100 dark:hover:bg-[#404040]"
                      >
                        <RotateCcw className="size-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(document.id)}
                      disabled={isPending || isBusy(document)}
                      aria-label="Delete document"
                      className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <AlertDialog open={isDeleteAllOpen} onOpenChange={setIsDeleteAllOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete all documents?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes every document in this knowledge base.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={deleteAll}>
              Delete all documents
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
