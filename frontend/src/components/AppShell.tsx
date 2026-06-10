import type { ReactNode } from "react";

import type { ThemeId } from "../theme";
import type { DashboardRangeQuery } from "../types/dashboard";
import type { DashboardResponse } from "../types/dashboard";
import { type AppView, Sidebar } from "./Sidebar";
import { type ApiState, TopBar } from "./TopBar";

interface AppShellProps {
  activeView: AppView;
  apiState: ApiState;
  apiStatus: string;
  dashboard: DashboardResponse;
  isLoading: boolean;
  rangeQuery: DashboardRangeQuery;
  theme: ThemeId;
  children: ReactNode;
  onRangeChange: (query: DashboardRangeQuery) => void;
  onViewChange: (view: AppView) => void;
}

export function AppShell({
  activeView,
  apiState,
  apiStatus,
  dashboard,
  isLoading,
  rangeQuery,
  theme,
  children,
  onRangeChange,
  onViewChange
}: AppShellProps) {
  return (
    <div className="theme-root min-h-screen bg-background text-zinc-100" data-theme={theme}>
      <div className="app-background fixed inset-0 -z-10" />
      <Sidebar activeView={activeView} hero={dashboard.hero} onViewChange={onViewChange} />
      <main className="min-h-screen px-4 pb-8 pt-4 lg:ml-[260px] lg:px-8">
        <TopBar
          apiState={apiState}
          apiStatus={apiStatus}
          hero={dashboard.hero}
          isLoading={isLoading}
          rangeQuery={rangeQuery}
          streakDays={dashboard.habitsSummary.streakDays}
          onRangeChange={onRangeChange}
        />
        <div className="space-y-4">{children}</div>
      </main>
    </div>
  );
}
