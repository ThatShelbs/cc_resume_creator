import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Download, FileUp, Save, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Callout, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/primitives";
import { api, withToken } from "@/lib/api";
import { keys, useProfile } from "@/lib/queries";
import type { Profile, ProfilePayload } from "@/lib/types";
import { relativeTime, uid } from "@/lib/utils";
import { ProfileEditor } from "./ProfileEditor";

/** Drop blank items so they don't count as unsaved changes or get written. */
export function cleanProfile(p: Profile): Profile {
  return { ...p, sections: p.sections.map((s) => ({ ...s, items: s.items.filter((i) => i.trim()) })) };
}

export default function ProfilePage() {
  const { data, isLoading } = useProfile();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Profile | null>(null);
  const baseline = useRef("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!data) return;
    const p = data.profile.sections.length ? data.profile : { ...data.profile, sections: [{ id: uid(), title: "Skills", items: [""] }] };
    baseline.current = JSON.stringify(cleanProfile(p));
    setDraft(p);
  }, [data]);

  const dirty = !!draft && JSON.stringify(cleanProfile(draft)) !== baseline.current;

  const save = useMutation({
    mutationFn: (p: Profile) => api.put<ProfilePayload>("/api/profile", cleanProfile(p)),
    onSuccess: (res) => {
      qc.setQueryData(keys.profile, res);
      qc.invalidateQueries({ queryKey: keys.system });
      qc.invalidateQueries({ queryKey: keys.projects });
      toast.success("Profile saved", { description: res.backup ? `Previous version backed up as ${res.backup}` : undefined });
    },
    onError: (e) => toast.error("Couldn't save", { description: (e as Error).message }),
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "s" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (draft && dirty) save.mutate(draft);
      }
    };
    const onUnload = (e: BeforeUnloadEvent) => dirty && e.preventDefault();
    window.addEventListener("keydown", onKey);
    window.addEventListener("beforeunload", onUnload);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("beforeunload", onUnload);
    };
  }, [draft, dirty, save]);

  const importDocx = async (file: File) => {
    try {
      const r = await api.upload<{ profile: Profile }>("/api/profile/import", file);
      setDraft(r.profile);
      toast.success("Imported. Review it, then save.");
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 pb-28 sm:px-6">
      <PageHeader
        title="Profile"
        description="Everything true about your career that the tailoring may draw from: accomplishments, projects, tools, skills. Nothing outside your profile and base resume can appear in a resume."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => fileInput.current?.click()}>
              <FileUp /> Import .docx
            </Button>
            <input ref={fileInput} type="file" accept=".docx" className="hidden" onChange={(e) => e.target.files?.[0] && importDocx(e.target.files[0])} />
            {data?.exists && (
              <Button asChild variant="outline" size="sm">
                <a href={withToken("/api/profile/download")} download>
                  <Download /> Export .docx
                </a>
              </Button>
            )}
          </>
        }
      />
      {data?.exists ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Saved as <code className="rounded bg-muted px-1">resume_input/{data.file}</code>
          {data.updated && `, updated ${relativeTime(data.updated)}`}. Every save keeps a backup in resume_archive/.
        </p>
      ) : (
        !isLoading && (
          <Callout className="mt-5" title="No profile yet">
            Start with your contact details and the skills and tools you use. Add accomplishments with real numbers under sections like
            Projects or Leadership.
          </Callout>
        )
      )}

      <div className="mt-6">
        {isLoading || !draft ? (
          <div className="grid gap-4">
            <Skeleton className="h-56" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
          </div>
        ) : (
          <ProfileEditor value={draft} onChange={setDraft} />
        )}
      </div>

      <AnimatePresence>
        {dirty && (
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            transition={{ type: "spring", stiffness: 420, damping: 36 }}
            className="fixed inset-x-0 bottom-5 z-30 mx-auto flex w-[calc(100%-2rem)] max-w-xl items-center gap-3 rounded-xl border bg-popover px-4 py-3 shadow-lift"
          >
            <UserRound className="size-4 text-primary" />
            <span className="flex-1 text-sm font-medium">Unsaved profile changes</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => data && setDraft(data.profile)}
            >
              Discard
            </Button>
            <Button size="sm" loading={save.isPending} onClick={() => draft && save.mutate(draft)}>
              <Save /> Save
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
