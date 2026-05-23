"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelJob,
  createUploadJob,
  createUrlJob,
  deleteJob,
  getJob,
  listJobs,
  retryJob,
} from "@/lib/api/client";
import type { DetectionConfig } from "@/lib/api/types";
import { TERMINAL_STATUSES } from "@/lib/status";

export function useJobs() {
  return useQuery({ queryKey: ["jobs"], queryFn: () => listJobs() });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ["job", id],
    queryFn: () => getJob(id),
    // Polling 2 detik sampai status terminal (§4).
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL_STATUSES.includes(status) ? false : 2000;
    },
  });
}

export function useCreateUrlJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { url: string; config: DetectionConfig }) =>
      createUrlJob(vars.url, vars.config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useCreateUploadJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { file: File; config: DetectionConfig }) =>
      createUploadJob(vars.file, vars.config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useCancelJob(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => cancelJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["job", jobId] }),
  });
}

export function useRetryJob(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => retryJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["job", jobId] }),
  });
}
