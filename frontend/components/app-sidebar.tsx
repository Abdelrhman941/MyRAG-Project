'use client';

import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { createSessionAction, deleteSessionAction } from '@/lib/api';
import { Files, Loader2, MessageSquare, PlusCircle, Trash2 } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useState, useTransition } from 'react';
import { toast } from 'sonner';

export function AppSidebar({
  initialSessions,
}: {
  initialSessions: import('@/lib/types').Session[];
}) {
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleNewChat = () => {
    startTransition(() => {
      createSessionAction();
    });
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    startTransition(() => {
      const currentMatch = pathname.match(/\/chat\/([^\/]+)/);
      const activeId = currentMatch ? currentMatch[1] : undefined;

      deleteSessionAction(id, activeId, initialSessions).then((res) => {
        setDeletingId(null);
        if (res && !res.success) {
          if (res.error?.code === 'document_processing') {
            toast.error('Cannot delete session while documents are processing.');
          } else {
            toast.error(res.error?.message || 'Failed to delete session.');
          }
        } else {
          toast.success('Session deleted.');
        }
      });
    });
  };

  const match = pathname.match(/\/chat\/([^\/]+)/);
  const activeSessionId = match ? match[1] : null;

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Button
          onClick={handleNewChat}
          disabled={isPending}
          className="w-full justify-start gap-2 bg-primary/10 text-primary hover:bg-primary/20 border-none shadow-none"
        >
          {isPending && !deletingId ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <PlusCircle className="h-4 w-4" />
          )}
          New Chat
        </Button>
      </SidebarHeader>

      <SidebarContent>
        {activeSessionId && (
          <SidebarGroup>
            <SidebarGroupLabel>Current Workspace</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<a href={`/chat/${activeSessionId}`} />}
                    isActive={pathname === `/chat/${activeSessionId}`}
                  >
                    <MessageSquare className="h-4 w-4" />
                    <span>Chat</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<a href={`/chat/${activeSessionId}/documents`} />}
                    isActive={pathname === `/chat/${activeSessionId}/documents`}
                  >
                    <Files className="h-4 w-4" />
                    <span>Knowledge Base</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        <SidebarGroup>
          <SidebarGroupLabel>Past Sessions</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {initialSessions.map((session) => (
                <SidebarMenuItem
                  key={session.id}
                  className="group flex items-center justify-between"
                >
                  <SidebarMenuButton
                    render={<a href={`/chat/${session.id}`} className="truncate block w-full" />}
                    isActive={activeSessionId === session.id}
                    className="flex-1 truncate"
                  >
                    <span className="truncate">{session.id.split('-')[0]}...</span>
                  </SidebarMenuButton>
                  <button
                    onClick={() => handleDelete(session.id)}
                    className="opacity-0 group-hover:opacity-100 p-2 text-muted-foreground hover:text-destructive transition-opacity"
                    aria-label="Delete session"
                    disabled={isPending}
                  >
                    {deletingId === session.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
