"use client";

import { ClipList } from "@/components/clip/clip-list";
import { Badge } from "@/components/ui/badge";
import { useJob } from "@/lib/hooks/use-jobs";
import { statusLabel, statusVariant } from "@/lib/status";

export function JobProgress({ jobId }: { jobId: string }) {
  const { data: job, isLoading, error } = useJob(jobId);

  if (isLoading) {
    return <p className="text-muted-foreground">Memuat job...</p>;
  }
  if (error || !job) {
    return <p className="text-destructive">Gagal memuat job{error ? `: ${error.message}` : ""}.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="truncate text-2xl font-semibold">{job.original_filename}</h1>
        <Badge variant={statusVariant(job.status)}>{statusLabel(job.status)}</Badge>
      </div>

      <div className="space-y-1">
        <div className="bg-secondary h-2 w-full overflow-hidden rounded-full">
          <div
            className="bg-primary h-full transition-all"
            style={{ width: `${job.progress_pct}%` }}
          />
        </div>
        <p className="text-muted-foreground text-sm">
          {job.progress_message || "—"} ({job.progress_pct}%)
        </p>
      </div>

      {job.status === "failed" && job.error_message ? (
        <p className="text-destructive text-sm">{job.error_message}</p>
      ) : null}

      {job.status === "ready_for_review" ? <ClipList jobId={jobId} /> : null}
    </div>
  );
}
