import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchDashboard } from "./api/dashboard";
import { ActivityForm } from "./components/ActivityForm";
import { AppShell } from "./components/AppShell";
import { AttributesPanel } from "./components/AttributesPanel";
import { AchievementsView } from "./components/AchievementsView";
import { CalendarView } from "./components/CalendarView";
import { ChartsPanel } from "./components/ChartsPanel";
import { ChallengePanel } from "./components/ChallengePanel";
import { GoalsView } from "./components/GoalsView";
import { HabitsPanel } from "./components/HabitsPanel";
import { HeroSection } from "./components/HeroSection";
import { HeroJournalView } from "./components/HeroJournalView";
import { QuestsPanel } from "./components/QuestsPanel";
import { SettingsView } from "./components/SettingsView";
import type { AppView } from "./components/Sidebar";
import { SkillsPanel } from "./components/SkillsPanel";
import { StatusesPanel } from "./components/StatusesPanel";
import { mockDashboard } from "./data/mockDashboard";
import { useI18n } from "./i18n";
import { defaultTheme, isThemeId, type ThemeId } from "./theme";
import type { DashboardRangeQuery, DashboardResponse } from "./types/dashboard";

type ApiState = "loading" | "ready" | "fallback";

const themeStorageKey = "life-rpg-dashboard-theme";
const viewIds: AppView[] = [
  "dashboard",
  "quests",
  "habits",
  "skills",
  "goals",
  "achievements",
  "journal",
  "inventory",
  "finance",
  "calendar",
  "settings"
];

function getInitialTheme(): ThemeId {
  const storedTheme = window.localStorage.getItem(themeStorageKey);
  return isThemeId(storedTheme) ? storedTheme : defaultTheme;
}

function isAppView(value: string): value is AppView {
  return viewIds.includes(value as AppView);
}

function getInitialView(): AppView {
  const hashView = window.location.hash.replace("#", "");
  return isAppView(hashView) ? hashView : "dashboard";
}

