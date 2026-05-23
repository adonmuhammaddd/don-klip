"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { DetectionConfig, StrategyConfig } from "@/lib/api/types";
import { useCreateUploadJob, useCreateUrlJob } from "@/lib/hooks/use-jobs";

type Mode = "upload" | "url";

export function JobForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("upload");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [audioSpike, setAudioSpike] = useState(true);
  const [std, setStd] = useState(2.0);
  const [llm, setLlm] = useState(false);
  const [twitchChat, setTwitchChat] = useState(false);
  const [manual, setManual] = useState(false);
  const [markers, setMarkers] = useState("");

  const createUrl = useCreateUrlJob();
  const createUpload = useCreateUploadJob();
  const pending = createUrl.isPending || createUpload.isPending;
  const error = createUrl.error ?? createUpload.error;

  const isTwitchUrl = mode === "url" && /twitch\.tv/i.test(url);
  const twitchEnabled = twitchChat && isTwitchUrl;

  function buildStrategies(): StrategyConfig[] {
    const strategies: StrategyConfig[] = [];
    if (audioSpike) strategies.push({ strategy: "audio_spike", std_multiplier: std });
    if (llm) strategies.push({ strategy: "llm_transcript" });
    if (twitchEnabled) strategies.push({ strategy: "twitch_chat" });
    if (manual) {
      const list = markers
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      strategies.push({ strategy: "manual", markers: list });
    }
    return strategies;
  }

  const strategies = buildStrategies();
  const sourceReady = mode === "url" ? url.trim().length > 0 : file !== null;
  const canSubmit = sourceReady && strategies.length > 0;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const config: DetectionConfig = { strategies };
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

      <div className="space-y-3">
        <p className="text-sm font-medium">Strategi deteksi</p>

        <StrategyRow
          id="audio"
          checked={audioSpike}
          onChange={setAudioSpike}
          label="Audio spike"
          hint="Deteksi lonjakan energi audio (momen rame)."
        >
          <div className="flex items-center gap-2">
            <Label htmlFor="std" className="text-xs">
              Sensitivity (σ)
            </Label>
            <Input
              id="std"
              type="number"
              step="0.1"
              min="0.5"
              value={std}
              onChange={(e) => setStd(Number(e.target.value))}
              className="h-8 w-24"
            />
          </div>
        </StrategyRow>

        <StrategyRow
          id="llm"
          checked={llm}
          onChange={setLlm}
          label="LLM transcript"
          hint="Cari quote/punchline menarik dari transcript pakai LLM."
        />

        <StrategyRow
          id="twitch"
          checked={twitchChat}
          onChange={setTwitchChat}
          label="Twitch chat density"
          hint={
            isTwitchUrl
              ? "Deteksi spike kepadatan chat Twitch."
              : "Hanya untuk URL Twitch VOD."
          }
          disabled={!isTwitchUrl}
        />

        <StrategyRow
          id="manual"
          checked={manual}
          onChange={setManual}
          label="Manual marker"
          hint="Tandai timestamp sendiri, satu per baris."
        >
          <Textarea
            value={markers}
            onChange={(e) => setMarkers(e.target.value)}
            placeholder={"00:01:30, epic play\n00:12:05, quote bagus"}
            rows={4}
          />
        </StrategyRow>
      </div>

      {strategies.length === 0 ? (
        <p className="text-muted-foreground text-xs">Pilih minimal satu strategi deteksi.</p>
      ) : null}
      {error ? <p className="text-destructive text-sm">{error.message}</p> : null}

      <Button type="submit" disabled={!canSubmit || pending}>
        {pending ? "Memproses..." : "Buat Job"}
      </Button>
    </form>
  );
}

function StrategyRow({
  id,
  checked,
  onChange,
  label,
  hint,
  disabled = false,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  hint: string;
  disabled?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <Checkbox
          id={id}
          checked={checked}
          disabled={disabled}
          onCheckedChange={(value) => onChange(value === true)}
          className="mt-0.5"
        />
        <div className="space-y-0.5">
          <Label htmlFor={id} className={disabled ? "opacity-50" : ""}>
            {label}
          </Label>
          <p className="text-muted-foreground text-xs">{hint}</p>
        </div>
      </div>
      {checked && !disabled && children ? <div className="mt-3 pl-7">{children}</div> : null}
    </div>
  );
}
