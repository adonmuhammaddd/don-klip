import type { JobStatus } from "@/lib/api/types";

export const TERMINAL_STATUSES: JobStatus[] = [
  "ready_for_review",
  "completed",
  "failed",
  "cancelled",
];

export const IN_PROGRESS_STATUSES: JobStatus[] = [
  "pending",
  "downloading",
  "transcribing",
  "detecting",
];

const LABELS: Record<JobStatus, string> = {
  pending: "Menunggu",
  downloading: "Mengunduh",
  transcribing: "Transcribing",
  detecting: "Mendeteksi",
  ready_for_review: "Siap direview",
  exporting: "Mengekspor",
  completed: "Selesai",
  failed: "Gagal",
  cancelled: "Dibatalkan",
};

export function statusLabel(status: JobStatus): string {
  return LABELS[status];
}

export function statusVariant(
  status: JobStatus,
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "failed") return "destructive";
  if (status === "ready_for_review" || status === "completed") return "default";
  if (status === "cancelled") return "outline";
  return "secondary";
}
