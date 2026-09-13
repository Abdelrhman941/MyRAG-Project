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
import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useDocuments } from '@/features/documents/use-documents';
import { useThemeTransition } from '@/hooks/use-theme-transition';
import { createSessionAction, deleteSessionAction } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Document, Session } from '@/lib/types';
import { parseUtcDate } from '@/lib/utils';
import {
  FileCode2,
  FileText,
  Files,
  Loader2,
  MessageSquare,
  Moon,
  Plus,
  Sun,
  Trash2,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState, useTransition } from 'react';
import { toast } from 'sonner';

function relativeDate(value: string): string {
  const date = parseUtcDate(value);
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));

  if (seconds < 60) return 'now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

  return date.toLocaleDateString();
}

function useRelativeDate(value: string): string {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);
  return mounted ? relativeDate(value) : '';
}

function SessionDate({ value }: { value: string }) {
  const label = useRelativeDate(value);
  return <>{label}</>;
}

function FileTypeIcon({ document }: { document: Document }) {
  const extension = document.original_file_name.split('.').pop()?.toLowerCase();
  const Icon = extension === 'md' || extension === 'txt' ? FileCode2 : FileText;

  return <Icon className="size-3.5 shrink-0" />;
}

function StatusDot({ status }: { status: Document['status'] }) {
  const color = {
    processing: 'bg-amber-500 animate-pulse',
    uploaded: 'bg-amber-500 animate-pulse',
    deleting: 'bg-neutral-400 animate-pulse',
    failed: 'bg-red-500',
    ready: 'bg-emerald-500',
  }[status];

  return <span className={`size-1.5 shrink-0 rounded-full ${color}`} />;
}

