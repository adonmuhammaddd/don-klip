import type { DetectionStrategyName } from "@/lib/api/types";

export function formatTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

const STRATEGY_LABELS: Record<DetectionStrategyName, string> = {
  audio_spike: "Audio spike",
  llm_transcript: "LLM",
  twitch_chat: "Twitch chat",
  manual: "Manual",
};

export function strategyLabel(strategy: DetectionStrategyName): string {
  return STRATEGY_LABELS[strategy];
}
