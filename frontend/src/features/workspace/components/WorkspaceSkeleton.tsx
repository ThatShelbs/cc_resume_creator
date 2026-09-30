import { Skeleton } from "@/components/ui/primitives";

export function WorkspaceSkeleton() {
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
      <Skeleton className="h-5 w-24" />
      <div className="mt-4 flex items-center gap-3">
        <Skeleton className="size-12 rounded-lg" />
        <div className="grid gap-2">
          <Skeleton className="h-6 w-72" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
      <Skeleton className="mt-8 h-9 w-[480px] max-w-full" />
      <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_44%]">
        <div className="grid gap-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-64" />
          <Skeleton className="h-48" />
        </div>
        <Skeleton className="hidden aspect-[8.5/11] lg:block" />
      </div>
    </div>
  );
}
