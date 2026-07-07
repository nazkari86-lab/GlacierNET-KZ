export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-zinc-200 ${className}`}
      aria-hidden="true"
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm" aria-busy="true" aria-label="Loading">
      <Skeleton className="mb-4 h-5 w-40" />
      <Skeleton className="mb-2 h-4 w-full" />
      <Skeleton className="mb-2 h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="overflow-x-auto" aria-busy="true" aria-label="Loading table">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-zinc-500">
            <th className="pb-2 font-medium">Date</th>
            <th className="pb-2 font-medium">Model</th>
            <th className="pb-2 font-medium">Area</th>
            <th className="pb-2 font-medium">Year</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-b border-zinc-100">
              <td className="py-3"><Skeleton className="h-4 w-20" /></td>
              <td className="py-3"><Skeleton className="h-4 w-24" /></td>
              <td className="py-3"><Skeleton className="h-4 w-16" /></td>
              <td className="py-3"><Skeleton className="h-4 w-12" /></td>
              <td className="py-3"><Skeleton className="h-5 w-16 rounded-full" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MapSkeleton() {
  return (
    <div className="relative h-96 overflow-hidden rounded-xl" aria-busy="true" aria-label="Loading map">
      <Skeleton className="h-full w-full" />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm text-zinc-400">Loading map...</span>
      </div>
    </div>
  );
}
