"use client";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
  gradient?: string;
  delay?: number;
}

export default function StatCard({ title, value, subtitle, icon, trend, gradient, delay = 0 }: StatCardProps) {
  const isPositive = trend && trend.value >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative overflow-hidden rounded-2xl border border-white/8 bg-white/5 p-6 backdrop-blur-xl shadow-glass hover:bg-white/8 transition-all duration-300 group"
    >
      {gradient && (
        <div className={cn("absolute inset-0 opacity-10 group-hover:opacity-15 transition-opacity", gradient)} />
      )}
      <div className="relative flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm text-white/50 font-medium">{title}</p>
          <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
          {subtitle && <p className="text-xs text-white/40">{subtitle}</p>}
          {trend && (
            <div className={cn("flex items-center gap-1 text-xs font-medium", isPositive ? "text-emerald-400" : "text-rose-400")}>
              <span>{isPositive ? "↑" : "↓"}</span>
              <span>{Math.abs(trend.value)}% {trend.label}</span>
            </div>
          )}
        </div>
        <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-white/8 text-white/70 border border-white/10", gradient && "bg-gradient-to-br opacity-90")}>
          {icon}
        </div>
      </div>
    </motion.div>
  );
}
