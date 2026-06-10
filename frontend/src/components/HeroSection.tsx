import { Battery, Brain, Gauge, Trophy } from "lucide-react";

import type { DashboardHero, ResourceCard } from "../types/dashboard";
import { formatNumber } from "../utils/formatters";
import { ProgressBar } from "./ui/ProgressBar";

const resourceIcons = [Battery, Brain, Gauge];

interface HeroSectionProps {
  hero: DashboardHero;
  resources: ResourceCard[];
}

export function HeroSection({ hero, resources }: HeroSectionProps) {
  return (
    <section className="grid gap-4 xl:grid-cols-[1.35fr_0.45fr_1fr]">
      <article className="panel flex items-center gap-5 p-5">
        <div className="grid h-20 w-20 shrink-0 place-items-center rounded-xl border border-xp/40 bg-xp/10 text-2xl font-semibold text-xp shadow-[0_0_40px_rgba(212,175,55,0.16)]">
          {hero.name.slice(0, 1)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Character Level</p>
              <h2 className="mt-1 text-4xl font-semibold text-zinc-50">Level {hero.level}</h2>
            </div>
            <div className="text-right text-sm text-zinc-500">
              <p>{formatNumber(hero.currentLevelXp)} XP</p>
              <p>{formatNumber(hero.nextLevelXp)} XP next</p>
            </div>
          </div>
          <ProgressBar className="mt-5 h-3" value={hero.progressPercent} />
        </div>
      </article>

      <article className="panel flex flex-col justify-between p-5">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Rank</p>
          <Trophy className="text-xp" size={22} />
        </div>
        <div>
          <p className="text-3xl font-semibold text-xp">{hero.rank}</p>
          <p className="mt-1 text-sm text-zinc-500">Current progression tier</p>
        </div>
      </article>

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
        {resources.map((resource, index) => {
          const Icon = resourceIcons[index] ?? Gauge;

          return (
            <article className="panel flex items-center gap-3 p-4" key={resource.id}>
              <div className="grid h-10 w-10 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-xp">
                <Icon size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-sm font-medium text-zinc-300">{resource.name}</p>
                  <p className="text-sm text-zinc-500">
                    <span className="font-semibold text-zinc-100">{resource.value}</span>/{resource.maxValue}
                  </p>
                </div>
                <ProgressBar className="mt-2 h-2" value={resource.progressPercent} variant="success" />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
