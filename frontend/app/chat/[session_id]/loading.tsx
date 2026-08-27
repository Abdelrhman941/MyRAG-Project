import { Skeleton } from '@/components/ui/skeleton';

export default function ChatSessionLoading() {
  return (
    <div className="flex flex-col h-full bg-muted/20 px-4 py-6">
      <div className="max-w-3xl mx-auto w-full space-y-6">
        <div className="flex justify-end">
          <Skeleton className="h-16 w-64 rounded-2xl" />
        </div>
        <div className="flex justify-start">
          <Skeleton className="h-24 w-80 rounded-2xl" />
        </div>
        <div className="flex justify-end">
          <Skeleton className="h-12 w-48 rounded-2xl" />
        </div>
      </div>
      <div className="absolute bottom-0 left-0 w-full pt-10 pb-4 px-4 bg-gradient-to-t from-muted/20 to-transparent">
        <div className="max-w-3xl mx-auto">
          <Skeleton className="h-14 w-full rounded-2xl" />
        </div>
      </div>
    </div>
  );
}
