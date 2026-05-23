"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useDeleteJob, useJobs } from "@/lib/hooks/use-jobs";
import { statusLabel, statusVariant } from "@/lib/status";

export function JobList() {
  const { data, isLoading, error } = useJobs();
  const remove = useDeleteJob();

  if (isLoading) {
    return <p className="text-muted-foreground">Memuat job...</p>;
  }
  if (error) {
    return <p className="text-destructive">Gagal memuat: {error.message}</p>;
  }
  if (!data || data.items.length === 0) {
    return <p className="text-muted-foreground">Belum ada job. Buat job baru untuk mulai.</p>;
  }

  return (
    <div className="space-y-3">
      {data.items.map((job) => (
        <Card key={job.id}>
          <CardContent className="flex items-center justify-between gap-4">
            <Link href={`/jobs/${job.id}`} className="min-w-0 flex-1">
              <p className="truncate font-medium">{job.original_filename}</p>
              <p className="text-muted-foreground text-xs">
                {new Date(job.created_at).toLocaleString()} · {job.source_type}
              </p>
            </Link>
            <Badge variant={statusVariant(job.status)}>{statusLabel(job.status)}</Badge>
            <span className="text-muted-foreground w-12 text-right text-sm tabular-nums">
              {job.progress_pct}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={remove.isPending}
              onClick={() => remove.mutate(job.id)}
            >
              Hapus
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
