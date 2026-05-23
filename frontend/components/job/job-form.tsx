"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DetectionConfig } from "@/lib/api/types";
import { useCreateUploadJob, useCreateUrlJob } from "@/lib/hooks/use-jobs";

type Mode = "upload" | "url";

export function JobForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("upload");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [std, setStd] = useState(2.0);

  const createUrl = useCreateUrlJob();
  const createUpload = useCreateUploadJob();
  const pending = createUrl.isPending || createUpload.isPending;
  const error = createUrl.error ?? createUpload.error;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const config: DetectionConfig = {
      strategies: [{ strategy: "audio_spike", std_multiplier: std }],
    };
    const job =
      mode === "url"
        ? await createUrl.mutateAsync({ url, config })
        : file
          ? await createUpload.mutateAsync({ file, config })
          : null;
    if (job) {
      router.push(`/jobs/${job.id}`);
    }
  }

  const canSubmit = mode === "url" ? url.trim().length > 0 : file !== null;

  return (
    <form onSubmit={handleSubmit} className="max-w-xl space-y-6">
      <div className="flex gap-2">
        <Button
          type="button"
          variant={mode === "upload" ? "default" : "outline"}
          onClick={() => setMode("upload")}
        >
          Upload File
        </Button>
        <Button
          type="button"
          variant={mode === "url" ? "default" : "outline"}
          onClick={() => setMode("url")}
        >
          Dari URL
        </Button>
      </div>

      {mode === "upload" ? (
        <div className="space-y-2">
          <Label htmlFor="file">File video (mp4, mkv, mov, webm)</Label>
          <Input
            id="file"
            type="file"
            accept=".mp4,.mkv,.mov,.webm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor="url">URL YouTube / Twitch VOD</Label>
          <Input
            id="url"
            type="url"
            placeholder="https://..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="std">Audio spike sensitivity (σ multiplier)</Label>
        <Input
          id="std"
          type="number"
          step="0.1"
          min="0.5"
          value={std}
          onChange={(e) => setStd(Number(e.target.value))}
        />
        <p className="text-muted-foreground text-xs">
          Makin kecil makin sensitif (default 2.0). Detector lain menyusul di Sprint 4.
        </p>
      </div>

      {error ? <p className="text-destructive text-sm">{error.message}</p> : null}

      <Button type="submit" disabled={!canSubmit || pending}>
        {pending ? "Memproses..." : "Buat Job"}
      </Button>
    </form>
  );
}
