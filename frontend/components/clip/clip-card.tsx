"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ClipRead } from "@/lib/api/types";
import { formatTime, strategyLabel } from "@/lib/format";

export function ClipCard({ clip }: { clip: ClipRead }) {
  const start = clip.user_start_seconds ?? clip.start_seconds;
  const end = clip.user_end_seconds ?? clip.end_seconds;

  return (
    <Card>
      <CardContent className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="secondary">{strategyLabel(clip.detection_strategy)}</Badge>
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
