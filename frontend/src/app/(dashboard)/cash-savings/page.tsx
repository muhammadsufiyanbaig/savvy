"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Coins, Plus, X, Home, Briefcase, PiggyBank, Landmark } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { cashApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

interface CashSaving {
  id: number;
  label: string;
  amount: number;
  currency: string;
  location?: string;
  purpose?: string;
  notes?: string;
  created_at: string;
}

interface Summary {
  total_amount: number;
  count: number;
  by_location: Record<string, number>;
}

const schema = z.object({
  label: z.string().min(1, "Label required"),
  amount: z.coerce.number().positive("Must be positive"),
  currency: z.string().default("USD"),
  location: z.string().optional(),
  purpose: z.string().optional(),
  notes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

const locationIcon = (loc?: string) => {
  if (loc?.toLowerCase().includes("home")) return <Home size={16} className="text-emerald-400" />;
  if (loc?.toLowerCase().includes("bank")) return <Landmark size={16} className="text-blue-400" />;
  if (loc?.toLowerCase().includes("work")) return <Briefcase size={16} className="text-amber-400" />;
  return <PiggyBank size={16} className="text-violet-400" />;
};

export default function CashSavingsPage() {
  const [records, setRecords] = useState<CashSaving[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "USD" },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await cashApi.list();
      setRecords(res.data?.cash_savings || []);
      setSummary(res.data?.summary || null);
    } catch { toast.error("Failed to load cash savings"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      await cashApi.create(data);
      toast.success("Cash saving added!");
      reset();
      setShowForm(false);
      fetchData();
    } catch { toast.error("Failed to add cash saving"); }
    finally { setSaving(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Cash Savings" subtitle="Track physical cash and offline savings" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <GlassCard className="p-5" hover={false}>
              <p className="text-xs text-white/40 mb-1">Total Cash Saved</p>
              <p className="text-2xl font-bold text-emerald-400">{formatCurrency(summary.total_amount)}</p>
            </GlassCard>
            <GlassCard className="p-5" hover={false}>
              <p className="text-xs text-white/40 mb-1">Locations</p>
              <p className="text-2xl font-bold text-white">{Object.keys(summary.by_location || {}).length}</p>
            </GlassCard>
            <GlassCard className="p-5" hover={false}>
              <p className="text-xs text-white/40 mb-1">Entries</p>
              <p className="text-2xl font-bold text-white">{summary.count}</p>
            </GlassCard>
          </div>
        )}

        {/* Header + add button */}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">All Cash Savings</h2>
          <Button icon={<Plus size={14} />} onClick={() => setShowForm(true)} size="sm">Add Entry</Button>
        </div>

        {/* Add form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <GlassCard className="p-6" hover={false}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">New Cash Saving</h3>
                  <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white">
                    <X size={16} />
                  </button>
                </div>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input label="Label" placeholder="Emergency fund" error={errors.label?.message} {...register("label")} />
                    <Input label="Amount" type="number" step="0.01" placeholder="500" error={errors.amount?.message} {...register("amount")} />
                    <Input label="Location" placeholder="Home safe, Bank, etc." {...register("location")} />
                    <Input label="Purpose" placeholder="Emergency, Hajj, etc." {...register("purpose")} />
                    <Input label="Notes" placeholder="Optional notes..." className="sm:col-span-2" {...register("notes")} />
                  </div>
                  <div className="flex gap-3">
                    <Button type="submit" loading={saving}>Save Entry</Button>
                    <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Records list */}
        <GlassCard hover={false} className="overflow-hidden">
          {loading ? (
            <div className="space-y-1 p-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 rounded-xl shimmer" />)}</div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Coins className="mb-3 h-12 w-12 text-white/20" />
              <p className="text-sm text-white/40">No cash savings recorded yet</p>
              <Button className="mt-4" size="sm" onClick={() => setShowForm(true)}>Add your first entry</Button>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {records.map((rec) => (
                <motion.div
                  key={rec.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-4 px-6 py-4"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5">
                    {locationIcon(rec.location)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{rec.label}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {rec.location && <span className="text-xs text-white/40">{rec.location}</span>}
                      {rec.purpose && <span className="text-xs text-violet-400/60">· {rec.purpose}</span>}
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-emerald-400">{formatCurrency(rec.amount)}</p>
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
