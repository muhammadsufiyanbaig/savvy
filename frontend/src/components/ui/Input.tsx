"use client";
import { forwardRef, InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, rightIcon, className, ...props }, ref) => (
    <div className="w-full space-y-1.5">
      {label && (
        <label className="block text-sm font-medium text-white/70">{label}</label>
      )}
      <div className="relative">
        {icon && (
          <div className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-white/40">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={cn(
            "w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder:text-white/30",
            "backdrop-blur-sm transition-all duration-200",
            "focus:border-violet-500/60 focus:bg-white/8 focus:outline-none focus:ring-2 focus:ring-violet-500/20",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error && "border-rose-500/60 focus:border-rose-500/60 focus:ring-rose-500/20",
            icon && "pl-10",
            rightIcon && "pr-10",
            className
          )}
          {...props}
        />
        {rightIcon && (
          <div className="absolute inset-y-0 right-3 flex items-center text-white/40">
            {rightIcon}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  )
);

Input.displayName = "Input";
export default Input;
