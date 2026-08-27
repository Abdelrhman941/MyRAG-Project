import { SidebarProvider } from '@/components/ui/sidebar';
import { Skeleton } from '@/components/ui/skeleton';

export default function ChatLayoutLoading() {
  return (
    <SidebarProvider>
      <div className="w-[250px] border-r flex flex-col p-4 gap-4">
        <Skeleton className="h-10 w-full rounded-xl" />
        <div className="mt-8 space-y-3">
          <Skeleton className="h-5 w-24 mb-4" />
          <Skeleton className="h-8 w-full rounded-md" />
          <Skeleton className="h-8 w-full rounded-md" />
        </div>
      </div>
      <main className="flex-1 flex flex-col h-screen bg-background">
        <header className="flex h-14 shrink-0 items-center border-b px-4">
          <Skeleton className="h-8 w-8 rounded-md" />
        </header>
        <div className="flex-1 overflow-hidden relative p-8">
          <Skeleton className="h-full w-full rounded-2xl" />
        </div>
      </main>
    </SidebarProvider>
  );
}
