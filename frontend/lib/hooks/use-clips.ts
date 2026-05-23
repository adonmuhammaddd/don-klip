"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listClips, updateClip } from "@/lib/api/client";
import type { ClipUpdate } from "@/lib/api/types";

export function useClips(jobId: string) {
  return useQuery({ queryKey: ["clips", jobId], queryFn: () => listClips(jobId) });
}

export function useUpdateClip(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; payload: ClipUpdate }) => updateClip(vars.id, vars.payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clips", jobId] }),
  });
}
