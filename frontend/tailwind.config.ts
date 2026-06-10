import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--color-background) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        surfaceStrong: "rgb(var(--color-surface-strong) / <alpha-value>)",
        xp: "rgb(var(--color-xp) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        rare: "rgb(var(--color-rare) / <alpha-value>)",
        epic: "rgb(var(--color-epic) / <alpha-value>)"
      },
      boxShadow: {
        premium: "var(--shadow-premium)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
} satisfies Config;
