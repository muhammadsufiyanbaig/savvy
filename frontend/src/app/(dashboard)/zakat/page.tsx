"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Scale, Plus, X, CheckCircle2, Clock } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { zakatApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

interface ZakatRecord {
  id: number;
  hijri_year?: string;
  total_assets: number;
  total_liabilities: number;
  zakatable_wealth: number;
  zakat_due: number;
  amount_paid: number;
  is_paid: boolean;
  currency: string;
  calculated_at: string;
}

interface ZakatSummary {
  total_calculated: number;
  total_zakat_due: number;
  total_paid: number;
  outstanding: number;
}

interface NisabData {
  nisab_gold: number;
  nisab_silver: number;
  currency: string;
  note: string;
}

const schema = z.object({
  total_assets: z.coerce.number().positive("Must be positive"),
  total_liabilities: z.coerce.number().min(0).default(0),
  currency: z.string().default("USD"),
  hijri_year: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export default function ZakatPage() {
  const [records, setRecords] = useState<ZakatRecord[]>([]);
  const [summary, setSummary] = useState<ZakatSummary | null>(null);
  const [nisab, setNisab] = useState<NisabData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [calculating, setCalculating] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "USD", total_liabilities: 0 },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [recs, nisabData] = await Promise.allSettled([
        zakatApi.list(),
        zakatApi.nisab("USD"),
      ]);
      if (recs.status === "fulfilled") {
        setRecords(recs.value.data?.records || []);
        setSummary(recs.value.data?.summary || null);
      }
      if (nisabData.status === "fulfilled") setNisab(nisabData.value.data);
    } catch { }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onCalculate = async (data: FormData) => {
    setCalculating(true);
    try {
      await zakatApi.calculate(data);
      toast.success("Zakat calculated and saved!");
      reset();
      setShowForm(false);
      fetchData();
    } catch { toast.error("Failed to calculate zakat"); }
    finally { setCalculating(false); }
  };

  const markPaid = async (id: number, zakat_due: number) => {
    try {
      await zakatApi.updatePayment(id, { amount_paid: zakat_due, is_paid: true });
      toast.success("Marked as paid!");
      fetchData();
    } catch { toast.error("Failed to update payment"); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Zakat" subtitle="Calculate and track your annual zakat obligation" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Nisab info */}
        {nisab && (
          <GlassCard className="p-5 border-amber-500/15 bg-amber-500/5" hover={false}>
            <div className="flex items-start gap-3">
              <Scale size={18} className="shrink-0 mt-0.5 text-amber-400" />
              <div>
                <p className="text-sm font-medium text-white">Current Nisab Threshold</p>
                <p className="mt-1 text-xs text-white/50">
                  Gold: <span className="text-amber-300">{formatCurrency(nisab.nisab_gold)}</span>
                  {" · "}
                  Silver: <span className="text-amber-300">{formatCurrency(nisab.nisab_silver)}</span>
                  {" · "}{nisab.note}
                </p>
              </div>
            </div>
          </GlassCard>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Total Calculated", value: String(summary.total_calculated), highlight: false },
              { label: "Total Due", value: formatCurrency(summary.total_zakat_due), highlight: false },
              { label: "Total Paid", value: formatCurrency(summary.total_paid), highlight: false },
              { label: "Outstanding", value: formatCurrency(summary.outstanding), highlight: summary.outstanding > 0 },
            ].map(({ label, value, highlight }) => (
              <GlassCard key={label} className="p-4" hover={false}>
                <p className="text-xs text-white/40 mb-1">{label}</p>
                <p className={`text-xl font-bold ${highlight ? "text-rose-400" : "text-white"}`}>
                  {value}
                </p>
              </GlassCard>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Zakat Records</h2>
          <Button icon={<Plus size={14} />} onClick={() => setShowForm(true)} size="sm">Calculate Zakat</Button>
        </div>

        {/* Calculation form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <GlassCard className="p-6" hover={false}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">New Zakat Calculation</h3>
                  <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white"><X size={16} /></button>
                </div>
                <form onSubmit={handleSubmit(onCalculate)} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input label="Total Assets ($)" type="number" step="0.01" placeholder="e.g. 10000" error={errors.total_assets?.message} {...register("total_assets")} />
                    <Input label="Total Liabilities ($)" type="number" step="0.01" placeholder="e.g. 2000" error={errors.total_liabilities?.message} {...register("total_liabilities")} />
                    <Input label="Hijri Year" placeholder="e.g. 1446" {...register("hijri_year")} />
                  </div>
                  <p className="text-xs text-white/30">Zakat = 2.5% of (Assets − Liabilities) if above Nisab</p>
                  <div className="flex gap-3">
                    <Button type="submit" loading={calculating}>Calculate & Save</Button>
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
            <div className="space-y-1 p-4">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-20 rounded-xl shimmer" />)}</div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Scale className="mb-3 h-12 w-12 text-white/20" />
              <p className="text-sm text-white/40">No zakat records yet</p>
              <Button className="mt-4" size="sm" onClick={() => setShowForm(true)}>Calculate your first zakat</Button>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {records.map((rec) => (
                <motion.div key={rec.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-4 px-6 py-4">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${rec.is_paid ? "border-emerald-500/20 bg-emerald-500/10" : "border-amber-500/20 bg-amber-500/10"}`}>
                    {rec.is_paid ? <CheckCircle2 size={16} className="text-emerald-400" /> : <Clock size={16} className="text-amber-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-white">
                        Zakat {rec.hijri_year ? `· ${rec.hijri_year}H` : ""}
                      </p>
                      <Badge variant={rec.is_paid ? "success" : "warning"}>{rec.is_paid ? "Paid" : "Pending"}</Badge>
                    </div>
                    <p className="text-xs text-white/40 mt-0.5">
                      Assets: {formatCurrency(rec.total_assets)} · Liabilities: {formatCurrency(rec.total_liabilities)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-amber-400">{formatCurrency(rec.zakat_due)}</p>
                    {!rec.is_paid && (
                      <button
                        onClick={() => markPaid(rec.id, rec.zakat_due)}
                        className="mt-1 text-xs text-violet-400 hover:text-violet-300"
                      >
                        Mark paid
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
