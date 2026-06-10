import type { ThemeId } from "../theme";
import { themeOptions } from "../theme";

interface ThemeSwitcherProps {
  value: ThemeId;
  onChange: (theme: ThemeId) => void;
}

export function ThemeSwitcher({ value, onChange }: ThemeSwitcherProps) {
  return (
    <div className="theme-switcher" aria-label="Dashboard theme">
      {themeOptions.map((theme) => {
        const Icon = theme.icon;
        const isActive = theme.id === value;

        return (
          <button
            aria-pressed={isActive}
            className={`theme-option ${isActive ? "theme-option-active" : ""}`}
            key={theme.id}
            onClick={() => onChange(theme.id)}
            title={`${theme.label}: ${theme.description}`}
            type="button"
          >
            <Icon size={15} />
            <span>{theme.shortLabel}</span>
          </button>
        );
      })}
    </div>
  );
}
