"use client";
import { useEffect, useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Filter, Search, Receipt } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { expenseApi } from "@/lib/api";
import { formatCurrency, formatDate, CATEGORY_COLORS, CATEGORY_ICONS } from "@/lib/utils";
import toast from "react-hot-toast";

const schema = z.object({
  amount: z.string().refine((v) => !isNaN(+v) && +v > 0, "Must be > 0"),
  category: z.string().min(1, "Required"),
  expense_type: z.string().default("variable"),
  description: z.string().optional(),
  merchant_name: z.string().optional(),
  transaction_date: z.string().min(1, "Required"),
  payment_method: z.string().optional(),
  currency: z.string().default("USD"),
});
type FormData = z.infer<typeof schema>;

const CATEGORIES = ["Food", "Transport", "Shopping", "Entertainment", "Health", "Education", "Utilities", "Housing", "Other"];

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { transaction_date: new Date().toISOString().slice(0, 16), currency: "USD", expense_type: "variable" },
  });

  const fetchExpenses = useCallback(async () => {
    setLoading(true);
    try {
      const res = await expenseApi.list({ limit: 50, search, category: filterCategory || undefined });
      setExpenses(res.data.expenses || []);
      setTotal(res.data.total || 0);
    } catch { toast.error("Failed to load expenses"); }
    finally { setLoading(false); }
  }, [search, filterCategory]);

  useEffect(() => { fetchExpenses(); }, [fetchExpenses]);

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      await expenseApi.create({ ...data, amount: parseFloat(data.amount), transaction_date: new Date(data.transaction_date).toISOString() });
      toast.success("Expense added!");
      reset();
      setShowForm(false);
      fetchExpenses();
    } catch { toast.error("Failed to add expense"); }
    finally { setSubmitting(false); }
  };

  const deleteExpense = async (id: number) => {
    try {
      await expenseApi.delete(id);
      toast.success("Deleted");
      fetchExpenses();
    } catch { toast.error("Failed to delete"); }
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Expenses" subtitle={`${total} transactions`} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search expenses..."
              className="w-full h-9 rounded-xl border border-white/8 bg-white/5 pl-9 pr-4 text-sm text-white placeholder:text-white/30 focus:border-violet-500/40 focus:outline-none focus:ring-1 focus:ring-violet-500/20 transition-all"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="h-9 rounded-xl border border-white/8 bg-white/5 px-3 text-sm text-white/70 focus:border-violet-500/40 focus:outline-none"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>
            Add Expense
          </Button>
        </div>

        {/* Add form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
              <GlassCard className="p-6" hover={false}>
                <h3 className="mb-4 text-sm font-semibold text-white">New Expense</h3>
                <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Input label="Amount ($)" placeholder="0.00" error={errors.amount?.message} {...register("amount")} />
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-white/70">Category</label>
                    <select className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-violet-500/60 focus:outline-none" {...register("category")}>
                      <option value="">Select...</option>
                      {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>)}
                    </select>
                    {errors.category && <p className="text-xs text-rose-400">{errors.category.message}</p>}
                  </div>
                  <Input label="Description" placeholder="Coffee, groceries..." {...register("description")} />
                  <Input label="Merchant" placeholder="Store name" {...register("merchant_name")} />
                  <Input label="Date & Time" type="datetime-local" {...register("transaction_date")} />
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-white/70">Payment Method</label>
                    <select className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-violet-500/60 focus:outline-none" {...register("payment_method")}>
                      <option value="">None</option>
                      <option>cash</option><option>credit_card</option><option>debit_card</option><option>bank_transfer</option><option>digital_wallet</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2 lg:col-span-3 flex gap-3">
                    <Button type="submit" loading={submitting} icon={<Plus size={16} />}>Add Expense</Button>
                    <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Expenses list */}
        <GlassCard className="overflow-hidden" hover={false}>
          {loading ? (
            <div className="space-y-1 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 rounded-xl shimmer" />
              ))}
            </div>
          ) : expenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Receipt className="mb-3 h-12 w-12 text-white/20" />
              <p className="text-sm text-white/40">No expenses found</p>
              <Button className="mt-4" icon={<Plus size={16} />} onClick={() => setShowForm(true)}>Add First Expense</Button>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {expenses.map((exp) => (
                <motion.div
                  key={exp.id as number}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-white/3 transition-colors group"
                >
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg"
                    style={{ background: `${CATEGORY_COLORS[exp.category as string]}20` }}
                  >
                    {CATEGORY_ICONS[exp.category as string] || "📦"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{exp.description as string || exp.category as string}</p>
                    <p className="text-xs text-white/40">{exp.merchant_name as string || "—"} · {formatDate(exp.transaction_date as string)}</p>
                  </div>
                  <Badge variant="default">{exp.category as string}</Badge>
                  <p className="text-sm font-semibold text-rose-400 w-24 text-right">
                    -{formatCurrency(exp.amount as number, exp.currency as string)}
                  </p>
                  <button
                    onClick={() => deleteExpense(exp.id as number)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-white/30 hover:text-rose-400"
                  >
                    <Trash2 size={15} />
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
