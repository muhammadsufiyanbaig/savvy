"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, Receipt, PiggyBank, Wallet, Building2,
  Sparkles, Bell, Settings, LogOut, TrendingUp, ChevronLeft, Menu,
  Coins, Target, Scale, Beef, BarChart3, Heart, Minus, Moon, Activity,
} from "lucide-react";
import { cn, getInitials } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import { useNotificationStore } from "@/store/notificationStore";
import { useState } from "react";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/expenses", label: "Expenses", icon: Receipt },
  { href: "/budgets", label: "Budgets", icon: Wallet },
  { href: "/savings", label: "Savings", icon: PiggyBank },
  { href: "/cash-savings", label: "Cash Savings", icon: Coins },
  { href: "/spending-limits", label: "Spending Limits", icon: Target },
  { href: "/assets", label: "Assets", icon: BarChart3 },
  { href: "/banks", label: "Banks", icon: Building2 },
  { href: "/ai-recommendations", label: "AI Insights", icon: Sparkles },
  { href: "/notifications", label: "Notifications", icon: Bell, badge: true },
  { href: "/zakat",            label: "Zakat",            icon: Scale,     section: "Islamic" },
  { href: "/qurbani",          label: "Qurbani",          icon: Beef,      section: "Islamic" },
  { href: "/sadaqah-tracker",  label: "Sadaqah",          icon: Heart,     section: "Islamic" },
  { href: "/hajj-umrah",       label: "Hajj / Umrah",     icon: Moon,      section: "Islamic" },
  { href: "/net-worth",        label: "Net Worth",        icon: Minus,     section: "Planning" },
  { href: "/financial-health", label: "Health Score",     icon: Activity,  section: "Planning" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { unreadCount } = useNotificationStore();
  const [collapsed, setCollapsed] = useState(false);
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    logout();
    router.push("/login");
    toast.success("Logged out successfully");
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="relative flex h-screen flex-col border-r border-white/8 bg-white/3 backdrop-blur-2xl"
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-white/8">
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex items-center gap-2"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-purple-700 shadow-glow">
                <TrendingUp className="h-4 w-4 text-white" />
              </div>
              <span className="text-lg font-bold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                Savvy
              </span>
            </motion.div>
          )}
        </AnimatePresence>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors"
        >
          {collapsed ? <Menu className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map(({ href, label, icon: Icon, badge, section }, idx) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          const prevSection = idx > 0 ? navItems[idx - 1].section : undefined;
          const showSectionHeader = section && section !== prevSection;
          return (
            <div key={href}>
              {showSectionHeader && !collapsed && (
                <p className="px-3 pt-3 pb-1 text-xs font-semibold text-white/25 uppercase tracking-wider">
                  {section}
                </p>
              )}
              <Link href={href}>
                <motion.div
                  whileHover={{ x: 2 }}
                  className={cn(
                    "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    active
                      ? "bg-gradient-to-r from-violet-600/30 to-purple-600/20 text-white border border-violet-500/20 shadow-glow"
                      : "text-white/50 hover:bg-white/8 hover:text-white"
                  )}
                >
                  {active && (
                    <motion.div
                      layoutId="active-pill"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-full bg-violet-400"
                    />
                  )}
                  <Icon className={cn("h-4.5 w-4.5 shrink-0", active ? "text-violet-400" : "")} size={18} />
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="truncate"
                      >
                        {label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  {badge && unreadCount > 0 && !collapsed && (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-violet-600 px-1.5 text-xs text-white">
                      {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                  )}
                  {badge && unreadCount > 0 && collapsed && (
                    <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-violet-500" />
                  )}
                </motion.div>
              </Link>
            </div>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="border-t border-white/8 p-2 space-y-1">
        <Link href="/settings">
          <div className={cn(
            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/50 hover:bg-white/8 hover:text-white transition-all duration-200",
          )}>
            <Settings size={18} className="shrink-0" />
            <AnimatePresence>
              {!collapsed && <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>Settings</motion.span>}
            </AnimatePresence>
          </div>
        </Link>

        {/* User profile */}
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 to-purple-700 text-xs font-bold text-white">
            {user ? getInitials(user.full_name || user.username) : "?"}
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">{user?.full_name || user?.username}</p>
                <p className="text-xs text-white/40 truncate">{user?.email}</p>
              </motion.div>
            )}
          </AnimatePresence>
          {!collapsed && (
            <button onClick={handleLogout} className="text-white/30 hover:text-rose-400 transition-colors">
              <LogOut size={15} />
            </button>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
