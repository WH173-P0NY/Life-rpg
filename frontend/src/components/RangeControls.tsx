import { useEffect, useState } from "react";

import type { DashboardRange, DashboardRangeQuery } from "../types/dashboard";

const rangeOptions: Array<{ id: DashboardRange; label: string }> = [
  { id: "today", label: "Today" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "custom", label: "Custom" }
];

interface RangeControlsProps {
  isLoading: boolean;
  value: DashboardRangeQuery;
  onChange: (query: DashboardRangeQuery) => void;
}

export function RangeControls({ isLoading, value, onChange }: RangeControlsProps) {
  const [draftStart, setDraftStart] = useState(value.start ?? "");
  const [draftEnd, setDraftEnd] = useState(value.end ?? "");

  useEffect(() => {
    setDraftStart(value.start ?? "");
    setDraftEnd(value.end ?? "");
  }, [value.start, value.end]);

  function setRange(range: DashboardRange) {
    if (range === "custom") {
      onChange({ range, start: draftStart || undefined, end: draftEnd || undefined });
      return;
    }

    onChange({ range });
  }

  return (
    <div className="range-control">
      <div className="range-tabs" aria-label="Dashboard date range">
        {rangeOptions.map((option) => (
          <button
            aria-pressed={value.range === option.id}
            className={`range-tab ${value.range === option.id ? "range-tab-active" : ""}`}
            disabled={isLoading}
            key={option.id}
            onClick={() => setRange(option.id)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>

      {value.range === "custom" ? (
        <div className="custom-range-fields">
          <label>
            <span>Start</span>
            <input
              type="date"
              value={draftStart}
              onChange={(event) => setDraftStart(event.target.value)}
            />
          </label>
          <label>
            <span>End</span>
            <input
              type="date"
              value={draftEnd}
              onChange={(event) => setDraftEnd(event.target.value)}
            />
          </label>
          <button
            disabled={isLoading}
            onClick={() =>
              onChange({
                range: "custom",
                start: draftStart || undefined,
                end: draftEnd || undefined
              })
            }
            type="button"
          >
            Apply
          </button>
        </div>
      ) : null}
    </div>
  );
}
