import axios from 'axios';

const baseURL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cn_access');
  if (token && config.headers) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const wsUrl = (path: string) => {
  const base = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000';
  return `${base}${path}`;
};
