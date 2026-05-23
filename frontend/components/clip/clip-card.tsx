"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ClipRead } from "@/lib/api/types";
import { formatTime, strategyLabel } from "@/lib/format";
import { useClipEditor } from "@/lib/store/clip-editor";
import { cn } from "@/lib/utils";

export function ClipCard({ clip }: { clip: ClipRead }) {
  const { activeClipId, setActiveClip } = useClipEditor();
  const active = activeClipId === clip.id;
  const start = clip.user_start_seconds ?? clip.start_seconds;
  const end = clip.user_end_seconds ?? clip.end_seconds;

  return (
    <Card
      onClick={() => setActiveClip(clip.id)}
      className={cn("cursor-pointer transition-colors", active && "ring-primary ring-2")}
    >
      <CardContent className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{strategyLabel(clip.detection_strategy)}</Badge>
            {clip.status === "selected" ? <Badge>Approved</Badge> : null}
            {clip.status === "rejected" ? <Badge variant="outline">Rejected</Badge> : null}
            {clip.status === "exported" ? <Badge>Exported</Badge> : null}
          </div>
          <span className="text-muted-foreground text-xs tabular-nums">
            {Math.round(clip.score * 100)}% · {formatTime(start)}–{formatTime(end)}
          </span>
        </div>
        <p className="text-sm">{clip.reason}</p>
        {clip.transcript_excerpt ? (
          <p className="text-muted-foreground line-clamp-3 text-xs italic">
            &ldquo;{clip.transcript_excerpt}&rdquo;
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
