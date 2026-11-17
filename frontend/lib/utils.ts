import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDocType(type: string): string {
  const map: Record<string, string> = {
    code: "Building Code",
    spec: "Technical Spec",
    report: "Inspection Report",
    safety_manual: "Safety Manual",
    drawing_note: "Drawing Note",
    addendum: "Addendum",
    other: "Document",
  };
  return map[type] || type.toUpperCase();
}

export function formatConflictType(type: string): string {
  const map: Record<string, string> = {
    version_supersession: "Version Supersession",
    report_vs_code_divergence: "Report vs Governing Spec Divergence",
    cross_document_value_mismatch: "Cross-Document Value Mismatch",
  };
  return map[type] || type;
}
