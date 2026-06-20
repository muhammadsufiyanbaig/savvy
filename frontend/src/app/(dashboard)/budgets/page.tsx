"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Wallet, AlertTriangle, CheckCircle } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { budgetApi } from "@/lib/api";
import { formatCurrency, CATEGORY_ICONS } from "@/lib/utils";
import toast from "react-hot-toast";

const schema = z.object({
  category: z.string().min(1),
  allocated_amount: z.string().refine((v) => !isNaN(+v) && +v > 0),
  period: z.string().default("monthly"),
  period_start_date: z.string().min(1),
  period_end_date: z.string().min(1),
  alert_threshold: z.string().default("80"),
  currency: z.string().default("USD"),
});
type FormData = z.infer<typeof schema>;

const CATEGORIES = ["Food", "Transport", "Shopping", "Entertainment", "Health", "Education", "Utilities", "Housing", "Other"];

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { period: "monthly", period_start_date: firstDay, period_end_date: lastDay, alert_threshold: "80", currency: "USD" },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [bList, bStatus] = await Promise.allSettled([budgetApi.list(), budgetApi.status("monthly")]);
      if (bList.status === "fulfilled") setBudgets(bList.value.data?.budgets || []);
      if (bStatus.status === "fulfilled") setStatus(bStatus.value.data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      await budgetApi.create({ ...data, allocated_amount: parseFloat(data.allocated_amount), alert_threshold: parseFloat(data.alert_threshold) });
      toast.success("Budget created!");
      reset();
      setShowForm(false);
      fetchData();
    } catch { toast.error("Failed to create budget"); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Budgets" subtitle="Track your spending limits" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Summary */}
        {status && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: "Total Allocated", value: formatCurrency(status.total_allocated as number), color: "text-white" },
              { label: "Total Spent", value: formatCurrency(status.total_spent as number), color: "text-amber-400" },
              { label: "Remaining", value: formatCurrency((status.total_allocated as number) - (status.total_spent as number)), color: "text-emerald-400" },
            ].map((item) => (
              <GlassCard key={item.label} className="p-4 text-center">
                <p className="text-xs text-white/40">{item.label}</p>
                <p className={`text-xl font-bold mt-1 ${item.color}`}>{item.value}</p>
              </GlassCard>
            ))}
          </div>
        )}

        {/* Toolbar */}
        <div className="flex justify-end">
          <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>New Budget</Button>
        </div>

        {/* Form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
              <GlassCard className="p-6" hover={false}>
                <h3 className="mb-4 text-sm font-semibold text-white">Create Budget</h3>
                <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-white/70">Category</label>
                    <select className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-violet-500/60 focus:outline-none" {...register("category")}>
                      <option value="">Select...</option>
                      {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>)}
                    </select>
                    {errors.category && <p className="text-xs text-rose-400">{errors.category.message}</p>}
                  </div>
                  <Input label="Allocated Amount ($)" placeholder="500.00" error={errors.allocated_amount?.message} {...register("allocated_amount")} />
                  <Input label="Start Date" type="date" {...register("period_start_date")} />
                  <Input label="End Date" type="date" {...register("period_end_date")} />
                  <Input label="Alert Threshold (%)" placeholder="80" {...register("alert_threshold")} />
                  <div className="sm:col-span-2 lg:col-span-3 flex gap-3">
                    <Button type="submit" loading={submitting}>Create Budget</Button>
                    <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Budget cards */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-48 rounded-2xl shimmer" />)}
          </div>
        ) : budgets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Wallet className="mb-3 h-12 w-12 text-white/20" />
            <p className="text-sm text-white/40">No budgets yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {budgets.map((b) => {
              const pct = Math.min(100, Math.round(((b.spent_amount as number) / (b.allocated_amount as number)) * 100));
              const over = pct >= 100;
              const alert = pct >= (b.alert_threshold as number);
              return (
                <motion.div key={b.id as number} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-white/8 bg-white/5 p-5 backdrop-blur-xl hover:bg-white/8 transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{CATEGORY_ICONS[b.category as string] || "📦"}</span>
                      <div>
                        <p className="text-sm font-semibold text-white">{b.category as string}</p>
                        <p className="text-xs text-white/40">{b.period as string}</p>
                      </div>
                    </div>
                    <Badge variant={over ? "danger" : alert ? "warning" : "success"}>
                      {over ? "Over" : alert ? "Alert" : "OK"}
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-white/50">
                      <span>Spent: {formatCurrency(b.spent_amount as number)}</span>
                      <span>Limit: {formatCurrency(b.allocated_amount as number)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={`h-2 rounded-full ${over ? "bg-rose-500" : alert ? "bg-amber-500" : "bg-emerald-500"}`}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-white/40">{pct}% used</span>
                      {over ? <AlertTriangle size={12} className="text-rose-400" /> : <CheckCircle size={12} className="text-emerald-400" />}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
