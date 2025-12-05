/**
 * Утилита для объединения классов с поддержкой Tailwind CSS
 * Использует clsx для условных классов и tailwind-merge для разрешения конфликтов
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
