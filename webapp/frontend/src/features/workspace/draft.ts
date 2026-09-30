/**
 * The editable copy of a project's result. Bullets get a client-only `_key`
 * so drag-and-drop and React lists stay stable while text changes; keys are
 * stripped before anything is sent to the server.
 */
import type { Bullet, ExperienceEntry, ResumeResult } from "@/lib/types";
import { uid } from "@/lib/utils";

export type EditableBullet = Bullet & { _key: string };
export type EditableEntry = Omit<ExperienceEntry, "bullets"> & { bullets: EditableBullet[] };
export type Draft = Omit<ResumeResult, "experience"> & { experience: EditableEntry[] };

export function toDraft(result: ResumeResult): Draft {
  return {
    ...result,
    experience: result.experience.map((e) => ({
      ...e,
      bullets: e.bullets.map((b) => ({ ...b, ids: b.ids ?? [], _key: uid() })),
    })),
  };
}

export function fromDraft(draft: Draft): ResumeResult {
  return {
    ...draft,
    experience: draft.experience.map((e) => ({
      ...e,
      bullets: e.bullets.map(({ _key: _ignored, ...b }) => b),
    })),
  };
}

export function newBullet(): EditableBullet {
  return { text: "", ids: [], _key: uid() };
}

/** Serialized form used to detect real changes (ignores client keys). */
export function fingerprint(draft: Draft | null): string {
  return draft ? JSON.stringify(fromDraft(draft)) : "";
}
