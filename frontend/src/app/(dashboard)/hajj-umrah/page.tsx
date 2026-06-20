"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Moon, Calendar, Target, Trash2, Edit2, ChevronDown, ChevronUp } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { hajjUmrahApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

const PACKAGE_TYPES  = ["economy","standard","premium","vip"] as const;
const DEPARTURE_CITIES = ["Karachi","Lahore","Islamabad","Dubai","London","New York","Toronto","Other"] as const;

const planSchema = z.object({
  plan_type:      z.enum(["hajj","umrah"]),
  title:          z.string().min(1),
  target_year:    z.coerce.number().int().min(new Date().getFullYear()),
  num_persons:    z.coerce.number().int().min(1).max(50),
  departure_city: z.string().min(1),
  package_type:   z.enum(PACKAGE_TYPES),
  estimated_cost: z.coerce.number().positive(),
  current_amount: z.coerce.number().nonnegative(),
  currency:       z.string().default("USD"),
  notes:          z.string().optional(),
});
type PlanForm = z.infer<typeof planSchema>;

const depositSchema = z.object({ amount: z.coerce.number().positive(), note: z.string().optional(), date: z.string().min(1) });
type DepositForm = z.infer<typeof depositSchema>;

interface Plan { id: number; plan_type: "hajj" | "umrah"; title: string; target_year: number; num_persons: number; departure_city: string; package_type: string; estimated_cost: number; current_amount: number; currency: string; notes?: string; progress_pct: number; remaining_amount: number; months_remaining: number; monthly_target: number; }
interface Deposit { id: number; amount: number; note?: string; date: string; }

