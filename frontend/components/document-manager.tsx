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
import { Document } from '@/lib/types';
import { File, Loader2, Trash2, UploadCloud } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useDocuments } from '@/hooks/use-documents';

export function DocumentManager({
  initialDocuments,
  sessionId,
}: {
  initialDocuments: Document[];
  sessionId: string;
}) {
  const { documents, setDocuments, isUploading, isPending, uploadFiles, handleDelete } = useDocuments(sessionId, initialDocuments);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync if initialDocuments change (from server actions revalidating)
  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments, setDocuments]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await uploadFiles(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