export default function App() {
  const { t } = useI18n();
  const [activeView, setActiveView] = useState<AppView>(getInitialView);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [apiState, setApiState] = useState<ApiState>("loading");
  const [isLoading, setIsLoading] = useState(true);
  const [rangeQuery, setRangeQuery] = useState<DashboardRangeQuery>({ range: "today" });
  const [theme, setTheme] = useState<ThemeId>(getInitialTheme);

  const refreshDashboard = useCallback(async () => {
    setIsLoading(true);
    setApiState((current) => (current === "ready" ? "ready" : "loading"));

    try {
      const response = await fetchDashboard(rangeQuery);
      setDashboard(response);
      setApiState("ready");
    } catch {
      setDashboard(mockDashboard);
      setApiState("fallback");
    } finally {
      setIsLoading(false);
    }
  }, [rangeQuery]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    function handleHashChange() {
      const hashView = window.location.hash.replace("#", "");
      setActiveView(isAppView(hashView) ? hashView : "dashboard");
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  const apiStatus = useMemo(() => {
    if (apiState === "loading") {
      return t("api.loading");
    }
    if (apiState === "fallback") {
      return t("api.fallback");
    }
    return t("api.ready");
  }, [apiState, t]);

  const isApiReady = apiState === "ready";

  function handleViewChange(view: AppView) {
    setActiveView(view);
    window.location.hash = view;
  }

  function renderActiveView() {
    if (!dashboard) {
      return null;
    }

    switch (activeView) {
      case "quests":
        return (
          <>
            <ViewHeader label={t("view.quests.label")} title={t("view.quests.title")} meta={`${dashboard.dailyQuests.length} ${t("view.quests.meta")}`} />
            <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <QuestsPanel
                isApiReady={isApiReady}
                quests={dashboard.dailyQuests}
                onQuestChanged={refreshDashboard}
              />
              <ActivityForm
                activityDefinitions={dashboard.activityDefinitions}
                onActivityCreated={refreshDashboard}
              />
            </section>
          </>
        );
      case "habits":
        return (
          <>
            <ViewHeader label={t("view.habits.label")} title={t("view.habits.title")} meta={`${dashboard.habitsSummary.completed}/${dashboard.habitsSummary.total} ${t("view.habits.meta")}`} />
            <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <HabitsPanel
                habits={dashboard.habits}
                isApiReady={isApiReady}
                summary={dashboard.habitsSummary}
                onHabitChanged={refreshDashboard}
              />
              <StatusesPanel statuses={dashboard.statuses} />
            </section>
          </>
        );
      case "skills":
        return (
          <>
            <ViewHeader label={t("view.skills.label")} title={t("view.skills.title")} meta={`${dashboard.skills.length} ${t("view.skills.meta")}`} />
            <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <SkillsPanel skills={dashboard.skills} />
              <AttributesPanel attributes={dashboard.attributes} />
            </section>
          </>
        );
      case "goals":
        return (
          <>
            <ViewHeader label={t("view.goals.label")} title={t("view.goals.title")} meta={t("view.goals.meta")} />
            <GoalsView isApiReady={isApiReady} onProgressionChanged={refreshDashboard} />
          </>
        );
      case "achievements":
        return (
          <>
            <ViewHeader label={t("view.achievements.label")} title={t("view.achievements.title")} meta={`${dashboard.achievements.length} ${t("view.achievements.meta")}`} />
            <AchievementsView isApiReady={isApiReady} onAchievementsChanged={refreshDashboard} />
          </>
        );
      case "journal":
        return (
          <>
            <ViewHeader label={t("view.journal.label")} title={t("view.journal.title")} meta={t("view.journal.meta")} />
            <HeroJournalView isApiReady={isApiReady} onJournalChanged={refreshDashboard} />
          </>
        );
      case "inventory":
        return (
          <>
            <ViewHeader label={t("view.inventory.label")} title={t("view.inventory.title")} meta={t("view.inventory.meta")} />
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <EmptyStatePanel title={t("view.inventory.equipment")} value={t("view.inventory.equipmentEmpty")} />
              <EmptyStatePanel title={t("view.inventory.artifacts")} value={t("view.inventory.artifactsEmpty")} />
              <EmptyStatePanel title={t("view.inventory.rewards")} value={t("view.inventory.rewardsEmpty")} />
            </section>
          </>
        );
      case "finance":
        return (
          <>
            <ViewHeader label={t("view.finance.label")} title={t("view.finance.title")} meta={t("view.finance.meta")} />
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <EmptyStatePanel title={t("view.finance.accounts")} value={t("view.finance.accountsEmpty")} />
              <EmptyStatePanel title={t("view.finance.budget")} value={t("view.finance.budgetEmpty")} />
              <EmptyStatePanel title={t("view.finance.cashflow")} value={t("view.finance.cashflowEmpty")} />
            </section>
          </>
        );
      case "calendar":
        return (
          <>
            <ViewHeader label={t("view.calendar.label")} title={t("view.calendar.title")} meta={t("view.calendar.meta")} />
            <CalendarView isApiReady={isApiReady} />
          </>
        );
      case "settings":
        return (
          <>
            <ViewHeader label={t("view.settings.label")} title={t("view.settings.title")} meta={apiStatus} />
            <SettingsView
              apiStatus={apiStatus}
              isApiReady={isApiReady}
              theme={theme}
              onCatalogChanged={refreshDashboard}
              onThemeChange={setTheme}
            />
          </>
        );
      case "dashboard":
      default:
        return (
          <>
            <HeroSection hero={dashboard.hero} resources={dashboard.resources} />

            <section className="grid gap-4 xl:grid-cols-[1fr_1.2fr_0.9fr]">
              <AttributesPanel attributes={dashboard.attributes} />
              <QuestsPanel
                isApiReady={isApiReady}
                quests={dashboard.dailyQuests}
                onQuestChanged={refreshDashboard}
              />
              <ChallengePanel
                challenge={dashboard.activeChallenge}
                isApiReady={isApiReady}
                onChallengeChanged={refreshDashboard}
              />
            </section>

            <section className="grid gap-4 xl:grid-cols-[0.9fr_1fr_1.1fr]">
              <HabitsPanel
                habits={dashboard.habits}
                isApiReady={isApiReady}
                summary={dashboard.habitsSummary}
                onHabitChanged={refreshDashboard}
              />
              <SkillsPanel skills={dashboard.skills} />
              <StatusesPanel statuses={dashboard.statuses} />
            </section>

            <section className="grid gap-4 xl:grid-cols-[0.95fr_1.55fr]">
              <ActivityForm
                activityDefinitions={dashboard.activityDefinitions}
                onActivityCreated={refreshDashboard}
              />
              <ChartsPanel
                achievements={dashboard.achievements}
                isApiReady={isApiReady}
                journalEntries={dashboard.journalEntries}
                theme={theme}
                weeklyProgress={dashboard.weeklyProgress}
                onJournalCreated={refreshDashboard}
              />
            </section>
          </>
        );
    }
  }

  if (!dashboard) {
    return (
      <div className="theme-root loading-screen min-h-screen bg-background text-zinc-100" data-theme={theme}>
        <div className="app-background fixed inset-0 -z-10" />
        <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center px-6 text-center">
          <div className="grid h-16 w-16 place-items-center rounded-lg border border-xp/40 bg-xp/10 text-2xl font-semibold text-xp">
            L
          </div>
          <p className="mt-6 text-xs font-medium uppercase tracking-[0.24em] text-xp">{t("loading.label")}</p>
          <h1 className="mt-2 text-3xl font-semibold text-zinc-50">{t("loading.title")}</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            {t("loading.description")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <AppShell
      activeView={activeView}
      apiState={apiState}
      apiStatus={apiStatus}
      dashboard={dashboard}
      isLoading={isLoading}
      rangeQuery={rangeQuery}
      theme={theme}
      onRangeChange={setRangeQuery}
      onViewChange={handleViewChange}
    >
      {renderActiveView()}

      {apiState === "fallback" ? (
        <p className="rounded-lg border border-epic/30 bg-epic/10 px-4 py-3 text-sm text-epic">
          {t("api.previewPaused")}
        </p>
      ) : null}
    </AppShell>
  );
}

interface ViewHeaderProps {
  label: string;
  title: string;
  meta: string;
}

function ViewHeader({ label, title, meta }: ViewHeaderProps) {
  return (
    <section className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{label}</p>
          <h2>{title}</h2>
        </div>
        <span>{meta}</span>
      </div>
    </section>
  );
}

interface EmptyStatePanelProps {
  title: string;
  value: string;
}

function EmptyStatePanel({ title, value }: EmptyStatePanelProps) {
  const { t } = useI18n();

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("view.state")}</p>
          <h2>{title}</h2>
        </div>
        <span>{t("view.empty")}</span>
      </div>
      <p className="mt-4 text-sm text-zinc-500">{value}</p>
    </article>
  );
}
