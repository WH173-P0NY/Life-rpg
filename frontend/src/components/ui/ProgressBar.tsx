interface ProgressBarProps {
  className?: string;
  value: number;
  variant?: "xp" | "success";
}

export function ProgressBar({ className = "h-2", value, variant = "xp" }: ProgressBarProps) {
  const normalizedValue = Math.max(0, Math.min(100, value));

  return (
    <div className={`overflow-hidden rounded-full bg-white/10 ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-700 ${
          variant === "success"
            ? "bg-gradient-to-r from-success to-xp"
            : "bg-gradient-to-r from-xp to-[#F0C85A]"
        }`}
        style={{ width: `${normalizedValue}%` }}
      />
    </div>
  );
}
