"use client";
import { Bell, Search, Sparkles } from "lucide-react";
import { useNotificationStore } from "@/store/notificationStore";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface NavbarProps {
  title: string;
  subtitle?: string;
}

export default function Navbar({ title, subtitle }: NavbarProps) {
  const { unreadCount } = useNotificationStore();

  return (
    <header className="flex h-16 items-center justify-between border-b border-white/8 bg-white/3 backdrop-blur-xl px-6">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-white/40">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden md:flex items-center">
          <Search className="absolute left-3 h-4 w-4 text-white/30" />
          <input
            placeholder="Search..."
            className="h-9 w-56 rounded-xl border border-white/8 bg-white/5 pl-9 pr-4 text-sm text-white placeholder:text-white/30 focus:border-violet-500/40 focus:bg-white/8 focus:outline-none focus:ring-1 focus:ring-violet-500/20 transition-all"
          />
        </div>

        {/* AI quick action */}
        <Link href="/ai-recommendations">
          <button className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-white/50 hover:bg-violet-600/20 hover:text-violet-400 hover:border-violet-500/30 transition-all duration-200">
            <Sparkles className="h-4 w-4" />
          </button>
        </Link>

        {/* Notifications */}
        <Link href="/notifications">
          <button className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-white/50 hover:bg-white/10 hover:text-white transition-all duration-200">
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className={cn(
                "absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-violet-600 px-1 text-[10px] font-bold text-white",
              )}>
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>
        </Link>
      </div>
    </header>
  );
}
