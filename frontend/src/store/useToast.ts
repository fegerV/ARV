import { create } from 'zustand';

interface ToastState {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
  showToast: (message: string, severity?: 'success' | 'error' | 'warning' | 'info') => void;
  hideToast: () => void;
}

export const useToast = create<ToastState>((set) => ({
  open: false,
  message: '',
  severity: 'info',
  showToast: (message, severity = 'info') => set({ open: true, message, severity }),
  hideToast: () => set({ open: false }),
}));
