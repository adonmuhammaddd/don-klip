import { create } from "zustand";

interface ClipEditorState {
  activeClipId: string | null;
  setActiveClip: (id: string | null) => void;
}

export const useClipEditor = create<ClipEditorState>((set) => ({
  activeClipId: null,
  setActiveClip: (id) => set({ activeClipId: id }),
}));
