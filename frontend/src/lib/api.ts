import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError & { config?: { _retry?: boolean } }) => {
    const originalConfig = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && originalConfig && !originalConfig._retry) {
      originalConfig._retry = true;
      if (typeof window !== "undefined") {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          try {
            const res = await axios.post(
              `${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/token/refresh`,
              { refresh_token: refreshToken },
              { headers: { "Content-Type": "application/json" } }
            );
            const newAccessToken: string = res.data.access_token;
            localStorage.setItem("access_token", newAccessToken);
            if (originalConfig.headers) {
              originalConfig.headers.Authorization = `Bearer ${newAccessToken}`;
            }
            return api(originalConfig);
          } catch {
            // refresh failed — fall through to logout
          }
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// ── Auth (/api/v1/users) ──────────────────────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    api.post("/api/v1/users/login", new URLSearchParams({ username, password }), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  register: (data: { username: string; email: string; password: string; full_name?: string }) =>
    api.post("/api/v1/users/register", data),
  me: () => api.get("/api/v1/users/me"),
  updateMe: (data: unknown) => api.put("/api/v1/users/me", data),
  changePassword: (data: unknown) => api.post("/api/v1/users/me/password", data),
  logout: () => api.post("/api/v1/users/logout"),
};

// ── Expenses (/api/v1/expenses) ───────────────────────────────────────────────

export const expenseApi = {
  list: (params?: Record<string, unknown>) => api.get("/api/v1/expenses", { params }),
  create: (data: unknown) => api.post("/api/v1/expenses", data),
  update: (id: number, data: unknown) => api.put(`/api/v1/expenses/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/expenses/${id}`),
  summary: (params?: Record<string, unknown>) => api.get("/api/v1/expenses/summary", { params }),
  categories: () => api.get("/api/v1/expenses/categories"),
  trend: (months = 6) => api.get("/api/v1/expenses/trend", { params: { months } }),
};

// ── Budgets (/api/v1/budgets) ─────────────────────────────────────────────────

export const budgetApi = {
  list: (params?: Record<string, unknown>) => api.get("/api/v1/budgets", { params }),
  create: (data: unknown) => api.post("/api/v1/budgets", data),
  update: (id: number, data: unknown) => api.put(`/api/v1/budgets/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/budgets/${id}`),
  status: (period?: string) => api.get("/api/v1/budgets/status", { params: { period } }),
};

// ── Savings Goals (/api/v1/savings) ──────────────────────────────────────────

export const savingsApi = {
  list: () => api.get("/api/v1/savings"),
  create: (data: unknown) => api.post("/api/v1/savings", data),
  deposit: (id: number, data: unknown) => api.post(`/api/v1/savings/${id}/deposit`, data),
  withdraw: (id: number, data: unknown) => api.post(`/api/v1/savings/${id}/withdraw`, data),
  transactions: (id: number) => api.get(`/api/v1/savings/${id}/transactions`),
};

// ── Cash Savings (/api/v1/cash-savings) ──────────────────────────────────────

export const cashApi = {
  list: () => api.get("/api/v1/cash-savings"),
  create: (data: unknown) => api.post("/api/v1/cash-savings", data),
  update: (id: number, data: unknown) => api.put(`/api/v1/cash-savings/${id}`, data),
};

// ── Bank Accounts (/api/v1/banks) ─────────────────────────────────────────────

export const bankApi = {
  list: () => api.get("/api/v1/banks/accounts"),
  create: (data: unknown) => api.post("/api/v1/banks/accounts", data),
  uploadStatement: (accountId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    form.append("account_id", accountId.toString());
    return api.post("/api/v1/banks/statements/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  statements: (accountId?: number) =>
    api.get("/api/v1/banks/statements", { params: accountId ? { account_id: accountId } : undefined }),
};

// ── AI Recommendations (/api/v1/ai) ──────────────────────────────────────────

export const aiApi = {
  recommendations: () => api.get("/api/v1/ai/insights"),
  generate: () => api.post("/api/v1/ai/recommendations"),
};

// ── Notifications (/api/v1/notifications) ─────────────────────────────────────

export const notificationApi = {
  list: (params?: Record<string, unknown>) => api.get("/api/v1/notifications", { params }),
  markRead: (id: number) => api.put(`/api/v1/notifications/${id}/read`),
  markAllRead: () => api.put("/api/v1/notifications/read-all"),
  unreadCount: () => api.get("/api/v1/notifications/unread"),
  getPreferences: () => api.get("/api/v1/notifications/preferences"),
  updatePreferences: (data: unknown) => api.put("/api/v1/notifications/preferences", data),
};

// ── Spending Limits (/api/v1/spending-limits) ─────────────────────────────────

export const spendingLimitApi = {
  get: () => api.get("/api/v1/spending-limits"),
  create: (data: unknown) => api.post("/api/v1/spending-limits", data),
  update: (data: unknown) => api.patch("/api/v1/spending-limits", data),
  status: () => api.get("/api/v1/spending-limits/status"),
  delete: () => api.delete("/api/v1/spending-limits"),
};

// ── Zakat (/api/v1/zakat) ─────────────────────────────────────────────────────

export const zakatApi = {
  nisab: (currency = "USD") => api.get("/api/v1/zakat/nisab", { params: { currency } }),
  calculate: (data: unknown) => api.post("/api/v1/zakat/calculate", data),
  list: (params?: Record<string, unknown>) => api.get("/api/v1/zakat", { params }),
  updatePayment: (id: number, data: unknown) => api.patch(`/api/v1/zakat/${id}/payment`, data),
  delete: (id: number) => api.delete(`/api/v1/zakat/${id}`),
};

// ── Qurbani (/api/v1/qurbani) ─────────────────────────────────────────────────

export const qurbaniApi = {
  prices: (currency = "PKR") => api.get("/api/v1/qurbani/prices", { params: { currency } }),
  list: (params?: Record<string, unknown>) => api.get("/api/v1/qurbani", { params }),
  create: (data: unknown) => api.post("/api/v1/qurbani", data),
  contribute: (id: number, data: unknown) => api.post(`/api/v1/qurbani/${id}/contribute`, data),
  update: (id: number, data: unknown) => api.put(`/api/v1/qurbani/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/qurbani/${id}`),
};

// ── Assets (/api/v1/assets) ───────────────────────────────────────────────────

export const assetApi = {
  list: (params?: Record<string, unknown>) => api.get("/api/v1/assets", { params }),
  create: (data: unknown) => api.post("/api/v1/assets", data),
  get: (id: number) => api.get(`/api/v1/assets/${id}`),
  update: (id: number, data: unknown) => api.put(`/api/v1/assets/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/assets/${id}`),
  analytics: () => api.get("/api/v1/assets/analytics/summary"),
};

// ── Sadaqah (/api/v1/sadaqah) ─────────────────────────────────────────────────

export const sadaqahApi = {
  list:    (params?: Record<string, unknown>) => api.get("/api/v1/sadaqah", { params }),
  summary: () => api.get("/api/v1/sadaqah/summary"),
  create:  (data: unknown) => api.post("/api/v1/sadaqah", data),
  update:  (id: number, data: unknown) => api.put(`/api/v1/sadaqah/${id}`, data),
  delete:  (id: number) => api.delete(`/api/v1/sadaqah/${id}`),
};

// ── Liabilities & Net Worth (/api/v1/liabilities) ─────────────────────────────

export const liabilityApi = {
  list:      (params?: Record<string, unknown>) => api.get("/api/v1/liabilities", { params }),
  netWorth:  () => api.get("/api/v1/liabilities/net-worth"),
  create:    (data: unknown) => api.post("/api/v1/liabilities", data),
  update:    (id: number, data: unknown) => api.put(`/api/v1/liabilities/${id}`, data),
  delete:    (id: number) => api.delete(`/api/v1/liabilities/${id}`),
};

// ── Hajj / Umrah (/api/v1/hajj-umrah) ────────────────────────────────────────

export const hajjUmrahApi = {
  list:     () => api.get("/api/v1/hajj-umrah"),
  create:   (data: unknown) => api.post("/api/v1/hajj-umrah", data),
  update:   (id: number, data: unknown) => api.put(`/api/v1/hajj-umrah/${id}`, data),
  delete:   (id: number) => api.delete(`/api/v1/hajj-umrah/${id}`),
  deposit:  (id: number, data: unknown) => api.post(`/api/v1/hajj-umrah/${id}/deposit`, data),
  deposits: (id: number) => api.get(`/api/v1/hajj-umrah/${id}/deposits`),
};

// ── Financial Health Score (/api/v1/financial-health) ─────────────────────────

export const healthApi = {
  score: () => api.get("/api/v1/financial-health/score"),
};
