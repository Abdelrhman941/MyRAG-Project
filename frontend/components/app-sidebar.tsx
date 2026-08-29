'use client';

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useDocuments } from '@/hooks/use-documents';
import { createSessionAction, deleteSessionAction } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Document, Session } from '@/lib/types';
import { FileCode2, FileText, Files, Loader2, MessageSquare, Moon, Plus, Sun, Trash2, TrashIcon } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useState, useTransition } from 'react';
import { toast } from 'sonner';

function relativeDate(value: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return 'now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(value).toLocaleDateString();
}

function FileTypeIcon({ document }: { document: Document }) {
  const extension = document.original_file_name.split('.').pop()?.toLowerCase();
  return extension === 'md' || extension === 'txt' ? <FileCode2 className="size-3.5 shrink-0" /> : <FileText className="size-3.5 shrink-0" />;
}

function StatusDot({ status }: { status: Document['status'] }) {
  if (status === 'processing' || status === 'uploaded') return <span className="size-1.5 shrink-0 rounded-full bg-amber-500 animate-pulse" />;
  if (status === 'deleting') return <span className="size-1.5 shrink-0 rounded-full bg-neutral-400 animate-pulse" />;
  if (status === 'failed') return <span className="size-1.5 shrink-0 rounded-full bg-red-500" />;
  return <span className="size-1.5 shrink-0 rounded-full bg-emerald-500" />;
}

export function AppSidebar({ initialSessions }: { initialSessions: Session[] }) {
  const pathname = usePathname();
  const config = useConfig();
  const { resolvedTheme, setTheme } = useTheme();
  const [isPending, startTransition] = useTransition();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const match = pathname.match(/\/chat\/([^/]+)/);
  const activeSessionId = match ? match[1] : null;
  const { documents } = useDocuments(activeSessionId);

  const handleNewChat = () => startTransition(() => createSessionAction());
  const deleteSession = (id: string, force = false) => {
    setDeletingId(id);
    startTransition(() => {
      deleteSessionAction(id, activeSessionId ?? undefined, initialSessions, force).then((result) => {
        setDeletingId(null);
        if (result && !result.success) {
          if (result.error?.code === 'document_processing' && !force) {
            toast.error('Cannot delete this chat while documents are processing.', { action: { label: 'Force Delete', onClick: () => deleteSession(id, true) } });
          } else toast.error(result.error?.message || 'Failed to delete chat.');
          return;
        }
        toast.success('Chat deleted.');
      });
    });
  };
  const deleteAllChats = () => {
    setConfirmDeleteAll(false);
    startTransition(() => {
      Promise.all(initialSessions.map((session) => deleteSessionAction(session.id, undefined, initialSessions, true))).then((results) => {
        if (results.some((result) => !result?.success)) {
          toast.error('Some chats could not be deleted.');
          return;
        }
        toast.success('All chats deleted.');
        createSessionAction();
      }).catch(() => toast.error('Failed to delete all chats.'));
    });
  };

  return <Sidebar className="border-sidebar-border">
    <SidebarHeader className="gap-4 p-4"><div className="flex items-center gap-2.5 px-1"><div className="flex size-8 items-center justify-center rounded-lg bg-sidebar-primary font-bold text-sidebar-primary-foreground">R</div><span className="truncate text-sm font-semibold">{config?.app_name || 'RAG Assistant'}</span></div><Button onClick={handleNewChat} disabled={isPending} className="w-full justify-start gap-2"><Plus className="size-4" />New Chat</Button></SidebarHeader>
    <Separator />
    <SidebarContent className="px-2 py-3">
      {activeSessionId && <SidebarGroup className="p-0"><SidebarGroupLabel className="gap-2 px-2"><Files className="size-3.5" />Current workspace</SidebarGroupLabel><SidebarGroupContent><SidebarMenu><SidebarMenuItem><SidebarMenuButton render={<Link href={`/chat/${activeSessionId}`} />} isActive={pathname === `/chat/${activeSessionId}`}><MessageSquare className="size-4" /><span>Chat</span></SidebarMenuButton></SidebarMenuItem><SidebarMenuItem><SidebarMenuButton render={<Link href={`/chat/${activeSessionId}/documents`} />} isActive={pathname === `/chat/${activeSessionId}/documents`}><Files className="size-4" /><span>Knowledge Base</span><span className="ml-auto text-xs text-muted-foreground">{documents.length}</span></SidebarMenuButton></SidebarMenuItem></SidebarMenu><div className="mt-1 max-h-52 overflow-y-auto px-2 pb-1 custom-scrollbar">{documents.length ? documents.map((document) => <div key={document.id} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-sidebar-foreground/70"><StatusDot status={document.status} /><FileTypeIcon document={document} /><span className="min-w-0 flex-1 truncate" title={document.original_file_name}>{document.original_file_name}</span></div>) : <p className="px-2 py-2 text-xs text-muted-foreground">No documents yet</p>}</div></SidebarGroupContent></SidebarGroup>}
      <Separator className="my-3" />
      <SidebarGroup className="p-0"><SidebarGroupLabel className="gap-2 px-2"><MessageSquare className="size-3.5" />Chats</SidebarGroupLabel><SidebarGroupContent><SidebarMenu>{initialSessions.length ? initialSessions.map((session) => <SidebarMenuItem key={session.id} className="group relative"><SidebarMenuButton render={<Link href={`/chat/${session.id}`} />} isActive={activeSessionId === session.id} className="pr-10"><div className="min-w-0 flex-1"><span className="block truncate">{session.title || 'New Chat'}</span><span className="block text-[11px] text-muted-foreground">{relativeDate(session.updated_at || session.created_at)}</span></div></SidebarMenuButton><button type="button" onClick={() => setSessionToDelete(session.id)} disabled={isPending} aria-label="Delete chat" className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 focus:opacity-100 disabled:opacity-50">{deletingId === session.id ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}</button></SidebarMenuItem>) : <p className="px-3 py-4 text-center text-xs text-muted-foreground">No chats yet — start one!</p>}</SidebarMenu></SidebarGroupContent></SidebarGroup>
    </SidebarContent>
    <SidebarFooter className="border-t border-sidebar-border p-3"><div className="flex items-center justify-between"><Tooltip><TooltipTrigger render={<button type="button" onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')} className="rounded-md p-2 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground" />}><Sun className="size-4 dark:hidden" /><Moon className="hidden size-4 dark:block" /></TooltipTrigger><TooltipContent>Toggle theme</TooltipContent></Tooltip><Tooltip><TooltipTrigger render={<button type="button" onClick={() => setConfirmDeleteAll(true)} disabled={!initialSessions.length || isPending} className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-40" />}><TrashIcon className="size-4" /></TooltipTrigger><TooltipContent>Delete all chats</TooltipContent></Tooltip></div></SidebarFooter>
    <AlertDialog open={sessionToDelete !== null} onOpenChange={(open) => !open && setSessionToDelete(null)}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete this chat?</AlertDialogTitle><AlertDialogDescription>Its messages and documents will be removed.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={() => { if (sessionToDelete) deleteSession(sessionToDelete); setSessionToDelete(null); }}>Delete chat</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    <AlertDialog open={confirmDeleteAll} onOpenChange={setConfirmDeleteAll}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete all chats?</AlertDialogTitle><AlertDialogDescription>This will permanently delete ALL chats and their documents.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={deleteAllChats}>Delete all chats</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </Sidebar>;
}
