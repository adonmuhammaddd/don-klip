// Mirror dari Pydantic DTO backend. Bisa di-generate via openapi-typescript nanti.

export type SourceType = "upload" | "url";

export type JobStatus =
  | "pending"
  | "downloading"
  | "transcribing"
  | "detecting"
  | "ready_for_review"
  | "exporting"
  | "completed"
  | "failed"
  | "cancelled";

export type DetectionStrategyName = "audio_spike" | "llm_transcript" | "twitch_chat" | "manual";

export interface StrategyConfig {
  strategy: DetectionStrategyName;
  std_multiplier?: number;
  markers?: string[];
}

export interface DetectionConfig {
  strategies: StrategyConfig[];
}

export interface JobRead {
  id: string;
  source_type: SourceType;
  source_url: string | null;
  original_filename: string;
  duration_seconds: number | null;
  status: JobStatus;
  progress_pct: number;
  progress_message: string;
  detection_config: DetectionConfig;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobListItem {
  id: string;
  source_type: SourceType;
  original_filename: string;
  status: JobStatus;
  progress_pct: number;
  created_at: string;
}

export interface JobListResponse {
  items: JobListItem[];
  total: number;
  page: number;
  page_size: number;
}

export type ClipStatus =
  | "pending"
  | "selected"
  | "rejected"
  | "exporting"
  | "exported"
  | "failed";

export interface ClipRead {
  id: string;
  job_id: string;
  start_seconds: number;
  end_seconds: number;
  user_start_seconds: number | null;
  user_end_seconds: number | null;
  detection_strategy: DetectionStrategyName;
  score: number;
  reason: string;
  transcript_excerpt: string | null;
  status: ClipStatus;
  exported_paths: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ClipUpdate {
  user_start_seconds?: number;
  user_end_seconds?: number;
  status?: ClipStatus;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  confidence: number | null;
}

export interface TranscriptRead {
  job_id: string;
  language: string;
  segments: TranscriptSegment[];
}
