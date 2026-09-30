import { describe, expect, it } from "vitest";
import type { ResumeResult } from "@/lib/api/types";
import { fingerprint, fromDraft, toDraft } from "./draft";

const result: ResumeResult = {
  schema: 1,
  contact: { first_name: "Jordan", last_name: "Rivera", email: "j@example.com", phone: "", location: "", linkedin: "" },
  summary: "Analytics leader.",
  education: [],
  experience: [{ company: "Northwind", location: "", dates: "2019 - Present", title: "Director", bullets: [{ text: "Did X.", ids: ["F001"] }] }],
  skills: ["Python"],
  cover_letter: null,
};

describe("draft model", () => {
  it("adds client keys and strips them again", () => {
    const draft = toDraft(result);
    expect(draft.experience[0].bullets[0]._key).toBeTruthy();
    expect(fromDraft(draft)).toEqual(result);
  });

  it("fingerprints ignore client keys", () => {
    expect(fingerprint(toDraft(result))).toBe(fingerprint(toDraft(result)));
  });
});
