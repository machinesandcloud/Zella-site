import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json"
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("zella_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fetchDashboardOverview = async () => {
  const { data } = await api.get("/api/dashboard/overview");
  return data;
};

export const fetchAccountSummary = async () => {
  const { data } = await api.get("/api/account/summary");
  return data;
};

export const fetchPositions = async () => {
  const { data } = await api.get("/api/account/positions");
  return data;
};

export const fetchOrders = async () => {
  const { data } = await api.get("/api/trading/orders");
  return data;
};

export default api;
