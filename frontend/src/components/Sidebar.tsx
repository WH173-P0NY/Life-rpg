import {
  Award,
  CalendarDays,
  CheckSquare,
  Crown,
  Dumbbell,
  Home,
  Package,
  ScrollText,
  Settings,
  Shield,
  Target,
  WalletCards
} from "lucide-react";

import { useI18n } from "../i18n";
import type { TranslationKey } from "../i18n";
import type { DashboardHero } from "../types/dashboard";

export type AppView =
  | "dashboard"
  | "quests"
  | "habits"
  | "skills"
  | "goals"
  | "achievements"
  | "journal"
  | "inventory"
  | "finance"
  | "calendar"
  | "settings";

const navItems = [
  { id: "dashboard", labelKey: "nav.dashboard", icon: Home },
  { id: "quests", labelKey: "nav.quests", icon: CheckSquare },
  { id: "habits", labelKey: "nav.habits", icon: Target },
  { id: "skills", labelKey: "nav.skills", icon: Dumbbell },
  { id: "goals", labelKey: "nav.goals", icon: Crown },
  { id: "achievements", labelKey: "nav.achievements", icon: Award },
  { id: "journal", labelKey: "nav.journal", icon: ScrollText },
  { id: "inventory", labelKey: "nav.inventory", icon: Package },
  { id: "finance", labelKey: "nav.finance", icon: WalletCards },
  { id: "calendar", labelKey: "nav.calendar", icon: CalendarDays },
  { id: "settings", labelKey: "nav.settings", icon: Settings }
] satisfies Array<{ id: AppView; labelKey: TranslationKey; icon: typeof Home }>;

interface SidebarProps {
  activeView: AppView;
  hero: DashboardHero;
  onViewChange: (view: AppView) => void;
}

export function Sidebar({ activeView, hero, onViewChange }: SidebarProps) {
  const { t } = useI18n();

  return (
    <aside className="border-white/10 bg-black/20 backdrop-blur-xl lg:fixed lg:inset-y-0 lg:left-0 lg:w-[260px] lg:border-r">
      <div className="flex min-h-full flex-col p-4">
        <div className="mb-7 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-lg border border-xp/50 bg-xp/10 text-xp">
            <Shield size={23} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-[0.18em] text-zinc-100">LIFE RPG</p>
            <p className="text-xs text-zinc-500">{t("app.tagline")}</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === activeView;

            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${
                  isActive
                    ? "border border-xp/30 bg-xp/10 text-xp shadow-[0_0_24px_rgba(212,175,55,0.12)]"
                    : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
                }`}
                key={item.id}
                onClick={() => onViewChange(item.id)}
                type="button"
              >
                <Icon size={17} />
                {t(item.labelKey)}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto hidden items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 lg:flex">
          <div className="grid h-11 w-11 place-items-center rounded-full border border-xp/40 bg-zinc-900 text-sm font-semibold text-xp">
            {hero.name.slice(0, 1)}
          </div>
          <div>
            <p className="text-sm font-semibold">{hero.name}</p>
            <p className="text-xs text-zinc-500">
              {t("app.level")} {hero.level} · {hero.rank} {t("app.rank")}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
