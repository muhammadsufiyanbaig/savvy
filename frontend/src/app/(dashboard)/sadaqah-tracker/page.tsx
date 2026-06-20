"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Heart, Trash2, Edit2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { sadaqahApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

const CATEGORIES = [
  { value: "sadaqah",        label: "Sadaqah (Voluntary)",  color: "#7c3aed" },
  { value: "zakat_fitrah",   label: "Zakat al-Fitr",        color: "#0891b2" },
  { value: "lillah",         label: "Lillah",               color: "#059669" },
  { value: "waqf",           label: "Waqf (Endowment)",     color: "#d97706" },
  { value: "fidya",          label: "Fidya",                color: "#db2777" },
  { value: "kaffarah",       label: "Kaffarah",             color: "#ea580c" },
  { value: "general_charity","label": "General Charity",    color: "#6366f1" },
] as const;

const PIE_COLORS = CATEGORIES.map(c => c.color);

const schema = z.object({
  amount:    z.coerce.number().positive("Must be > 0"),
  currency:  z.string().default("USD"),
  category:  z.string().min(1),
  recipient: z.string().optional(),
  date:      z.string().min(1),
  notes:     z.string().optional(),
});
type FormData = z.infer<typeof schema>;

interface Record { id: number; amount: number; currency: string; category: string; recipient?: string; date: string; notes?: string; }
interface Summary { total_all_time: number; total_this_year: number; total_this_month: number; by_category: { category: string; label: string; total: number; count: number }[]; monthly_trend: { month: string; total: number }[]; }

export default function SadaqahPage() {
  const [records,  setRecords]  = useState<Record[]>([]);
  const [summary,  setSummary]  = useState<Summary | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing,  setEditing]  = useState<Record | null>(null);
  const [saving,   setSaving]   = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "USD", date: new Date().toISOString().split("T")[0] },
  });

  const load = async () => {
    try {
      const [listRes, sumRes] = await Promise.allSettled([sadaqahApi.list(), sadaqahApi.summary()]);
      if (listRes.status === "fulfilled") setRecords(listRes.value.data.records ?? []);
      if (sumRes.status  === "fulfilled") setSummary(sumRes.value.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); reset({ currency: "USD", date: new Date().toISOString().split("T")[0] }); setShowForm(true); };
  const openEdit   = (r: Record) => { setEditing(r); reset({ amount: r.amount, currency: r.currency, category: r.category, recipient: r.recipient ?? "", date: r.date, notes: r.notes ?? "" }); setShowForm(true); };

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      editing ? await sadaqahApi.update(editing.id, data) : await sadaqahApi.create(data);
      toast.success(editing ? "Updated!" : "Recorded! JazakAllah khair.");
      setShowForm(false); load();
    } catch { toast.error("Failed to save"); } finally { setSaving(false); }
  };

  const onDelete = async (id: number) => {
    if (!confirm("Delete this record?")) return;
    await sadaqahApi.delete(id); toast.success("Deleted"); load();
  };

  const getCatLabel = (val: string) => CATEGORIES.find(c => c.value === val)?.label ?? val;
  const getCatColor = (val: string) => CATEGORIES.find(c => c.value === val)?.color ?? "#7c3aed";

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Sadaqah Tracker" subtitle="Track your charitable giving" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { label: "All Time",    value: formatCurrency(summary.total_all_time),   color: "text-violet-400" },
              { label: "This Year",   value: formatCurrency(summary.total_this_year),  color: "text-cyan-400"   },
              { label: "This Month",  value: formatCurrency(summary.total_this_month), color: "text-emerald-400"},
            ].map(c => (
              <GlassCard key={c.label} className="p-4" hover={false}>
                <p className="text-xs text-white/40 mb-1">{c.label}</p>
                <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
              </GlassCard>
            ))}
          </div>
        )}

        <div className="flex justify-end">
          <Button icon={<Plus size={14} />} onClick={openCreate} size="sm">Add Donation</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly trend */}
          {summary && summary.monthly_trend.length > 0 && (
            <GlassCard className="p-6" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">Monthly Giving</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={summary.monthly_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} formatter={(v: number) => [formatCurrency(v), "Donated"]} />
                  <Bar dataKey="total" fill="#7c3aed" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Category breakdown */}
          {summary && summary.by_category.length > 0 && (
            <GlassCard className="p-6" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">By Category</h3>
              <div className="flex gap-4 items-center">
                <ResponsiveContainer width={140} height={140}>
                  <PieChart>
                    <Pie data={summary.by_category} dataKey="total" nameKey="label" cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={3}>
                      {summary.by_category.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} formatter={(v: number) => formatCurrency(v)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-2">
                  {summary.by_category.map((c, i) => (
                    <div key={c.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="text-xs text-white/60">{c.label}</span>
                      </div>
                      <span className="text-xs font-medium text-white">{formatCurrency(c.total)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          )}
        </div>

        {/* Records list */}
        <div className="space-y-2">
          {loading ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 rounded-2xl bg-white/5 animate-pulse" />) :
          records.length === 0 ? (
            <GlassCard className="p-12 text-center" hover={false}>
              <Heart size={40} className="mx-auto text-white/20 mb-3" />
              <p className="text-white/40 text-sm">No donations recorded yet.</p>
            </GlassCard>
          ) : records.map(r => (
            <GlassCard key={r.id} className="p-4" hover={false}>
              <div className="flex items-center gap-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style={{ backgroundColor: `${getCatColor(r.category)}22` }}>
                  <Heart size={16} style={{ color: getCatColor(r.category) }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{getCatLabel(r.category)}</p>
                  <p className="text-xs text-white/40">{r.recipient ? `→ ${r.recipient} · ` : ""}{r.date}</p>
                </div>
                <p className="text-sm font-bold text-emerald-400">{formatCurrency(r.amount)}</p>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(r)} className="text-white/30 hover:text-white p-1"><Edit2 size={14} /></button>
                  <button onClick={() => onDelete(r.id)} className="text-white/30 hover:text-rose-400 p-1"><Trash2 size={14} /></button>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>

      {/* Form modal */}
      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={e => e.target === e.currentTarget && setShowForm(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#1a1528] shadow-2xl">
              <div className="flex items-center justify-between p-5 border-b border-white/8">
                <h2 className="text-sm font-semibold text-white">{editing ? "Edit Donation" : "Record Donation"}</h2>
                <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white"><X size={16} /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Amount *" type="number" step="any" error={errors.amount?.message} {...register("amount")} placeholder="0.00" />
                  <Input label="Currency" {...register("currency")} placeholder="USD" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5">Category *</label>
                  <select {...register("category")} className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500">
                    <option value="">Select category</option>
                    {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
                <Input label="Recipient / Organisation" {...register("recipient")} placeholder="JDC, Edhi, local masjid..." />
                <Input label="Date *" type="date" error={errors.date?.message} {...register("date")} />
                <Input label="Notes" {...register("notes")} placeholder="Optional notes..." />
                <div className="flex gap-3 pt-1">
                  <Button type="button" variant="secondary" onClick={() => setShowForm(false)} className="flex-1">Cancel</Button>
                  <Button type="submit" loading={saving} className="flex-1">{editing ? "Update" : "Record"}</Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
