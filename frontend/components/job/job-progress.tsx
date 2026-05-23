"use client";

import { JobReview } from "@/components/job/job-review";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCancelJob, useJob, useRetryJob } from "@/lib/hooks/use-jobs";
import { IN_PROGRESS_STATUSES, statusLabel, statusVariant } from "@/lib/status";

export function JobProgress({ jobId }: { jobId: string }) {
  const { data: job, isLoading, error } = useJob(jobId);
  const cancel = useCancelJob(jobId);
  const retry = useRetryJob(jobId);

  if (isLoading) {
    return <p className="text-muted-foreground">Memuat job...</p>;
  }
  if (error || !job) {
    return <p className="text-destructive">Gagal memuat job{error ? `: ${error.message}` : ""}.</p>;
  }

  const inProgress = IN_PROGRESS_STATUSES.includes(job.status);
  const canRetry = job.status === "failed" || job.status === "cancelled";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="truncate text-2xl font-semibold">{job.original_filename}</h1>
        <div className="flex items-center gap-2">
          <Badge variant={statusVariant(job.status)}>{statusLabel(job.status)}</Badge>
          {inProgress ? (
            <Button
              variant="outline"
              size="sm"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate()}
            >
              Batalkan
            </Button>
          ) : null}
          {canRetry ? (
            <Button size="sm" disabled={retry.isPending} onClick={() => retry.mutate()}>
              {retry.isPending ? "Mengulang..." : "Coba lagi"}
            </Button>
          ) : null}
        </div>
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
      {cancel.error ? <p className="text-destructive text-sm">{cancel.error.message}</p> : null}
      {retry.error ? <p className="text-destructive text-sm">{retry.error.message}</p> : null}

      {job.status === "ready_for_review" ? <JobReview job={job} /> : null}
    </div>
  );
}
