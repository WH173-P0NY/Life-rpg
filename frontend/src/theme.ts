import type { LucideIcon } from "lucide-react";
import { BookOpen, Cpu, Leaf, Moon, Shield } from "lucide-react";

export type ThemeId =
  | "minimal-dark"
  | "cyberpunk"
  | "living-world"
  | "adventurers-journal"
  | "premium-hybrid";

export interface ThemeOption {
  id: ThemeId;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
}

export const themeOptions: ThemeOption[] = [
  {
    id: "premium-hybrid",
    label: "Legendary Hero",
    shortLabel: "Legendary",
    description: "Premium productivity with RPG progression.",
    icon: Shield
  },
  {
    id: "minimal-dark",
    label: "Minimal Dark RPG",
    shortLabel: "Minimal",
    description: "Linear-like dark character sheet.",
    icon: Moon
  },
  {
    id: "cyberpunk",
    label: "Cyberpunk OS",
    shortLabel: "Cyberpunk",
    description: "Neon personal upgrade interface.",
    icon: Cpu
  },
  {
    id: "living-world",
    label: "Living World",
    shortLabel: "Nature",
    description: "Personal growth as an ecosystem.",
    icon: Leaf
  },
  {
    id: "adventurers-journal",
    label: "Adventurer Journal",
    shortLabel: "Journal",
    description: "A premium chronicle of progress.",
    icon: BookOpen
  }
];

export const defaultTheme: ThemeId = "premium-hybrid";

export function isThemeId(value: string | null): value is ThemeId {
  return themeOptions.some((theme) => theme.id === value);
}