function PlanCard({ plan, onEdit, onDelete, onRefresh }: { plan: Plan; onEdit: () => void; onDelete: () => void; onRefresh: () => void; }) {
  const [expanded, setExpanded] = useState(false);
  const [deposits, setDeposits] = useState<Deposit[]>([]);
  const [showDeposit, setShowDeposit] = useState(false);
  const [saving, setSaving] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<DepositForm>({
    resolver: zodResolver(depositSchema),
    defaultValues: { date: new Date().toISOString().split("T")[0] },
  });

  const loadDeposits = async () => {
    const res = await hajjUmrahApi.deposits(plan.id);
    setDeposits(res.data.deposits ?? []);
  };

  const onExpand = () => { setExpanded(v => !v); if (!expanded) loadDeposits(); };

  const onDeposit = async (data: DepositForm) => {
    setSaving(true);
    try {
      await hajjUmrahApi.deposit(plan.id, data);
      toast.success("Deposit recorded!");
      setShowDeposit(false);
      reset({ date: new Date().toISOString().split("T")[0] });
      await loadDeposits();
      onRefresh();
    } catch { toast.error("Failed"); } finally { setSaving(false); }
  };

  const pct = Math.min(plan.progress_pct, 100);
  const color = pct >= 80 ? "#10b981" : pct >= 50 ? "#0891b2" : "#7c3aed";

  return (
    <GlassCard className="overflow-hidden" hover={false}>
      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15">
            <Moon size={18} className="text-violet-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-semibold text-white">{plan.title}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${plan.plan_type === "hajj" ? "bg-amber-500/20 text-amber-400" : "bg-cyan-500/20 text-cyan-400"}`}>
                {plan.plan_type === "hajj" ? "Hajj" : "Umrah"}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/8 text-white/50 capitalize">{plan.package_type}</span>
            </div>
            <p className="text-xs text-white/40 mt-0.5">{plan.departure_city} · {plan.num_persons} person{plan.num_persons > 1 ? "s" : ""} · {plan.target_year}</p>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={onEdit} className="text-white/30 hover:text-white p-1"><Edit2 size={13} /></button>
            <button onClick={onDelete} className="text-white/30 hover:text-rose-400 p-1"><Trash2 size={13} /></button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-white/50">{formatCurrency(plan.current_amount)} saved</span>
            <span className="font-semibold" style={{ color }}>{pct.toFixed(0)}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/8 overflow-hidden">
            <motion.div className="h-full rounded-full" style={{ backgroundColor: color }} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: "easeOut" }} />
          </div>
          <div className="flex justify-between text-xs text-white/40">
            <span>Goal: {formatCurrency(plan.estimated_cost)}</span>
            <span>{formatCurrency(plan.remaining_amount)} remaining</span>
          </div>
        </div>

        {/* Stats row */}
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-white/5 p-3 text-center">
            <p className="text-xs text-white/40">Months Left</p>
            <p className="text-lg font-bold text-white">{plan.months_remaining > 0 ? plan.months_remaining : 0}</p>
          </div>
          <div className="rounded-xl bg-white/5 p-3 text-center">
            <p className="text-xs text-white/40">Monthly Target</p>
            <p className="text-lg font-bold text-cyan-400">{plan.months_remaining > 0 ? formatCurrency(plan.monthly_target) : "—"}</p>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button size="sm" variant="secondary" onClick={() => { setShowDeposit(v => !v); }} className="flex-1">Add Deposit</Button>
          <button onClick={onExpand} className="flex items-center gap-1 text-xs text-white/30 hover:text-white px-3">
            History {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {/* Inline deposit form */}
        <AnimatePresence>
          {showDeposit && (
            <motion.form initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
              onSubmit={handleSubmit(onDeposit)} className="overflow-hidden mt-3 space-y-3 border-t border-white/8 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <Input label="Amount *" type="number" step="any" error={errors.amount?.message} {...register("amount")} placeholder="0.00" />
                <Input label="Date *" type="date" error={errors.date?.message} {...register("date")} />
              </div>
              <Input label="Note" {...register("note")} placeholder="Monthly savings..." />
              <div className="flex gap-2">
                <Button type="button" variant="secondary" size="sm" onClick={() => setShowDeposit(false)} className="flex-1">Cancel</Button>
                <Button type="submit" size="sm" loading={saving} className="flex-1">Deposit</Button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>
      </div>

      {/* Deposit history */}
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-white/8">
            <div className="p-4 space-y-2">
              {deposits.length === 0 ? (
                <p className="text-xs text-white/30 text-center py-3">No deposits yet.</p>
              ) : deposits.map(d => (
                <div key={d.id} className="flex items-center justify-between text-xs">
                  <span className="text-white/50">{d.date}{d.note ? ` · ${d.note}` : ""}</span>
                  <span className="font-medium text-emerald-400">+{formatCurrency(d.amount)}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}

export default function HajjUmrahPage() {
  const [plans,    setPlans]    = useState<Plan[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing,  setEditing]  = useState<Plan | null>(null);
  const [saving,   setSaving]   = useState(false);

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<PlanForm>({
    resolver: zodResolver(planSchema),
    defaultValues: { currency: "USD", num_persons: 1, plan_type: "hajj", target_year: new Date().getFullYear() + 1 },
  });

  const load = async () => {
    try {
      const res = await hajjUmrahApi.list();
      setPlans(res.data.plans ?? []);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); reset({ currency: "USD", num_persons: 1, plan_type: "hajj", target_year: new Date().getFullYear() + 1 }); setShowForm(true); };
  const openEdit   = (p: Plan) => {
    setEditing(p);
    reset({ plan_type: p.plan_type, title: p.title, target_year: p.target_year, num_persons: p.num_persons, departure_city: p.departure_city, package_type: p.package_type as PlanForm["package_type"], estimated_cost: p.estimated_cost, current_amount: p.current_amount, currency: p.currency, notes: p.notes ?? "" });
    setShowForm(true);
  };
  const onDelete = async (id: number) => { if (!confirm("Delete this plan?")) return; await hajjUmrahApi.delete(id); toast.success("Deleted"); load(); };
  const onSubmit = async (data: PlanForm) => {
    setSaving(true);
    try {
      editing ? await hajjUmrahApi.update(editing.id, data) : await hajjUmrahApi.create(data);
      toast.success(editing ? "Updated!" : "Plan created!");
      setShowForm(false); load();
    } catch { toast.error("Failed"); } finally { setSaving(false); }
  };

  const totalSaved   = plans.reduce((s, p) => s + p.current_amount, 0);
  const totalTarget  = plans.reduce((s, p) => s + p.estimated_cost, 0);

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Hajj / Umrah" subtitle="Plan your sacred journey" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {plans.length > 0 && (
          <div className="grid grid-cols-2 gap-4">
            <GlassCard className="p-4" hover={false}>
              <p className="text-xs text-white/40">Total Saved</p>
              <p className="text-xl font-bold text-emerald-400">{formatCurrency(totalSaved)}</p>
            </GlassCard>
            <GlassCard className="p-4" hover={false}>
              <p className="text-xs text-white/40">Total Goal</p>
              <p className="text-xl font-bold text-cyan-400">{formatCurrency(totalTarget)}</p>
            </GlassCard>
          </div>
        )}

        <div className="flex justify-end">
          <Button icon={<Plus size={14} />} onClick={openCreate} size="sm">New Plan</Button>
        </div>

        {loading ? Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-56 rounded-2xl bg-white/5 animate-pulse" />) :
        plans.length === 0 ? (
          <GlassCard className="p-12 text-center" hover={false}>
            <Moon size={40} className="mx-auto text-white/20 mb-3" />
            <p className="text-white/40 text-sm">No plans yet. Start saving for your journey.</p>
          </GlassCard>
        ) : plans.map(p => (
          <PlanCard key={p.id} plan={p} onEdit={() => openEdit(p)} onDelete={() => onDelete(p.id)} onRefresh={load} />
        ))}
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={e => e.target === e.currentTarget && setShowForm(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#1a1528] shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-5 border-b border-white/8 sticky top-0 bg-[#1a1528]">
                <h2 className="text-sm font-semibold text-white">{editing ? "Edit Plan" : "New Plan"}</h2>
                <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white"><X size={16} /></button>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5">Type *</label>
                  <div className="grid grid-cols-2 gap-2">
                    {(["hajj","umrah"] as const).map(t => (
                      <label key={t} className={`flex items-center justify-center gap-2 p-3 rounded-xl cursor-pointer border transition-all ${watch("plan_type") === t ? "border-violet-500 bg-violet-500/15 text-violet-300" : "border-white/10 bg-white/5 text-white/50"}`}>
                        <input type="radio" value={t} {...register("plan_type")} className="sr-only" />
                        <Moon size={14} />
                        <span className="text-sm font-medium capitalize">{t}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <Input label="Plan Title *" error={errors.title?.message} {...register("title")} placeholder="Family Hajj 2027" />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Target Year *" type="number" error={errors.target_year?.message} {...register("target_year")} />
                  <Input label="Persons *" type="number" error={errors.num_persons?.message} {...register("num_persons")} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-white/60 mb-1.5">Package *</label>
                    <select {...register("package_type")} className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500">
                      {PACKAGE_TYPES.map(p => <option key={p} value={p} className="capitalize">{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-white/60 mb-1.5">Departure City *</label>
                    <select {...register("departure_city")} className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500">
                      <option value="">Select</option>
                      {DEPARTURE_CITIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Estimated Cost *" type="number" step="any" error={errors.estimated_cost?.message} {...register("estimated_cost")} placeholder="0.00" />
                  <Input label="Amount Saved" type="number" step="any" {...register("current_amount")} placeholder="0.00" />
                </div>
                <Input label="Currency" {...register("currency")} placeholder="USD" />
                <Input label="Notes" {...register("notes")} placeholder="Optional..." />
                <div className="flex gap-3 pt-1">
                  <Button type="button" variant="secondary" onClick={() => setShowForm(false)} className="flex-1">Cancel</Button>
                  <Button type="submit" loading={saving} className="flex-1">{editing ? "Update" : "Create"}</Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
