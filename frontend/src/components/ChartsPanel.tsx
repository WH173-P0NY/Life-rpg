import Chart from "chart.js/auto";
import { useEffect, useRef } from "react";

import type { ThemeId } from "../theme";
import type { Achievement, JournalEntry, WeeklyProgress } from "../types/dashboard";
import { JournalPanel } from "./JournalPanel";

interface ChartsPanelProps {
  achievements: Achievement[];
  isApiReady: boolean;
  journalEntries: JournalEntry[];
  theme: ThemeId;
  weeklyProgress: WeeklyProgress;
  onJournalCreated: () => Promise<void>;
}

function readCssColor(name: string, fallback: string): string {
  const root = document.querySelector(".theme-root") ?? document.documentElement;
  const value = getComputedStyle(root).getPropertyValue(name).trim();
  return value ? `rgb(${value})` : fallback;
}

export function ChartsPanel({
  achievements,
  isApiReady,
  journalEntries,
  theme,
  weeklyProgress,
  onJournalCreated
}: ChartsPanelProps) {
  const chartRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!chartRef.current) {
      return undefined;
    }

    const xpColor = readCssColor("--color-xp", "rgb(212 175 55)");
    const successColor = readCssColor("--color-success", "rgb(16 185 129)");
    const mutedColor = readCssColor("--color-text-muted", "rgb(161 161 170)");
    const gridColor = readCssColor("--color-chart-grid", "rgb(255 255 255 / 0.06)");

    const chart = new Chart(chartRef.current, {
      type: "bar",
      data: {
        labels: weeklyProgress.points.map((point) => point.label),
        datasets: [
          {
            label: "XP",
            data: weeklyProgress.points.map((point) => point.xp),
            backgroundColor: xpColor,
            borderRadius: 8
          },
          {
            label: "Minutes",
            data: weeklyProgress.points.map((point) => point.minutes),
            backgroundColor: successColor,
            borderRadius: 8
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: mutedColor
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: gridColor
            },
            ticks: {
              color: mutedColor
            }
          },
          y: {
            grid: {
              color: gridColor
            },
            ticks: {
              color: mutedColor
            }
          }
        }
      }
    });

    return () => chart.destroy();
  }, [theme, weeklyProgress]);

  return (
    <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr_0.9fr]">
      <article className="panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Trend</p>
            <h2>Weekly Progress</h2>
          </div>
          <span>+{weeklyProgress.xp} XP</span>
        </div>
        <div className="mt-4 h-72">
          <canvas ref={chartRef} />
        </div>
      </article>

      <article className="panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Archive</p>
            <h2>Achievements</h2>
          </div>
          <span>{achievements.length}</span>
        </div>
        <div className="mt-4 space-y-3">
          {achievements.map((achievement) => (
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={achievement.id}>
              <p className="text-sm font-semibold text-zinc-100">{achievement.title}</p>
              <p className="mt-1 text-xs capitalize text-zinc-500">
                {achievement.rarity} · {achievement.unlockedAtLabel}
              </p>
            </div>
          ))}
        </div>
      </article>

      <JournalPanel entries={journalEntries} isApiReady={isApiReady} onJournalCreated={onJournalCreated} />
    </section>
  );
}
