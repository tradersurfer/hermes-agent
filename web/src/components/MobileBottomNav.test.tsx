// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MobileBottomNav, { MOBILE_BOTTOM_NAV_TABS } from "./MobileBottomNav";

const apiMocks = vi.hoisted(() => ({
  getSessionStats: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: { getSessionStats: apiMocks.getSessionStats },
}));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

function renderAt(path: string) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(
      createElement(
        MemoryRouter,
        { initialEntries: [path] },
        createElement(MobileBottomNav),
      ),
    );
  });
}

beforeEach(() => {
  apiMocks.getSessionStats.mockResolvedValue({
    total: 20,
    active_store: 14,
  });
});

afterEach(async () => {
  if (root) {
    await act(async () => {
      root!.unmount();
    });
    root = null;
  }
  container?.remove();
  container = null;
  vi.clearAllMocks();
});

describe("MobileBottomNav", () => {
  it("renders exactly the five requested tabs, in order", () => {
    renderAt("/sessions");
    const labels = MOBILE_BOTTOM_NAV_TABS.map((tab) => tab.label);
    expect(labels).toEqual([
      "Agents",
      "Sessions",
      "Bots Mode",
      "Automations",
      "Beta",
    ]);
    for (const label of labels) {
      expect(container!.querySelector(`[aria-label="${label}"]`)).not.toBeNull();
    }
  });

  it("marks the current route's tab active and the others not", () => {
    renderAt("/cron");
    const automations = container!.querySelector('[aria-label="Automations"]');
    const sessions = container!.querySelector('[aria-label="Sessions"]');
    expect(automations?.getAttribute("aria-current")).toBe("page");
    expect(sessions?.getAttribute("aria-current")).toBeNull();
  });

  it("shows the active session count as a badge, not a hard-coded value", async () => {
    apiMocks.getSessionStats.mockResolvedValue({
      total: 20,
      active_store: 7,
    });
    renderAt("/sessions");
    await act(async () => {
      await Promise.resolve();
    });
    const badge = container!.querySelector(
      '[aria-label="7 active sessions"]',
    );
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toBe("7");
  });

  it("caps a large badge at 99+ while keeping the exact count in its label", async () => {
    apiMocks.getSessionStats.mockResolvedValue({
      total: 150,
      active_store: 150,
    });
    renderAt("/sessions");
    await act(async () => {
      await Promise.resolve();
    });
    const badge = container!.querySelector(
      '[aria-label="150 active sessions"]',
    );
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toBe("99+");
  });

  it("renders no badge when the stats call fails", async () => {
    apiMocks.getSessionStats.mockRejectedValue(new Error("offline"));
    renderAt("/sessions");
    await act(async () => {
      await Promise.resolve();
    });
    const badges = [...container!.querySelectorAll("[aria-label]")].filter(
      (el) =>
        /^\d+ active sessions$/.test(el.getAttribute("aria-label") ?? ""),
    );
    expect(badges).toHaveLength(0);
  });
});
