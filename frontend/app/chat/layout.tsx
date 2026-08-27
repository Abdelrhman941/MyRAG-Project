import { AppSidebar } from '@/components/app-sidebar';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { getSessions } from '@/lib/api';

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const sessions = await getSessions();

  return (
    <SidebarProvider>
      <AppSidebar initialSessions={sessions || []} />
      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-background">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
        </header>
        <div className="flex-1 overflow-hidden relative">{children}</div>
      </main>
    </SidebarProvider>
  );
}
