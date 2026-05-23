"use client";

import { ClipCard } from "@/components/clip/clip-card";
import { useClips } from "@/lib/hooks/use-clips";

export function ClipList({ jobId }: { jobId: string }) {
  const { data: clips, isLoading, error } = useClips(jobId);

  if (isLoading) {
    return <p className="text-muted-foreground">Memuat klip...</p>;
  }
  if (error) {
    return <p className="text-destructive">Gagal memuat klip: {error.message}</p>;
  }
  if (!clips || clips.length === 0) {
    return <p className="text-muted-foreground">Tidak ada kandidat klip terdeteksi.</p>;
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">{clips.length} kandidat klip</h2>
      {clips.map((clip) => (
        <ClipCard key={clip.id} clip={clip} />
      ))}
    </div>
  );
}
