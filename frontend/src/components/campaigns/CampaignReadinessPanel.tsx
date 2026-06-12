import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";

import { useI18n } from "../../i18n";
import type { CampaignValidationReport } from "../../types/campaigns";

interface CampaignReadinessPanelProps {
  validation: CampaignValidationReport;
}

function translateWithFallback(
  t: (key: string) => string,
  key: string,
  fallback: string
): string {
  const translated = t(key);

  return translated === key ? fallback : translated;
}

export function CampaignReadinessPanel({ validation }: CampaignReadinessPanelProps) {
  const { t } = useI18n();

  return (
    <section className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("campaigns.studio.readiness")}</p>
          <h2>
            {validation.valid
              ? t("campaigns.studio.readyToPublish")
              : t("campaigns.studio.needsWork")}
          </h2>
        </div>
        <span>{validation.valid ? t("campaigns.studio.ready") : t("campaigns.studio.draft")}</span>
      </div>

      <div className="mt-4 space-y-2">
        {validation.checks.map((check) => (
          <div
            className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3"
            key={check.code}
          >
            {check.passed ? (
              <CheckCircle2 className="mt-0.5 shrink-0 text-success" size={17} />
            ) : (
              <CircleDashed className="mt-0.5 shrink-0 text-xp" size={17} />
            )}
            <div>
              <p className="text-sm font-semibold text-zinc-100">
                {translateWithFallback(
                  t,
                  `campaigns.validation.${check.code}`,
                  check.label ?? check.message ?? check.code
                )}
              </p>
              {!check.passed ? (
                <p className="mt-1 text-xs leading-5 text-zinc-500">
                  {translateWithFallback(
                    t,
                    `campaigns.validation.${check.code}.hint`,
                    check.message ?? ""
                  )}
                </p>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {validation.issues.length ? (
        <div className="mt-4 space-y-2">
          {validation.issues.map((issue, index) => (
            <div
              className="rounded-lg border border-epic/30 bg-epic/10 p-3 text-sm text-epic"
              key={`${issue.code}-${issue.nodeId ?? issue.edgeId ?? index}`}
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 shrink-0" size={16} />
                <p>{issue.message}</p>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
