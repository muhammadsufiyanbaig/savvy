"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Minus, AlertTriangle, Trash2, Edit2 } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { liabilityApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

const LIA_CATEGORIES = [
  { value: "personal_loan",  label: "Personal Loan"  },
  { value: "car_loan",       label: "Car Loan"        },
  { value: "home_loan",      label: "Home Loan"       },
  { value: "student_loan",   label: "Student Loan"    },
  { value: "credit_card",    label: "Credit Card"     },
  { value: "business_loan",  label: "Business Loan"   },
  { value: "family_loan",    label: "Family Loan"     },
  { value: "other",          label: "Other"           },
] as const;

const COLORS = ["#7c3aed","#0891b2","#059669","#d97706","#db2777","#ea580c","#6366f1","#64748b"];

const schema = z.object({
  name:               z.string().min(1, "Required"),
  category:           z.string().min(1),
  currency:           z.string().default("USD"),
  original_amount:    z.coerce.number().positive("Must be > 0"),
  amount_owed:        z.coerce.number().nonnegative(),
  monthly_payment:    z.coerce.number().nonnegative().optional(),
  lender:             z.string().optional(),
  is_interest_bearing:z.boolean().default(false),
  notes:              z.string().optional(),
});
type FormData = z.infer<typeof schema>;

interface Liability { id: number; name: string; category: string; currency: string; original_amount: number; amount_owed: number; monthly_payment?: number; lender?: string; is_interest_bearing: boolean; notes?: string; }
interface NetWorth { total_assets: number; total_liabilities: number; net_worth: number; assets_by_category: { category: string; total: number }[]; liabilities_by_category: { category: string; total: number }[]; riba_debt_total: number; halal_debt_total: number; }

