"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Beef, Plus, X, Banknote } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { qurbaniApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

interface QurbaniRecord {
  id: number;
  animal_type: string;
  target_amount: number;
  saved_amount: number;
  target_year: number;
  is_complete: boolean;
  currency: string;
  notes?: string;
}

interface QurbaniSummary {
  total_records: number;
  total_target: number;
  total_saved: number;
  total_remaining: number;
  complete: number;
}

interface AnimalPrices {
  [animal: string]: number;
}

const schema = z.object({
  animal_type: z.string().min(1, "Animal type required"),
  target_amount: z.coerce.number().positive("Must be positive"),
  target_year: z.coerce.number().int().positive(),
  currency: z.string().default("PKR"),
  notes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

const ANIMAL_TYPES = ["Goat", "Sheep", "Cow (1/7 share)", "Cow (full)", "Camel (1/7 share)", "Camel (full)"];

export default function QurbaniPage() {
  const [records, setRecords] = useState<QurbaniRecord[]>([]);
  const [summary, setSummary] = useState<QurbaniSummary | null>(null);
  const [prices, setPrices] = useState<AnimalPrices>({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showContribute, setShowContribute] = useState<number | null>(null);
  const [contributeAmt, setContributeAmt] = useState("");
  const [saving, setSaving] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "PKR", target_year: new Date().getFullYear() + 1 },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [recs, priceData] = await Promise.allSettled([
        qurbaniApi.list(),
        qurbaniApi.prices("PKR"),
      ]);
      if (recs.status === "fulfilled") {
        setRecords(recs.value.data?.savings || []);
        setSummary(recs.value.data?.summary || null);
      }
      if (priceData.status === "fulfilled") setPrices(priceData.value.data?.prices || priceData.value.data || {});
    } catch { }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      await qurbaniApi.create(data);
      toast.success("Qurbani saving created!");
      reset();
      setShowForm(false);
      fetchData();
    } catch { toast.error("Failed to create qurbani saving"); }
    finally { setSaving(false); }
  };

  const contribute = async (id: number) => {
    const amount = parseFloat(contributeAmt);
    if (isNaN(amount) || amount <= 0) { toast.error("Enter valid amount"); return; }
    try {
      await qurbaniApi.contribute(id, { amount });
      toast.success("Contribution added!");
      setShowContribute(null);
      setContributeAmt("");
      fetchData();
    } catch { toast.error("Failed to add contribution"); }
  };

  const progressPct = (rec: QurbaniRecord) =>
    rec.target_amount > 0 ? Math.min(100, (rec.saved_amount / rec.target_amount) * 100) : 0;

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Qurbani" subtitle="Save for your annual Qurbani obligation" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Prices reference */}
        {Object.keys(prices).length > 0 && (
          <GlassCard className="p-5" hover={false}>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Approximate Animal Prices (PKR)</p>
            <div className="flex flex-wrap gap-3">
              {Object.entries(prices).map(([animal, price]) => (
                <div key={animal} className="rounded-lg border border-white/8 bg-white/5 px-3 py-1.5 text-xs">
                  <span className="text-white/60">{animal}: </span>
                  <span className="font-semibold text-amber-300">{formatCurrency(price as number, "PKR")}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Total Plans", value: summary.total_records },
              { label: "Target", value: formatCurrency(summary.total_target, "PKR") },
              { label: "Saved", value: formatCurrency(summary.total_saved, "PKR") },
              { label: "Remaining", value: formatCurrency(summary.total_remaining, "PKR"), highlight: summary.total_remaining > 0 },
            ].map(({ label, value, highlight }) => (
              <GlassCard key={label} className="p-4" hover={false}>
                <p className="text-xs text-white/40 mb-1">{label}</p>
                <p className={`text-lg font-bold ${highlight ? "text-amber-400" : "text-white"}`}>{value}</p>
              </GlassCard>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Qurbani Plans</h2>
          <Button icon={<Plus size={14} />} onClick={() => setShowForm(true)} size="sm">New Plan</Button>
        </div>

        {/* Form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <GlassCard className="p-6" hover={false}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">New Qurbani Plan</h3>
                  <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white"><X size={16} /></button>
                </div>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-white/60">Animal Type</label>
                      <select
                        {...register("animal_type")}
                        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                      >
                        <option value="">Select animal</option>
                        {ANIMAL_TYPES.map((a) => <option key={a} value={a} className="bg-gray-900">{a}</option>)}
                      </select>
                      {errors.animal_type && <p className="mt-1 text-xs text-rose-400">{errors.animal_type.message}</p>}
                    </div>
                    <Input label="Target Amount (PKR)" type="number" step="0.01" placeholder="e.g. 50000" error={errors.target_amount?.message} {...register("target_amount")} />
                    <Input label="Target Year" type="number" placeholder={String(new Date().getFullYear() + 1)} error={errors.target_year?.message} {...register("target_year")} />
                    <Input label="Notes" placeholder="Optional..." {...register("notes")} />
                  </div>
                  <div className="flex gap-3">
                    <Button type="submit" loading={saving}>Create Plan</Button>
                    <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Records */}
        <GlassCard hover={false} className="overflow-hidden">
          {loading ? (
            <div className="space-y-1 p-4">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 rounded-xl shimmer" />)}</div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Beef className="mb-3 h-12 w-12 text-white/20" />
              <p className="text-sm text-white/40">No qurbani plans yet</p>
              <Button className="mt-4" size="sm" onClick={() => setShowForm(true)}>Create your first plan</Button>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {records.map((rec) => {
                const pct = progressPct(rec);
                return (
                  <motion.div key={rec.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="px-6 py-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/10">
                          <Beef size={16} className="text-amber-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-white">{rec.animal_type}</p>
                            <Badge variant={rec.is_complete ? "success" : "warning"}>{rec.is_complete ? "Complete" : rec.target_year}</Badge>
                          </div>
                          <p className="text-xs text-white/40">{formatCurrency(rec.saved_amount, rec.currency)} of {formatCurrency(rec.target_amount, rec.currency)}</p>
                        </div>
                      </div>
                      {!rec.is_complete && (
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<Banknote size={12} />}
                          onClick={() => setShowContribute(showContribute === rec.id ? null : rec.id)}
                        >
                          Contribute
                        </Button>
                      )}
                    </div>
                    <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={`h-full rounded-full ${pct >= 100 ? "bg-emerald-500" : "bg-amber-500"}`}
                      />
                    </div>
                    <AnimatePresence>
                      {showContribute === rec.id && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="flex gap-2">
                          <input
                            type="number"
                            value={contributeAmt}
                            onChange={(e) => setContributeAmt(e.target.value)}
                            placeholder="Amount"
                            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-violet-500/50 focus:outline-none"
                          />
                          <Button size="sm" onClick={() => contribute(rec.id)}>Add</Button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
