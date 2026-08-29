'use client';

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useDocuments } from '@/hooks/use-documents';
import { useConfig } from '@/lib/config';
import type { Document } from '@/lib/types';
import { File, FileUp, Loader2, Trash2, UploadCloud } from 'lucide-react';
import { useRef, useState, useTransition } from 'react';
import { toast } from 'sonner';

export function DocumentManager({ initialDocuments, sessionId }: { initialDocuments: Document[]; sessionId: string }) {
  const { documents, isUploading, isPending, uploadFiles, handleDelete, deleteDocument } = useDocuments(sessionId, initialDocuments);
  const config = useConfig();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [isDeletingAll, startDeleteAll] = useTransition();
  const hasBusyDocuments = documents.some((document) => ['processing', 'uploaded', 'deleting'].includes(document.status));

  const submitFiles = async (files: FileList | File[]) => {
    if (!config || !files.length) return;
    const invalid = Array.from(files).find((file) => {
      const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
      return file.size > config.max_file_size_mb * 1024 * 1024 || !config.accepted_extensions.includes(extension);
    });
    if (invalid) {
      const extension = `.${invalid.name.split('.').pop()?.toLowerCase()}`;
      if (!config.accepted_extensions.includes(extension)) toast.error(`Unsupported file type. Supported types: ${config.accepted_extensions.join(', ')}.`);
      else toast.error(`Files must be ${config.max_file_size_mb}MB or smaller.`);
      return;
    }
    await uploadFiles(files);
  };
  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) await submitFiles(event.target.files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };
  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    await submitFiles(event.dataTransfer.files);
  };
  const deleteAll = () => {
    setConfirmDeleteAll(false);
    startDeleteAll(async () => {
      const results = await Promise.all(documents.map((document) => deleteDocument(document.id)));
      if (results.every(Boolean)) toast.success('All documents deleted.');
      else toast.error('Some documents could not be deleted.');
    });
  };

  return <div className="space-y-6">
    <div onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (event.currentTarget === event.target) setIsDragging(false); }} onDrop={handleDrop} className={`flex flex-col gap-5 rounded-2xl border border-dashed p-6 transition-colors sm:flex-row sm:items-center sm:justify-between ${isDragging ? 'border-primary bg-primary/10' : 'border-border/70 bg-muted/30'}`}>
      <div className="flex items-start gap-3"><div className="rounded-xl bg-primary/10 p-2.5 text-primary"><FileUp className="size-5" /></div><div><h3 className="font-medium text-foreground">Add Documents</h3><p className="mt-1 text-sm text-muted-foreground">Drop files here or click Select Files</p><p className="mt-1 text-xs text-muted-foreground">{config ? `${config.accepted_extensions.join(', ')} · up to ${config.max_file_size_mb}MB` : 'Loading upload limits…'}</p></div></div>
      <input type="file" multiple className="hidden" ref={fileInputRef} onChange={handleUpload} accept={config?.accepted_extensions.join(',')} />
      <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading || !config} className="gap-2">{isUploading ? <Loader2 className="size-4 animate-spin" /> : <UploadCloud className="size-4" />}Select Files</Button>
    </div>
    <div className="flex items-center justify-between gap-4"><div><h2 className="font-semibold">Documents</h2><p className="text-sm text-muted-foreground">{documents.length} in this knowledge base</p></div><Button variant="destructive" size="sm" onClick={() => setConfirmDeleteAll(true)} disabled={!documents.length || hasBusyDocuments || isDeletingAll || isPending} className="gap-2"><Trash2 className="size-3.5" />Delete all documents</Button></div>
    <div className="overflow-hidden rounded-2xl border bg-background shadow-sm"><Table><TableHeader className="bg-muted/50"><TableRow><TableHead>Filename</TableHead><TableHead>Status</TableHead><TableHead>Added</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>{documents.length === 0 ? <TableRow><TableCell colSpan={4} className="h-48"><div className="flex flex-col items-center justify-center gap-3 text-muted-foreground"><FileUp className="size-8" /><p>Drop files here or click Select Files</p></div></TableCell></TableRow> : documents.map((document) => <TableRow key={document.id}><TableCell className="font-medium"><div className="flex items-center gap-2"><File className="size-4 text-muted-foreground" /><span className="max-w-64 truncate">{document.original_file_name}</span></div></TableCell><TableCell><Badge variant={document.status === 'ready' ? 'default' : document.status === 'failed' ? 'destructive' : 'secondary'} className={document.status === 'deleting' ? 'border-none bg-neutral-500/15 text-neutral-500' : document.status === 'processing' ? 'border-none bg-primary/20 text-primary' : ''}>{['processing', 'uploaded', 'deleting'].includes(document.status) && <Loader2 className="mr-1 size-3 animate-spin" />}{document.status === 'deleting' ? 'Deleting…' : ['processing', 'uploaded'].includes(document.status) ? 'Indexing…' : document.status}</Badge></TableCell><TableCell className="text-sm text-muted-foreground">{new Date(document.created_at).toLocaleDateString()}</TableCell><TableCell className="text-right"><Button variant="ghost" size="icon" onClick={() => handleDelete(document.id)} disabled={isPending || ['processing', 'uploaded', 'deleting'].includes(document.status)} aria-label="Delete document" className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"><Trash2 className="size-4" /></Button></TableCell></TableRow>)}</TableBody></Table></div>
    <AlertDialog open={confirmDeleteAll} onOpenChange={setConfirmDeleteAll}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete all documents?</AlertDialogTitle><AlertDialogDescription>This permanently deletes every document in this knowledge base.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={deleteAll}>Delete all documents</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </div>;
}
