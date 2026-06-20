"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Building2, Upload, FileText, CheckCircle, Clock, XCircle, ChevronDown, ChevronRight } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { bankApi } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import toast from "react-hot-toast";

const accountSchema = z.object({
  bank_name: z.string().min(1),
  account_number: z.string().min(1),
  account_type: z.string().default("checking"),
  currency: z.string().default("USD"),
  balance: z.string().refine((v) => !isNaN(+v), "Must be a number").default("0"),
});
type AccountForm = z.infer<typeof accountSchema>;

const ACCOUNT_TYPES = ["checking", "savings", "credit", "investment"];

const statusIcon = (status: string) => {
  if (status === "completed") return <CheckCircle size={14} className="text-emerald-400" />;
  if (status === "processing") return <Clock size={14} className="text-amber-400" />;
  return <XCircle size={14} className="text-rose-400" />;
};

const statusVariant = (status: string): "success" | "warning" | "danger" | "default" => {
  if (status === "completed") return "success";
  if (status === "processing") return "warning";
  if (status === "failed") return "danger";
  return "default";
};

export default function BanksPage() {
  const [accounts, setAccounts] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [statements, setStatements] = useState<Record<number, Record<string, unknown>[]>>({});
  const [uploading, setUploading] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<AccountForm>({
    resolver: zodResolver(accountSchema),
    defaultValues: { account_type: "checking", currency: "USD", balance: "0" },
  });

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await bankApi.list();
      setAccounts(res.data?.accounts || res.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchAccounts(); }, [fetchAccounts]);

  const loadStatements = async (accountId: number) => {
    if (statements[accountId]) return;
    try {
      const res = await bankApi.statements(accountId);
      setStatements((prev) => ({ ...prev, [accountId]: res.data?.statements || res.data || [] }));
    } catch {}
  };

  const toggleExpand = (id: number) => {
    const next = expandedId === id ? null : id;
    setExpandedId(next);
    if (next !== null) loadStatements(next);
  };

  const onCreateAccount = async (data: AccountForm) => {
    setSubmitting(true);
    try {
      await bankApi.create({ ...data, balance: parseFloat(data.balance) });
      toast.success("Bank account added!");
      reset(); setShowForm(false); fetchAccounts();
    } catch { toast.error("Failed to add account"); }
    finally { setSubmitting(false); }
  };

  const triggerUpload = (accountId: number) => {
    setUploadTarget(accountId);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || uploadTarget === null) return;
    setUploading(uploadTarget);
    try {
      await bankApi.uploadStatement(uploadTarget, file);
      toast.success("Statement uploaded! Processing...");
      setStatements((prev) => ({ ...prev, [uploadTarget]: [] }));
      await loadStatements(uploadTarget);
    } catch { toast.error("Upload failed"); }
    finally { setUploading(null); setUploadTarget(null); e.target.value = ""; }
  };

  const bankGradients: Record<string, string> = {
    checking: "from-blue-600 to-cyan-600",
    savings: "from-emerald-600 to-teal-600",
    credit: "from-rose-600 to-pink-600",
    investment: "from-violet-600 to-purple-600",
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Bank Accounts" subtitle={`${accounts.length} connected accounts`} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        <div className="flex justify-end">
          <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>Add Account</Button>
        </div>

        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
              <GlassCard className="p-6" hover={false}>
                <h3 className="mb-4 text-sm font-semibold text-white">Add Bank Account</h3>
                <form onSubmit={handleSubmit(onCreateAccount)} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Input label="Bank Name" placeholder="Chase, Wells Fargo..." error={errors.bank_name?.message} {...register("bank_name")} />
                  <Input label="Account Number (last 4)" placeholder="1234" error={errors.account_number?.message} {...register("account_number")} />
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-white/70">Account Type</label>
                    <select className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-violet-500/60 focus:outline-none" {...register("account_type")}>
                      {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                    </select>
                  </div>
                  <Input label="Current Balance ($)" placeholder="0.00" {...register("balance")} />
                  <Input label="Currency" placeholder="USD" {...register("currency")} />
                  <div className="sm:col-span-2 lg:col-span-3 flex gap-3">
                    <Button type="submit" loading={submitting}>Add Account</Button>
                    <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
                  </div>
                </form>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Hidden file input */}
        <input ref={fileInputRef} type="file" accept=".pdf,.csv,.xlsx,.xls" className="hidden" onChange={handleFileChange} />

        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-28 rounded-2xl shimmer" />)}
          </div>
        ) : accounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Building2 className="mb-3 h-12 w-12 text-white/20" />
            <p className="text-sm text-white/40">No bank accounts connected</p>
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((acc) => {
              const id = acc.id as number;
              const type = acc.account_type as string;
              const isExpanded = expandedId === id;
              return (
                <motion.div
                  key={id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-white/8 bg-white/5 backdrop-blur-xl overflow-hidden"
                >
                  {/* Account row */}
                  <div className="flex items-center gap-4 p-5">
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${bankGradients[type] || "from-gray-600 to-gray-700"}`}>
                      <Building2 className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-white">{acc.bank_name as string}</p>
                      <p className="text-xs text-white/40">
                        {type.charAt(0).toUpperCase() + type.slice(1)} · ••••{acc.account_number as string}
                      </p>
                    </div>
                    <div className="text-right mr-4">
                      <p className="text-lg font-bold text-white">{formatCurrency(acc.balance as number, acc.currency as string)}</p>
                      <p className="text-xs text-white/40">{acc.currency as string}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={uploading === id ? undefined : <Upload size={14} />}
                        loading={uploading === id}
                        onClick={() => triggerUpload(id)}
                      >
                        Upload
                      </Button>
                      <button
                        onClick={() => toggleExpand(id)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors"
                      >
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Statements panel */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="border-t border-white/8"
                      >
                        <div className="p-5">
                          <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Statements</p>
                          {!statements[id] ? (
                            <p className="text-sm text-white/30">Loading...</p>
                          ) : statements[id].length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-6 text-center">
                              <FileText className="mb-2 h-8 w-8 text-white/20" />
                              <p className="text-sm text-white/30">No statements yet</p>
                              <p className="text-xs text-white/20 mt-1">Upload a PDF or CSV bank statement</p>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {statements[id].map((stmt) => (
                                <div key={stmt.id as number} className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/3 p-3">
                                  <FileText size={16} className="text-white/40 shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm text-white truncate">{stmt.filename as string || `Statement ${stmt.id}`}</p>
                                    <p className="text-xs text-white/40">{formatDate(stmt.created_at as string)}</p>
                                  </div>
                                  <div className="flex items-center gap-1.5">
                                    {statusIcon(stmt.status as string)}
                                    <Badge variant={statusVariant(stmt.status as string)}>
                                      {stmt.status as string}
                                    </Badge>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
