"use client";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlassCardProps extends HTMLMotionProps<"div"> {
  hover?: boolean;
  glow?: "purple" | "cyan" | "gold" | "none";
  className?: string;
}

export default function GlassCard({ hover = true, glow = "none", className, children, ...props }: GlassCardProps) {
  const glowClass = {
    purple: "hover:shadow-glow",
    cyan: "hover:shadow-glow-cyan",
    gold: "hover:shadow-glow-gold",
    none: "",
  }[glow];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={cn(
        "relative rounded-2xl border border-white/8 bg-white/5 backdrop-blur-xl shadow-glass",
        hover && "transition-all duration-300 hover:bg-white/10 hover:border-white/15 hover:shadow-glass-hover",
        glowClass,
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
