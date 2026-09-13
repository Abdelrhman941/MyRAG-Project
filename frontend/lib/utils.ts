import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Parses a date string and ensures it is interpreted as UTC.
 * If the string lacks a timezone marker (e.g., 'Z' or '±hh:mm'),
 * it appends 'Z' to prevent browser-specific local time fallbacks.
 *
 * @param value - The ISO 8601 date string to parse.
 * @returns A Date object representing the UTC time.
 */
export function parseUtcDate(value: string): Date {
  const hasTimezone = /[Zz]$|[+-]\d{2}:\d{2}$|[+-]\d{4}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
