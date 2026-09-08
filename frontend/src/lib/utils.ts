import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function clampNumberInput(value: number | "", min: number, max: number): number {
  const n = value === "" ? min : value;
  return Math.min(max, Math.max(min, n));
}
