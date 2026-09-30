import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { SortableItems } from "./SortableItems";

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
