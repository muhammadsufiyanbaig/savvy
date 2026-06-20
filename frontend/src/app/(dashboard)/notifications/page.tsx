"use client";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, BellOff, CheckCheck, AlertTriangle, Info, TrendingDown, PiggyBank, Sparkles } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { notificationApi } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";
import { useNotificationStore } from "@/store/notificationStore";
import toast from "react-hot-toast";

interface Notification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
  metadata?: Record<string, unknown>;
}

const typeIcon = (type: string) => {
  if (type?.includes("budget") || type?.includes("alert")) return <AlertTriangle size={16} className="text-amber-400" />;
  if (type?.includes("expense")) return <TrendingDown size={16} className="text-rose-400" />;
  if (type?.includes("saving")) return <PiggyBank size={16} className="text-emerald-400" />;
  if (type?.includes("ai") || type?.includes("insight")) return <Sparkles size={16} className="text-violet-400" />;
  return <Info size={16} className="text-cyan-400" />;
};

const typeBg = (type: string) => {
  if (type?.includes("budget") || type?.includes("alert")) return "bg-amber-500/10 border-amber-500/15";
  if (type?.includes("expense")) return "bg-rose-500/10 border-rose-500/15";
  if (type?.includes("saving")) return "bg-emerald-500/10 border-emerald-500/15";
  if (type?.includes("ai") || type?.includes("insight")) return "bg-violet-500/10 border-violet-500/15";
  return "bg-cyan-500/10 border-cyan-500/15";
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [markingAll, setMarkingAll] = useState(false);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const { setUnreadCount } = useNotificationStore();

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationApi.list({ limit: 50 });
      setNotifications(res.data?.notifications || res.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const markRead = async (id: number) => {
    try {
      await notificationApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => n.id === id ? { ...n, is_read: true } : n)
      );
      const unread = notifications.filter((n) => !n.is_read && n.id !== id).length;
      setUnreadCount(unread);
    } catch {}
  };

  const markAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast.success("All notifications marked as read");
    } catch { toast.error("Failed to mark all read"); }
    finally { setMarkingAll(false); }
  };

  const displayed = filter === "unread"
    ? notifications.filter((n) => !n.is_read)
    : notifications;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Notifications" subtitle={`${unreadCount} unread`} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Toolbar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex rounded-xl border border-white/8 bg-white/5 p-1 gap-1">
            {(["all", "unread"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${
                  filter === f
                    ? "bg-violet-600 text-white shadow-glow"
                    : "text-white/40 hover:text-white"
                }`}
              >
                {f === "all" ? "All" : `Unread${unreadCount > 0 ? ` (${unreadCount})` : ""}`}
              </button>
            ))}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              icon={<CheckCheck size={14} />}
              loading={markingAll}
              onClick={markAllRead}
              className="ml-auto"
            >
              Mark all read
            </Button>
          )}
        </div>

        {/* List */}
        <GlassCard hover={false} className="overflow-hidden">
          {loading ? (
            <div className="space-y-1 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-20 rounded-xl shimmer" />
              ))}
            </div>
          ) : displayed.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <BellOff className="mb-3 h-12 w-12 text-white/20" />
              <p className="text-sm text-white/40">
                {filter === "unread" ? "No unread notifications" : "No notifications yet"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              <AnimatePresence>
                {displayed.map((notif) => (
                  <motion.div
                    key={notif.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, height: 0 }}
                    onClick={() => !notif.is_read && markRead(notif.id)}
                    className={`flex items-start gap-4 px-6 py-4 transition-all cursor-pointer hover:bg-white/3 ${
                      !notif.is_read ? "bg-white/3" : ""
                    }`}
                  >
                    <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${typeBg(notif.notification_type)}`}>
                      {typeIcon(notif.notification_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className={`text-sm font-medium ${notif.is_read ? "text-white/60" : "text-white"}`}>
                          {notif.title}
                        </p>
                        {!notif.is_read && (
                          <span className="h-2 w-2 rounded-full bg-violet-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-white/40 mt-0.5 line-clamp-2">{notif.message}</p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <Badge variant="default">{notif.notification_type?.replace(/_/g, " ") || "system"}</Badge>
                        <span className="text-xs text-white/25">{formatRelativeTime(notif.created_at)}</span>
                      </div>
                    </div>
                    {notif.is_read ? (
                      <CheckCheck size={14} className="mt-1 text-white/20 shrink-0" />
                    ) : (
                      <Bell size={14} className="mt-1 text-violet-400 shrink-0" />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