export default function NetWorthPage() {
  const [liabilities, setLiabilities] = useState<Liability[]>([]);
  const [netWorth,    setNetWorth]    = useState<NetWorth | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [showForm,    setShowForm]    = useState(false);
  const [editing,     setEditing]     = useState<Liability | null>(null);
  const [saving,      setSaving]      = useState(false);

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "USD", is_interest_bearing: false },
  });

  const load = async () => {
    try {
      const [liaRes, nwRes] = await Promise.allSettled([liabilityApi.list(), liabilityApi.netWorth()]);
      if (liaRes.status === "fulfilled") setLiabilities(liaRes.value.data.liabilities ?? []);
      if (nwRes.status  === "fulfilled") setNetWorth(nwRes.value.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); reset({ currency: "USD", is_interest_bearing: false }); setShowForm(true); };
  const openEdit   = (l: Liability) => {
    setEditing(l);
    reset({ name: l.name, category: l.category, currency: l.currency, original_amount: l.original_amount, amount_owed: l.amount_owed, monthly_payment: l.monthly_payment ?? 0, lender: l.lender ?? "", is_interest_bearing: l.is_interest_bearing, notes: l.notes ?? "" });
    setShowForm(true);
  };

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      editing ? await liabilityApi.update(editing.id, data) : await liabilityApi.create(data);
      toast.success(editing ? "Updated!" : "Liability added.");
      setShowForm(false); load();
    } catch { toast.error("Failed to save"); } finally { setSaving(false); }
  };

  const onDelete = async (id: number) => {
    if (!confirm("Delete this liability?")) return;
    await liabilityApi.delete(id); toast.success("Deleted"); load();
  };

  const nw = netWorth;
  const positive = nw ? nw.net_worth >= 0 : true;

  const combinedBar = nw ? [
    { name: "Assets",      value: nw.total_assets      },
    { name: "Liabilities", value: nw.total_liabilities },
    { name: "Net Worth",   value: Math.abs(nw.net_worth) },
  ] : [];

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Net Worth" subtitle="Assets minus liabilities" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Big number */}
        {nw && (
          <GlassCard className="p-6 text-center" hover={false}>
            <p className="text-xs text-white/40 mb-2">Total Net Worth</p>
            <p className={`text-4xl font-bold ${positive ? "text-emerald-400" : "text-rose-400"}`}>
              {positive ? "" : "−"}{formatCurrency(Math.abs(nw.net_worth))}
            </p>
            <div className="flex justify-center gap-8 mt-4">
              <div>
                <p className="text-xs text-white/40">Total Assets</p>
                <p className="text-lg font-semibold text-cyan-400">{formatCurrency(nw.total_assets)}</p>
              </div>
              <div>
                <p className="text-xs text-white/40">Total Liabilities</p>
                <p className="text-lg font-semibold text-rose-400">{formatCurrency(nw.total_liabilities)}</p>
              </div>
            </div>
            {nw.riba_debt_total > 0 && (
              <div className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-4 py-2 text-xs text-amber-400">
                <AlertTriangle size={13} />
                Interest-bearing (riba) debt: {formatCurrency(nw.riba_debt_total)}
              </div>
            )}
          </GlassCard>
        )}

        <div className="flex justify-end">
          <Button icon={<Plus size={14} />} onClick={openCreate} size="sm">Add Liability</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Summary bar */}
          {nw && (
            <GlassCard className="p-6" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">Overview</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={combinedBar} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }} axisLine={false} tickLine={false} width={80} />
                  <Tooltip contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {combinedBar.map((entry, i) => (
                      <Cell key={i} fill={i === 0 ? "#0891b2" : i === 1 ? "#db2777" : positive ? "#059669" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Liabilities by category pie */}
          {nw && nw.liabilities_by_category.length > 0 && (
            <GlassCard className="p-6" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">Debt Breakdown</h3>
              <div className="flex gap-4 items-center">
                <ResponsiveContainer width={130} height={130}>
                  <PieChart>
                    <Pie data={nw.liabilities_by_category} dataKey="total" nameKey="category" cx="50%" cy="50%" innerRadius={38} outerRadius={58} paddingAngle={3}>
                      {nw.liabilities_by_category.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} formatter={(v: number) => formatCurrency(v)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-1.5">
                  {nw.liabilities_by_category.map((c, i) => (
                    <div key={c.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span className="text-xs text-white/60 capitalize">{c.category.replace(/_/g," ")}</span>
                      </div>
                      <span className="text-xs font-medium text-white">{formatCurrency(c.total)}</span>
                    </div>
                  ))}
                  {nw.halal_debt_total > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/8 flex justify-between text-xs">
                      <span className="text-emerald-400">Halal debt</span>
                      <span className="text-emerald-400">{formatCurrency(nw.halal_debt_total)}</span>
                    </div>
                  )}
                </div>
              </div>
            </GlassCard>
          )}
        </div>

        {/* Liabilities list */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-white/60 px-1">Liabilities</h3>
          {loading ? Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-16 rounded-2xl bg-white/5 animate-pulse" />) :
          liabilities.length === 0 ? (
            <GlassCard className="p-10 text-center" hover={false}>
              <Minus size={36} className="mx-auto text-white/20 mb-3" />
              <p className="text-white/40 text-sm">No liabilities added. Debt-free!</p>
            </GlassCard>
          ) : liabilities.map(l => (
            <GlassCard key={l.id} className="p-4" hover={false}>
              <div className="flex items-center gap-4">
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${l.is_interest_bearing ? "bg-amber-500/15" : "bg-white/5"}`}>
                  {l.is_interest_bearing ? <AlertTriangle size={16} className="text-amber-400" /> : <Minus size={16} className="text-white/40" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-white">{l.name}</p>
                    {l.is_interest_bearing && <span className="text-xs px-1.5 py-0.5 rounded-md bg-amber-500/15 text-amber-400">Riba</span>}
                  </div>
                  <p className="text-xs text-white/40">{l.category.replace(/_/g," ")} {l.lender ? `· ${l.lender}` : ""}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-rose-400">{formatCurrency(l.amount_owed)}</p>
                  {l.monthly_payment ? <p className="text-xs text-white/30">{formatCurrency(l.monthly_payment)}/mo</p> : null}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(l)} className="text-white/30 hover:text-white p-1"><Edit2 size={14} /></button>
                  <button onClick={() => onDelete(l.id)} className="text-white/30 hover:text-rose-400 p-1"><Trash2 size={14} /></button>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={e => e.target === e.currentTarget && setShowForm(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#1a1528] shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-5 border-b border-white/8 sticky top-0 bg-[#1a1528]">
                <h2 className="text-sm font-semibold text-white">{editing ? "Edit Liability" : "Add Liability"}</h2>
                <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white"><X size={16} /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
                <Input label="Name *" error={errors.name?.message} {...register("name")} placeholder="Car loan, Mortgage..." />
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5">Category *</label>
                  <select {...register("category")} className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500">
                    <option value="">Select</option>
                    {LIA_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Original Amount *" type="number" step="any" error={errors.original_amount?.message} {...register("original_amount")} placeholder="0.00" />
                  <Input label="Amount Owed *" type="number" step="any" error={errors.amount_owed?.message} {...register("amount_owed")} placeholder="0.00" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Monthly Payment" type="number" step="any" {...register("monthly_payment")} placeholder="0.00" />
                  <Input label="Currency" {...register("currency")} placeholder="USD" />
                </div>
                <Input label="Lender / Institution" {...register("lender")} placeholder="Bank name..." />
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" {...register("is_interest_bearing")} className="w-4 h-4 rounded border-white/20 bg-white/5 accent-amber-500" />
                  <span className="text-sm text-amber-400">Interest-bearing (Riba)</span>
                </label>
                <Input label="Notes" {...register("notes")} placeholder="Optional..." />
                <div className="flex gap-3 pt-1">
                  <Button type="button" variant="secondary" onClick={() => setShowForm(false)} className="flex-1">Cancel</Button>
                  <Button type="submit" loading={saving} className="flex-1">{editing ? "Update" : "Add"}</Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