function WorkspaceNavigation({
  activeSessionId,
  pathname,
  documents,
}: {
  activeSessionId: string;
  pathname: string;
  documents: Document[];
}) {
  return (
    <SidebarGroup className="p-0">
      <div className="px-3 pt-4 pb-2 text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground/60">
        Workspace
      </div>

      <SidebarGroupContent className="px-2">
        <SidebarMenu className="gap-1">
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<Link href={`/chat/${activeSessionId}`} />}
              isActive={pathname === `/chat/${activeSessionId}`}
              className="h-10 rounded-lg transition-colors hover:bg-sidebar-accent/50 data-[active=true]:bg-sidebar-accent/80"
            >
              <MessageSquare className="size-4" />
              <span>Chat</span>
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem>
            <SidebarMenuButton
              render={<Link href={`/chat/${activeSessionId}/documents`} />}
              isActive={pathname === `/chat/${activeSessionId}/documents`}
              className="h-10 rounded-lg transition-colors hover:bg-sidebar-accent/50 data-[active=true]:bg-sidebar-accent/80"
            >
              <Files className="size-4" />
              <span>Knowledge Base</span>
              <span className="ml-auto text-xs text-muted-foreground">{documents.length}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <div className="mt-2 max-h-52 overflow-y-auto pb-1 custom-scrollbar">
          {documents.length ? (
            documents.map((document) => (
              <div
                key={document.id}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent/30"
              >
                <StatusDot status={document.status} />
                <FileTypeIcon document={document} />
                <span className="min-w-0 flex-1 truncate" title={document.original_file_name}>
                  {document.original_file_name}
                </span>
              </div>
            ))
          ) : (
            <div className="mx-1 my-1 flex items-center justify-center rounded-lg border border-dashed border-sidebar-border/70 px-3 py-3">
              <p className="text-[11px] text-muted-foreground/70">No documents yet</p>
            </div>
          )}
        </div>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

function ChatList({
  sessions,
  activeSessionId,
  isPending,
  deletingId,
  onDelete,
}: {
  sessions: Session[];
  activeSessionId: string | null;
  isPending: boolean;
  deletingId: string | null;
  onDelete: (sessionId: string) => void;
}) {
  return (
    <SidebarGroup className="flex flex-1 flex-col overflow-hidden p-0">
      <div className="shrink-0 px-3 pt-3 pb-2 text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground/60">
        Chats
      </div>

      <SidebarGroupContent className="flex-1 overflow-y-auto custom-scrollbar px-2 pb-2">
        <SidebarMenu className="gap-1.5">
          {sessions.length ? (
            sessions.map((session) => (
              <SidebarMenuItem key={session.id} className="group relative">
                <SidebarMenuButton
                  render={<Link href={`/chat/${session.id}`} />}
                  isActive={activeSessionId === session.id}
                  className="h-auto min-h-13 rounded-xl border border-transparent py-2.5 pr-10 transition-all hover:bg-sidebar-accent/50 data-[active=true]:border-sidebar-border/50 data-[active=true]:bg-sidebar-accent/80 data-[active=true]:shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium leading-snug">
                      {session.title || 'New Chat'}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-muted-foreground">
                      <SessionDate value={session.updated_at || session.created_at} />
                    </span>
                  </div>
                </SidebarMenuButton>

                <button
                  type="button"
                  onClick={() => onDelete(session.id)}
                  disabled={isPending}
                  aria-label="Delete chat"
                  className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive focus:opacity-100 group-hover:opacity-100 disabled:opacity-50"
                >
                  {deletingId === session.id ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="size-3.5" />
                  )}
                </button>
              </SidebarMenuItem>
            ))
          ) : (
            <p className="px-3 py-4 text-center text-xs text-muted-foreground">
              No chats yet — start one!
            </p>
          )}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar({ initialSessions }: { initialSessions: Session[] }) {
  const pathname = usePathname();
  const config = useConfig();
  const { theme, toggleTheme, isTransitioning: isThemeTransitioning } = useThemeTransition();

  const [isPending, startTransition] = useTransition();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);

  const activeSessionId = pathname.match(/\/chat\/([^/]+)/)?.[1] ?? null;
  const { documents } = useDocuments(activeSessionId);

  const deleteSession = (sessionId: string, force = false) => {
    setDeletingId(sessionId);

    startTransition(async () => {
      const result = await deleteSessionAction(
        sessionId,
        activeSessionId ?? undefined,
        initialSessions,
        force
      );

      setDeletingId(null);

      if (!result.success) {
        if (result.error?.code === 'document_processing' && !force) {
          toast.error('Cannot delete this chat while documents are processing.', {
            action: {
              label: 'Force Delete',
              onClick: () => deleteSession(sessionId, true),
            },
          });
        } else {
          toast.error(result.error?.message || 'Failed to delete chat.');
        }

        return;
      }

      toast.success('Chat deleted.');
    });
  };

  const deleteAllChats = () => {
    setIsDeleteAllOpen(false);

    startTransition(async () => {
      let results;

      try {
        results = await Promise.all(
          initialSessions.map((session) =>
            deleteSessionAction(session.id, undefined, initialSessions, true)
          )
        );
      } catch {
        toast.error('Failed to delete all chats.');
        return;
      }

      if (results.some((result) => !result.success)) {
        toast.error('Some chats could not be deleted.');
        return;
      }

      toast.success('All chats deleted.');
      await createSessionAction();
    });
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        startTransition(() => createSessionAction());
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <Sidebar className="border-sidebar-border">
      <SidebarHeader className="gap-4 p-4 pb-2">
        <div
          className="flex h-10 items-center gap-2 px-1"
          role="img"
          aria-label={config?.app_name || 'Nova'}
        >
          <Image
            src="/images/logos/nova-icon.webp"
            alt="Nova"
            width={40}
            height={40}
            className="size-10 shrink-0"
          />

          <div className="relative ml-1 h-10 w-32">
            <Image
              src="/images/logos/nova-text.webp"
              alt="Nova"
              fill
              className="object-contain object-left brightness-0 dark:invert"
            />
          </div>
        </div>

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                onClick={() => startTransition(() => createSessionAction())}
                disabled={isPending}
                className="mt-1 h-10 w-full justify-start gap-2 rounded-xl"
              >
                <Plus className="size-4" />
                New Chat
              </Button>
            }
          />
          <TooltipContent>New Chat ⌘K</TooltipContent>
        </Tooltip>
      </SidebarHeader>

      <SidebarContent className="mt-2 flex flex-col gap-2 overflow-hidden px-2 pb-2">
        <div className="flex shrink-0 flex-col">
          {activeSessionId && (
            <WorkspaceNavigation
              activeSessionId={activeSessionId}
              pathname={pathname}
              documents={documents}
            />
          )}
        </div>

        <ChatList
          sessions={initialSessions}
          activeSessionId={activeSessionId}
          isPending={isPending}
          deletingId={deletingId}
          onDelete={setSessionToDelete}
        />
      </SidebarContent>

      <SidebarFooter className="p-3 pt-0">
        <div className="flex items-center gap-1 rounded-xl border border-sidebar-border/50 bg-sidebar-accent/30 p-1">
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  onClick={toggleTheme}
                  disabled={isThemeTransitioning}
                  aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
                  className="flex flex-1 items-center justify-center rounded-lg p-2.5 text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground disabled:opacity-50"
                />
              }
            >
              <Sun className="size-4 dark:hidden" />
              <Moon className="hidden size-4 dark:block" />
            </TooltipTrigger>
            <TooltipContent>Toggle theme</TooltipContent>
          </Tooltip>

          <div className="mx-0.5 h-5 w-px shrink-0 bg-sidebar-border/50" />

          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  onClick={() => setIsDeleteAllOpen(true)}
                  disabled={!initialSessions.length || isPending}
                  className="flex flex-1 items-center justify-center rounded-lg p-2.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
                />
              }
            >
              <Trash2 className="size-4" />
            </TooltipTrigger>
            <TooltipContent>Delete all chats</TooltipContent>
          </Tooltip>
        </div>
      </SidebarFooter>

      <AlertDialog
        open={sessionToDelete !== null}
        onOpenChange={(open) => !open && setSessionToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              Its messages and documents will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>

            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (sessionToDelete) {
                  deleteSession(sessionToDelete);
                }

                setSessionToDelete(null);
              }}
            >
              Delete chat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={isDeleteAllOpen} onOpenChange={setIsDeleteAllOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete all chats?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete ALL chats and their documents.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={deleteAllChats}>
              Delete all chats
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sidebar>
  );
}
