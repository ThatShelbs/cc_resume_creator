import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { SortableItems } from "@/components/SortableItems";
import { fingerprint, fromDraft, toDraft } from "@/features/workspace/draft";
import { TemplatePicker } from "@/features/projects/TemplatePicker";
import type { ResumeResult } from "@/lib/types";

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

describe("TemplatePicker", () => {
  it("shows three templates and reports the choice", async () => {
    const onChange = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TemplatePicker value="classic" onChange={onChange} />
      </QueryClientProvider>,
    );
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByText("Modern"));
    expect(onChange).toHaveBeenCalledWith("modern");
  });
});

function ListHarness({ initial }: { initial: string[] }) {
  const [items, setItems] = useState(initial);
  return (
    <>
      <SortableItems items={items} onChange={setItems} />
      <output data-testid="items">{JSON.stringify(items)}</output>
    </>
  );
}

describe("SortableItems", () => {
  it("Enter adds an item below; Backspace on an empty item removes it", async () => {
    render(<ListHarness initial={["Python", "SQL"]} />);
    const first = screen.getAllByRole("textbox")[0];
    fireEvent.keyDown(first, { key: "Enter" });
    expect(screen.getByTestId("items")).toHaveTextContent('["Python","","SQL"]');
    const blank = screen.getAllByRole("textbox")[1];
    fireEvent.keyDown(blank, { key: "Backspace" });
    expect(screen.getByTestId("items")).toHaveTextContent('["Python","SQL"]');
  });

  it("edits and removes items", async () => {
    render(<ListHarness initial={["Python"]} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Python 3\nnewline" } });
    expect(screen.getByTestId("items")).toHaveTextContent('["Python 3 newline"]');
    await userEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.getByTestId("items")).toHaveTextContent("[]");
  });
});
