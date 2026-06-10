import type { SkillRow } from "../types/dashboard";
import { useI18n } from "../i18n";
import { ProgressBar } from "./ui/ProgressBar";

interface SkillsPanelProps {
  skills: SkillRow[];
}

export function SkillsPanel({ skills }: SkillsPanelProps) {
  const { t } = useI18n();

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.progression")}</p>
          <h2>{t("panel.skills")}</h2>
        </div>
        <span>{skills.length} {t("common.tracked")}</span>
      </div>

      <div className="mt-4 space-y-4">
        {skills.map((skill) => (
          <div key={skill.id}>
            <div className="mb-2 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-zinc-100">{skill.name}</p>
                <p className="text-xs text-zinc-500">{skill.xp} XP</p>
              </div>
              <span className="rounded-md border border-xp/30 bg-xp/10 px-2 py-1 text-xs font-semibold text-xp">
                {t("panel.lvl")} {skill.level}
              </span>
            </div>
            <ProgressBar value={skill.progressPercent} />
          </div>
        ))}
      </div>
    </article>
  );
}
