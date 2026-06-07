import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTimeRemaining(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds <= 0) return '';
  if (seconds < 60) return `~${Math.round(seconds)}s kvar`;
  if (seconds < 3600) return `~${Math.round(seconds / 60)}min kvar`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return `~${hours}h ${mins}min kvar`;
}