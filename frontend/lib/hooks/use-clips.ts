"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { exportClip, listClips, updateClip } from "@/lib/api/client";
import type { ClipUpdate } from "@/lib/api/types";

export function useClips(jobId: string) {
  return useQuery({
    queryKey: ["clips", jobId],
    queryFn: () => listClips(jobId),
    // Polling saat ada klip yang sedang di-export.
    refetchInterval: (query) =>
      query.state.data?.some((clip) => clip.status === "exporting") ? 2000 : false,
  });
}

export function useUpdateClip(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; payload: ClipUpdate }) => updateClip(vars.id, vars.payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clips", jobId] }),
  });
}

export function useExportClip(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => exportClip(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clips", jobId] }),
  });
}
