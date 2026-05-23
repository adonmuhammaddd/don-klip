"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { sourcePreviewUrl } from "@/lib/api/client";
import type { ClipRead } from "@/lib/api/types";
import { formatTime } from "@/lib/format";
import { useUpdateClip } from "@/lib/hooks/use-clips";

const PAD = 10; // window ±10 detik dari kandidat (§10)

export function ClipTrimEditor({
  clip,
  duration,
  jobId,
}: {
  clip: ClipRead;
  duration: number;
  jobId: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const update = useUpdateClip(jobId);

  const rangeMin = Math.max(0, clip.start_seconds - PAD);
  const rangeMax = Math.min(duration || clip.end_seconds + PAD, clip.end_seconds + PAD);

  const [start, setStart] = useState(clip.user_start_seconds ?? clip.start_seconds);
  const [end, setEnd] = useState(clip.user_end_seconds ?? clip.end_seconds);

  // Reset & seek saat klip aktif berganti.
  useEffect(() => {
    const s = clip.user_start_seconds ?? clip.start_seconds;
    const e = clip.user_end_seconds ?? clip.end_seconds;
    setStart(s);
    setEnd(e);
    if (videoRef.current) {
      videoRef.current.currentTime = s;
    }
  }, [clip]);

  function handleChange(values: number[]) {
    const [s, e] = values;
    if (videoRef.current) {
      // Seek ke handle yang bergeser → live preview.
      videoRef.current.currentTime = s !== start ? s : e;
    }
    setStart(s);
    setEnd(e);
  }

  return (
    <div className="space-y-3">
      <video
        ref={videoRef}
        src={sourcePreviewUrl(clip.id)}
        controls
        className="aspect-video w-full rounded-lg bg-black"
      />
      <Slider
        min={rangeMin}
        max={rangeMax}
        step={0.5}
        value={[start, end]}
        onValueChange={handleChange}
      />
      <div className="text-muted-foreground flex justify-between text-xs tabular-nums">
        <span>mulai {formatTime(start)}</span>
        <span>durasi {formatTime(end - start)}</span>
        <span>akhir {formatTime(end)}</span>
      </div>

      {update.error ? <p className="text-destructive text-sm">{update.error.message}</p> : null}

      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          disabled={update.isPending}
          onClick={() =>
            update.mutate({ id: clip.id, payload: { user_start_seconds: start, user_end_seconds: end } })
          }
        >
          Simpan trim
        </Button>
        <Button
          disabled={update.isPending}
          onClick={() =>
            update.mutate({
              id: clip.id,
              payload: { user_start_seconds: start, user_end_seconds: end, status: "selected" },
            })
          }
        >
          Approve
        </Button>
        <Button
          variant="ghost"
          disabled={update.isPending}
          onClick={() => update.mutate({ id: clip.id, payload: { status: "rejected" } })}
        >
          Reject
        </Button>
      </div>
    </div>
  );
}
