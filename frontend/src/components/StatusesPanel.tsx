import type { StatusRow } from "../types/dashboard";
import { useI18n } from "../i18n";
import { ProgressBar } from "./ui/ProgressBar";

interface StatusesPanelProps {
  statuses: StatusRow[];
}

export function StatusesPanel({ statuses }: StatusesPanelProps) {
  const { t } = useI18n();

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.characterState")}</p>
          <h2>{t("panel.statuses")}</h2>
        </div>
        <span>{statuses.length} {t("panel.active")}</span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        {statuses.map((status) => (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={status.id}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-zinc-100">{status.name}</p>
              <p className="text-sm text-zinc-500">
                <span className="font-semibold text-zinc-100">{status.value}</span>/{status.maxValue}
              </p>
            </div>
            <ProgressBar className="mt-3 h-2" value={status.progressPercent} variant="success" />
          </div>
        ))}
      </div>
    </article>
  );
}
