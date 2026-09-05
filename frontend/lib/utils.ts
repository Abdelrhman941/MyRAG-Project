import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Parse a date string defensively: if the string has no timezone marker
 * (Z or ±hh:mm), append 'Z' so it is always interpreted as UTC.
 */
export function parseUtcDate(value: string): Date {
  // ISO 8601 timezone markers: 'Z', '+HH:MM', '-HH:MM', '+HHMM', '-HHMM'
  if (/[Zz]$|[+-]\d{2}:\d{2}$|[+-]\d{4}$/.test(value)) {
    return new Date(value);
  }
  return new Date(value + 'Z');
}
