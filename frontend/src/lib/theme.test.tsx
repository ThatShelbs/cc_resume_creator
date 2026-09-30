import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { THEME_STORAGE_KEY, ThemeProvider, useTheme } from "@/lib/theme";

let systemDark = false;
const listeners = new Set<() => void>();

beforeEach(() => {
  localStorage.clear();
  document.documentElement.className = "";
  systemDark = false;
  listeners.clear();
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      get matches() {
        return systemDark;
      },
      addEventListener: (_: string, cb: () => void) => listeners.add(cb),
      removeEventListener: (_: string, cb: () => void) => listeners.delete(cb),
    })),
  );
});

function Probe() {
  const { theme, resolved, setTheme, toggle } = useTheme();
  return (
    <div>
      <span data-testid="state">
        {theme}/{resolved}
      </span>
      <button onClick={() => setTheme("dark")}>night</button>
      <button onClick={() => setTheme("system")}>system</button>
      <button onClick={toggle}>toggle</button>
    </div>
  );
}

describe("ThemeProvider", () => {
  it("defaults to the system theme", () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("system/light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("applies and persists an explicit choice", async () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByText("night"));
    expect(screen.getByTestId("state")).toHaveTextContent("dark/dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    await userEvent.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state")).toHaveTextContent("light/light");
  });

  it("restores the saved preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("dark/dark");
  });

  it("follows the operating system live while on system", () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    act(() => {
      systemDark = true;
      listeners.forEach((cb) => cb());
    });
    expect(screen.getByTestId("state")).toHaveTextContent("system/dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
