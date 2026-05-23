"use client";

import { ClipList } from "@/components/clip/clip-list";
import { ClipTrimEditor } from "@/components/clip/clip-trim-editor";
import type { JobRead } from "@/lib/api/types";
import { useClips } from "@/lib/hooks/use-clips";
import { useClipEditor } from "@/lib/store/clip-editor";

export function JobReview({ job }: { job: JobRead }) {
  const { activeClipId } = useClipEditor();
  const { data: clips } = useClips(job.id);
  const active = clips?.find((clip) => clip.id === activeClipId) ?? null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="lg:sticky lg:top-6 lg:h-fit">
        {active ? (
          <ClipTrimEditor clip={active} duration={job.duration_seconds ?? 0} jobId={job.id} />
        ) : (
          <p className="text-muted-foreground">Pilih klip di kanan untuk preview &amp; trim.</p>
        )}
      </div>
      <ClipList jobId={job.id} />
    </div>
  );
}
