import { Bell, Flame, Settings, Wifi, WifiOff } from "lucide-react";

import { useI18n } from "../i18n";
import type { DashboardRangeQuery } from "../types/dashboard";
import type { DashboardHero } from "../types/dashboard";
import { RangeControls } from "./RangeControls";

export type ApiState = "loading" | "ready" | "fallback";

interface TopBarProps {
  apiState: ApiState;
  apiStatus: string;
  hero: DashboardHero;
  isLoading: boolean;
  rangeQuery: DashboardRangeQuery;
  streakDays: number;
  onRangeChange: (query: DashboardRangeQuery) => void;
}

export function TopBar({
  apiState,
  apiStatus,
  hero,
  isLoading,
  rangeQuery,
  streakDays,
  onRangeChange
}: TopBarProps) {
  const { t } = useI18n();
  const StatusIcon = apiState === "fallback" ? WifiOff : Wifi;

  return (
    <header className="mb-5 rounded-lg border border-white/10 bg-white/[0.035] px-4 py-4 backdrop-blur-xl">
      <div className="flex min-h-12 flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-xp">{hero.name}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal text-zinc-50">{hero.title}</h1>
          <p className={`mt-2 inline-flex items-center gap-2 text-sm ${apiState === "fallback" ? "text-epic" : "text-zinc-500"}`}>
            <StatusIcon size={15} />
            {apiStatus}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 xl:justify-end">
          <button className="icon-button" type="button" aria-label={t("topbar.notifications")}>
            <Bell size={17} />
          </button>
          <span className="inline-flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
            <Flame size={16} />
            {streakDays} {t("topbar.streakSuffix")}
          </span>
          <button className="icon-button" type="button" aria-label={t("topbar.settings")}>
            <Settings size={17} />
          </button>
        </div>
      </div>

      <RangeControls isLoading={isLoading} value={rangeQuery} onChange={onRangeChange} />
    </header>
  );
}
