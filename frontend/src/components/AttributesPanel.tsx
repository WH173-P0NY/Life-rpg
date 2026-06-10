import type { AttributeRow } from "../types/dashboard";
import { useI18n } from "../i18n";
import { ProgressBar } from "./ui/ProgressBar";

interface AttributesPanelProps {
  attributes: AttributeRow[];
}

export function AttributesPanel({ attributes }: AttributesPanelProps) {
  const { t } = useI18n();

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.character")}</p>
          <h2>{t("panel.attributes")}</h2>
        </div>
        <span>{t("panel.growth")}</span>
      </div>

      <div className="mt-4 space-y-4">
        {attributes.map((attribute) => (
          <div key={attribute.id}>
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-zinc-100">{attribute.name}</p>
                <p className="text-xs text-zinc-500">{attribute.description}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-zinc-100">{attribute.value}</p>
                <p className="text-xs text-success">+{attribute.growth}</p>
              </div>
            </div>
            <ProgressBar value={attribute.progressPercent} />
          </div>
        ))}
      </div>
    </article>
  );
}
