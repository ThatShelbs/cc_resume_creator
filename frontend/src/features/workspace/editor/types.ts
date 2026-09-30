import { type Draft } from "@/features/workspace/draft";

export type Update = (fn: (d: Draft) => Draft) => void;
