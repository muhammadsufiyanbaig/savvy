import { cn } from "@/lib/utils";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "purple";
  size?: "sm" | "md";
  children: React.ReactNode;
  className?: string;
}

export default function Badge({ variant = "default", size = "sm", children, className }: BadgeProps) {
  const variants = {
    default: "bg-white/10 text-white/70 border-white/10",
    success: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    warning: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    danger: "bg-rose-500/15 text-rose-400 border-rose-500/20",
    info: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
    purple: "bg-violet-500/15 text-violet-400 border-violet-500/20",
  };

  const sizes = {
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-3 py-1",
  };

  return (
    <span className={cn("inline-flex items-center rounded-full border font-medium", variants[variant], sizes[size], className)}>
      {children}
    </span>
  );
}
