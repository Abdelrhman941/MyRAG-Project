import { AppSidebar } from '@/components/layout/app-sidebar';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { getSessions } from '@/lib/api';

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const sessions = await getSessions();

  return (
    <SidebarProvider className="app-page-enter">
      <AppSidebar initialSessions={sessions} />
      <main className="relative flex h-screen flex-1 flex-col overflow-hidden bg-background">
        <div className="absolute top-3 left-3 z-50">
          <SidebarTrigger />
        </div>
        <div className="flex-1 overflow-hidden relative">{children}</div>
      </main>
    </SidebarProvider>
  );
}
