/**
 * An instant HTML approximation of the three .docx templates, so edits show
 * up while you type. The exact output is always the rendered PDF; this only
 * mirrors its fonts, spacing, and structure closely enough to judge flow.
 */
import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { TemplateKey } from "@/lib/types";
import type { Draft } from "./draft";

const PAGE_W = 816; // 8.5in at 96dpi
const PAGE_H = 1056;

interface Look {
  font: string;
  body: number;
  name: number;
  contact: number;
  section: number;
  entry: number;
  ink: string;
  accent: string;
  muted: string;
  rule: string | null;
  marginTB: number;
  marginLR: number;
  nameAlign: "center" | "left";
  nameSmallCaps: boolean;
  sectionCase: "upper" | "none" | "smallcaps";
  titleFirst: boolean;
  skillsSep: string;
  gap: number;
}

// Values mirror TEMPLATES in generate_resume.py (pt -> px at 96dpi = x1.333).
const LOOKS: Record<TemplateKey, Look> = {
  classic: {
    font: "Calibri, Carlito, 'Segoe UI', sans-serif", body: 10.5, name: 22, contact: 9.5, section: 11.5, entry: 10,
    ink: "#1F2A44", accent: "#1F2A44", muted: "#444444", rule: "#1F2A44", marginTB: 0.55, marginLR: 0.75,
    nameAlign: "center", nameSmallCaps: false, sectionCase: "upper", titleFirst: false, skillsSep: ", ", gap: 1,
  },
  modern: {
    font: "Arial, Helvetica, sans-serif", body: 10, name: 24, contact: 9, section: 11, entry: 10,
    ink: "#0F5E63", accent: "#0F5E63", muted: "#555B66", rule: "#C9D3D6", marginTB: 0.6, marginLR: 0.7,
    nameAlign: "left", nameSmallCaps: false, sectionCase: "none", titleFirst: true, skillsSep: " | ", gap: 0.95,
  },
  compact: {
    font: "Cambria, Georgia, 'Times New Roman', serif", body: 10, name: 18, contact: 9, section: 10.5, entry: 9.5,
    ink: "#1A1A1A", accent: "#1A1A1A", muted: "#4A4A4A", rule: "#1A1A1A", marginTB: 0.5, marginLR: 0.6,
    nameAlign: "center", nameSmallCaps: true, sectionCase: "smallcaps", titleFirst: false, skillsSep: " | ", gap: 0.6,
  },
};

const pt = (n: number) => `${(n * 4) / 3}px`;

export function ResumePaper({ draft, template }: { draft: Draft; template: TemplateKey }) {
  const L = LOOKS[template] ?? LOOKS.classic;
  const wrap = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.7);
  const [height, setHeight] = useState(PAGE_H);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setScale(Math.min(1.25, e.contentRect.width / PAGE_W)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Track the content's natural (unscaled) height so the scaled box fits it.
  useEffect(() => {
    const el = inner.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setHeight(Math.max(PAGE_H, el.scrollHeight)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const c = draft.contact;
  const contact = [c.email, c.phone, c.location, c.linkedin].filter(Boolean).join("  |  ");
  const sectionStyle: CSSProperties = {
    color: L.ink,
    fontSize: pt(L.section),
    fontWeight: 700,
    textTransform: L.sectionCase === "upper" ? "uppercase" : "none",
    fontVariant: L.sectionCase === "smallcaps" ? "small-caps" : "normal",
    borderBottom: L.rule ? `${template === "classic" ? 1 : 0.75}px solid ${L.rule}` : "none",
    paddingBottom: 2,
    marginTop: pt(12 * L.gap),
    marginBottom: pt(4 * L.gap),
  };
  const row: CSSProperties = { display: "flex", justifyContent: "space-between", gap: 12, fontWeight: 700 };
  const pages = Math.ceil(height / PAGE_H);

  return (
    <div ref={wrap} className="w-full">
      <div style={{ height: height * scale, width: PAGE_W * scale }} className="relative mx-auto">
        <div
          ref={inner}
          style={{
            transform: `scale(${scale})`,
            transformOrigin: "top left",
            width: PAGE_W,
            minHeight: PAGE_H,
            padding: `${L.marginTB * 96}px ${L.marginLR * 96}px`,
            fontFamily: L.font,
            fontSize: pt(L.body),
            lineHeight: 1.18,
            color: "#000",
            background: "#fff",
            backgroundImage:
              pages > 1
                ? `repeating-linear-gradient(to bottom, transparent 0, transparent ${PAGE_H - 1}px, #e4e4e7 ${PAGE_H - 1}px, #e4e4e7 ${PAGE_H}px)`
                : undefined,
          }}
          className="absolute left-0 top-0 rounded-sm shadow-paper"
        >
          <div
            style={{
              textAlign: L.nameAlign,
              fontSize: pt(L.name),
              fontWeight: 700,
              color: L.ink,
              fontVariant: L.nameSmallCaps ? "small-caps" : "normal",
              lineHeight: 1.1,
            }}
          >
            {c.first_name} {c.last_name}
          </div>
          <div style={{ textAlign: L.nameAlign, fontSize: pt(L.contact), color: L.muted, marginTop: 3, marginBottom: pt(10 * L.gap) }}>
            {contact}
          </div>

          <div style={sectionStyle}>Summary</div>
          <p style={{ margin: 0 }}>{draft.summary}</p>

          {!!draft.education?.length && (
            <>
              <div style={sectionStyle}>Education</div>
              {draft.education.map((e, i) => (
                <div key={i} style={{ marginBottom: pt(6 * L.gap) }}>
                  <div style={row}>
                    <span>{[e.institution, e.location].filter(Boolean).join(" | ")}</span>
                    <span style={{ fontWeight: 400, color: L.muted }}>{e.dates}</span>
                  </div>
                  <div>{e.degree}</div>
                </div>
              ))}
            </>
          )}

          <div style={sectionStyle}>Experience</div>
          {draft.experience.map((job, i) => {
            const place = [job.company, job.location].filter(Boolean).join(" | ");
            return (
              <div key={i} style={{ marginBottom: pt(8 * L.gap) }}>
                <div style={row}>
                  <span>{L.titleFirst ? job.title : place}</span>
                  <span style={{ fontWeight: 400, color: L.muted }}>{job.dates}</span>
                </div>
                {L.titleFirst ? (
                  <div style={{ color: L.accent, fontWeight: 700, fontSize: pt(L.entry), marginBottom: 3 }}>{place}</div>
                ) : (
                  <div style={{ fontStyle: "italic", color: L.muted, fontSize: pt(L.entry), marginBottom: 3 }}>{job.title}</div>
                )}
                <ul style={{ margin: 0, paddingLeft: template === "compact" ? 17 : 19, listStyle: "disc" }}>
                  {job.bullets.map((b) => (
                    <li key={b._key} style={{ marginBottom: pt(template === "compact" ? 1.5 : 3), paddingLeft: 2 }}>
                      {b.text}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}

          {!!draft.skills?.length && (
            <>
              <div style={sectionStyle}>Skills</div>
              <p style={{ margin: 0 }}>{draft.skills.join(L.skillsSep)}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
