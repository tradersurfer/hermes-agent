import { useEffect, useState, type ComponentType } from "react";
import { NavLink } from "react-router";
import { Bot, Clock, MessageSquare, Sparkles, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

/**
 * Mobile bottom navigation for the web dashboard.
 *
 * Rendered only below the `lg` breakpoint (the dashboard sidebar is the
 * navigation on desktop, and this bar must not change that layout).
 * It sits in normal flow at the bottom of the app shell, above the
 * Android system navigation, so it never covers the search bar,
 * composer, or page content.
 *
 * Tab -> route mapping, using routes that already exist in the
 * dashboard (no new pages, and no new data source):
 * - Agents: /profiles — the dashboard's agent-profile roster. There is
 *   no separate Agents route in the web dashboard; the bot roster in
 *   the screenshot lives in the desktop Bot Mode plugin.
 * - Sessions: /sessions — the session list, with a badge fed by
 *   /api/sessions/stats (never a hard-coded count).
 * - Bots Mode: /chat — the agent chat surface, which is Bot Mode's
 *   one-chat-per-agent home in the web dashboard. This tab never
 *   displays a session token or any credential.
 * - Automations: /cron — scheduled automations / cron jobs.
 * - Beta: /config — dashboard settings and flags.
 */
export interface MobileBottomNavTab {
  label: string;
  path: string;
  icon: ComponentType<{ className?: string }>;
  isCenter?: boolean;
}

export const MOBILE_BOTTOM_NAV_TABS: MobileBottomNavTab[] = [
  { label: "Agents", path: "/profiles", icon: Users },
  { label: "Sessions", path: "/sessions", icon: MessageSquare },
  { label: "Bots Mode", path: "/chat", icon: Bot, isCenter: true },
  { label: "Automations", path: "/cron", icon: Clock },
  { label: "Beta", path: "/config", icon: Sparkles },
];

export default function MobileBottomNav({
  closeMobile,
}: {
  closeMobile?: () => void;
}) {
  const [sessionTotal, setSessionTotal] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getSessionStats()
      .then((stats) => {
        if (!cancelled && typeof stats?.total === "number") {
          setSessionTotal(stats.total);
        }
      })
      .catch(() => {
        // Badge is decorative: a stats failure must not break navigation.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <nav
      aria-label="Mobile navigation"
      className="shrink-0 border-t border-current/20 bg-background-base pb-[env(safe-area-inset-bottom,0px)] lg:hidden"
    >
      <ul className="grid grid-cols-5 items-stretch">
        {MOBILE_BOTTOM_NAV_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <li key={tab.label} className="min-w-0">
              <NavLink
                to={tab.path}
                end={tab.path === "/sessions" || tab.path === "/profiles"}
                onClick={closeMobile}
                aria-label={tab.label}
                className={({ isActive }) =>
                  cn(
                    "relative flex min-h-12 flex-col items-center justify-center gap-0.5 px-1 py-2 text-xs",
                    tab.isCenter
                      ? "mx-1 my-1 rounded-full bg-[#d4af37] text-black"
                      : isActive
                        ? "text-[#d4af37]"
                        : "text-text-secondary",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="relative">
                      <Icon className="h-5 w-5" />
                      {tab.label === "Sessions" &&
                        sessionTotal !== null &&
                        sessionTotal > 0 && (
                          <span
                            aria-label={`${sessionTotal} sessions`}
                            className="absolute -right-4 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#d4af37] px-1 text-[10px] font-bold text-black"
                          >
                            {sessionTotal}
                          </span>
                        )}
                    </span>
                    <span>{tab.label}</span>
                    {!tab.isCenter && isActive && (
                      <span
                        aria-hidden
                        className="absolute bottom-0 left-6 right-6 h-0.5 bg-[#d4af37]"
                      />
                    )}
                  </>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
