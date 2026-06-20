"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, PiggyBank, ArrowDownCircle, ArrowUpCircle, Target } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { savingsApi } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import toast from "react-hot-toast";

const goalSchema = z.object({
  name: z.string().min(1),
  goal_type: z.string().default("emergency"),
  target_amount: z.string().refine((v) => +v > 0),
  currency: z.string().default("USD"),
  target_date: z.string().optional(),
  description: z.string().optional(),
});
const txSchema = z.object({ amount: z.string().refine((v) => +v > 0), description: z.string().optional() });

type GoalForm = z.infer<typeof goalSchema>;
type TxForm = z.infer<typeof txSchema>;

const GOAL_TYPES = ["emergency", "vacation", "education", "home", "car", "retirement", "wedding", "eid", "qurbani", "zakat", "other"];

export default function SavingsPage() {
  const [goals, setGoals] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [txModal, setTxModal] = useState<{ id: number; type: "deposit" | "withdraw" } | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<GoalForm>({
    resolver: zodResolver(goalSchema),
    defaultValues: { currency: "USD", goal_type: "emergency" },
  });
  const txForm = useForm<TxForm>({ resolver: zodResolver(txSchema) });

  const fetchGoals = useCallback(async () => {
    setLoading(true);
    try {
      const res = await savingsApi.list();
      setGoals(res.data?.goals || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchGoals(); }, [fetchGoals]);

  const onCreateGoal = async (data: GoalForm) => {
    setSubmitting(true);
    try {
      await savingsApi.create({ ...data, target_amount: parseFloat(data.target_amount) });
      toast.success("Savings goal created!");
      reset(); setShowForm(false); fetchGoals();
    } catch { toast.error("Failed to create goal"); }
    finally { setSubmitting(false); }
  };

  const onTransaction = async (data: TxForm) => {
    if (!txModal) return;
    try {
      if (txModal.type === "deposit") await savingsApi.deposit(txModal.id, { amount: parseFloat(data.amount), description: data.description });
      else await savingsApi.withdraw(txModal.id, { amount: parseFloat(data.amount), description: data.description });
      toast.success(txModal.type === "deposit" ? "Deposited!" : "Withdrawn!");
      setTxModal(null); txForm.reset(); fetchGoals();
    } catch { toast.error("Transaction failed"); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Savings Goals" subtitle={`${goals.length} active goals`} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        <div className="flex justify-end">
          <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>New Goal</Button>
        </div>

        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
              <GlassCard className="p-6" hover={false}>
                <h3 className="mb-4 text-sm font-semibold text-white">Create Savings Goal</h3>
                <form onSubmit={handleSubmit(onCreateGoal)} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Input label="Goal Name" placeholder="Emergency Fund" error={errors.name?.message} {...register("name")} />
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-white/70">Goal Type</label>
                    <select className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-violet-500/60 focus:outline-none" {...register("goal_type")}>
                      {GOAL_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                    </select>
                  </div>
                  <Input label="Target Amount ($)" placeholder="10000" error={errors.target_amount?.message} {...register("target_amount")} />
                  <Input label="Target Date" type="date" {...register("target_date")} />
                  <Input label="Description" placeholder="Optional" {...register("description")} />
                  <div className="sm:col-span-2 lg:col-span-3 flex gap-3">
                    <Button type="submit" loading={submitting}>Create Goal</Button>
                    <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-56 rounded-2xl shimmer" />)}
          </div>
        ) : goals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <PiggyBank className="mb-3 h-12 w-12 text-white/20" />
            <p className="text-sm text-white/40">No savings goals yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {goals.map((g) => {
              const pct = Math.min(100, Math.round(((g.current_amount as number) / (g.target_amount as number)) * 100));
              return (
                <motion.div key={g.id as number} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-white/8 bg-white/5 p-5 backdrop-blur-xl hover:bg-white/8 transition-all">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="font-semibold text-white">{g.name as string}</p>
                      <p className="text-xs text-white/40 mt-0.5">{g.goal_type as string} · {g.target_date ? formatDate(g.target_date as string) : "No deadline"}</p>
                    </div>
                    <Badge variant={pct >= 100 ? "success" : g.status === "active" ? "info" : "default"}>
                      {pct >= 100 ? "Complete!" : g.status as string}
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs text-white/50 mb-1.5">
                        <span>{formatCurrency(g.current_amount as number)}</span>
                        <span>of {formatCurrency(g.target_amount as number)}</span>
                      </div>
                      <div className="h-3 rounded-full bg-white/10 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          className="h-3 rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                        />
                      </div>
                      <p className="text-xs text-white/40 mt-1">{pct}% complete</p>
                    </div>

                    <div className="flex gap-2">
                      <Button size="sm" variant="secondary" className="flex-1" icon={<ArrowDownCircle size={14} />}
                        onClick={() => { setTxModal({ id: g.id as number, type: "deposit" }); txForm.reset(); }}>
                        Deposit
                      </Button>
                      <Button size="sm" variant="ghost" className="flex-1" icon={<ArrowUpCircle size={14} />}
                        onClick={() => { setTxModal({ id: g.id as number, type: "withdraw" }); txForm.reset(); }}>
                        Withdraw
                      </Button>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Transaction Modal */}
        <AnimatePresence>
          {txModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
              onClick={(e) => e.target === e.currentTarget && setTxModal(null)}
            >
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/8 p-6 backdrop-blur-2xl shadow-glass"
              >
                <div className="flex items-center gap-2 mb-4">
                  {txModal.type === "deposit" ? <ArrowDownCircle className="text-emerald-400" size={20} /> : <ArrowUpCircle className="text-amber-400" size={20} />}
                  <h3 className="font-semibold text-white capitalize">{txModal.type}</h3>
                </div>
                <form onSubmit={txForm.handleSubmit(onTransaction)} className="space-y-4">
                  <Input label="Amount ($)" placeholder="0.00" error={txForm.formState.errors.amount?.message} {...txForm.register("amount")} />
                  <Input label="Description" placeholder="Optional" {...txForm.register("description")} />
                  <div className="flex gap-3">
                    <Button type="submit" className="flex-1" variant={txModal.type === "deposit" ? "secondary" : "ghost"}>
                      Confirm
                    </Button>
                    <Button type="button" variant="ghost" className="flex-1" onClick={() => setTxModal(null)}>Cancel</Button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
