import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TemplatePicker } from "./TemplatePicker";

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
