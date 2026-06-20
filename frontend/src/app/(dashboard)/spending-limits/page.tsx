"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Target, Save, AlertTriangle, CheckCircle2 } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { spendingLimitApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

interface SpendingLimitStatus {
  daily_limit: number | null;
  weekly_limit: number | null;
  monthly_limit: number | null;
  daily_spent: number;
  weekly_spent: number;
  monthly_spent: number;
  daily_alert: boolean;
  weekly_alert: boolean;
  monthly_alert: boolean;
}

const schema = z.object({
  daily_limit: z.coerce.number().positive().nullable().optional(),
  weekly_limit: z.coerce.number().positive().nullable().optional(),
  monthly_limit: z.coerce.number().positive().nullable().optional(),
});
type FormData = z.infer<typeof schema>;

function LimitRow({
  label, limit, spent, alert,
}: { label: string; limit: number | null; spent: number; alert: boolean }) {
  const pct = limit ? Math.min(100, (spent / limit) * 100) : 0;
  const color = pct >= 100 ? "bg-rose-500" : pct >= 80 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {alert ? <AlertTriangle size={14} className="text-amber-400" /> : <CheckCircle2 size={14} className="text-emerald-400" />}
          <span className="text-sm font-medium text-white">{label}</span>
        </div>
        <span className="text-xs text-white/40">
          {limit ? `${formatCurrency(spent)} / ${formatCurrency(limit)}` : "No limit set"}
        </span>
      </div>
      {limit && (
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className={`h-full rounded-full ${color}`}
          />
        </div>
      )}
    </div>
  );
}

export default function SpendingLimitsPage() {
  const [status, setStatus] = useState<SpendingLimitStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [limits, stat] = await Promise.allSettled([
        spendingLimitApi.get(),
        spendingLimitApi.status(),
      ]);
      if (limits.status === "fulfilled") {
        const d = limits.value.data;
        reset({
          daily_limit: d.daily_limit || "",
          weekly_limit: d.weekly_limit || "",
          monthly_limit: d.monthly_limit || "",
        });
      }
      if (stat.status === "fulfilled") setStatus(stat.value.data);
    } catch { }
    finally { setLoading(false); }
  }, [reset]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      await spendingLimitApi.update(data);
      toast.success("Spending limits updated!");
      fetchData();
    } catch { toast.error("Failed to update limits"); }
    finally { setSaving(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Spending Limits" subtitle="Set daily, weekly and monthly caps" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Current status */}
        {!loading && status && (
          <GlassCard className="p-6" hover={false}>
            <h3 className="text-sm font-semibold text-white mb-5">Current Usage</h3>
            <div className="space-y-5">
              <LimitRow label="Daily" limit={status.daily_limit} spent={status.daily_spent} alert={status.daily_alert} />
              <LimitRow label="Weekly" limit={status.weekly_limit} spent={status.weekly_spent} alert={status.weekly_alert} />
              <LimitRow label="Monthly" limit={status.monthly_limit} spent={status.monthly_spent} alert={status.monthly_alert} />
            </div>
          </GlassCard>
        )}

        {/* Edit limits */}
        <GlassCard className="p-6" hover={false}>
          <h3 className="text-sm font-semibold text-white mb-1">Set Limits</h3>
          <p className="text-xs text-white/40 mb-5">Leave blank to remove a limit</p>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input
                label="Daily Limit ($)"
                type="number"
                step="0.01"
                placeholder="e.g. 50"
                error={errors.daily_limit?.message}
                {...register("daily_limit")}
              />
              <Input
                label="Weekly Limit ($)"
                type="number"
                step="0.01"
                placeholder="e.g. 300"
                error={errors.weekly_limit?.message}
                {...register("weekly_limit")}
              />
              <Input
                label="Monthly Limit ($)"
                type="number"
                step="0.01"
                placeholder="e.g. 1200"
                error={errors.monthly_limit?.message}
                {...register("monthly_limit")}
              />
            </div>
            <Button type="submit" icon={<Save size={14} />} loading={saving}>
              Save Limits
            </Button>
          </form>
        </GlassCard>

        {/* Info card */}
        <GlassCard className="p-5 border-amber-500/15 bg-amber-500/5" hover={false}>
          <div className="flex items-start gap-3">
            <Target size={18} className="shrink-0 mt-0.5 text-amber-400" />
            <div>
              <p className="text-sm font-medium text-white">How spending limits work</p>
              <p className="mt-1 text-xs text-white/40">
                Limits are checked each time you add an expense. You&apos;ll receive a notification when you approach
                or exceed a limit. Limits reset automatically at midnight (daily), Monday (weekly), and 1st of the month (monthly).
              </p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
