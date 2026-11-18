"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, ShieldAlert, Copy, Check, FileText } from "lucide-react";
import { QueryStatus } from "@/types/compliance";

interface AnswerSectionProps {
  answer: string;
  status: QueryStatus;
  onSelectCitation: (evidenceId: string) => void;
  selectedEvidenceId?: string | null;
}

export const AnswerSection: React.FC<AnswerSectionProps> = ({
  answer,
  status,
  onSelectCitation,
  selectedEvidenceId,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render text with interactive clickable citation badges [E1], [E2]
  const renderInteractiveText = (text: string) => {
    const parts = text.split(/(\[E\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[(E\d+)\]$/);
      if (match) {
        const eid = match[1];
        const isSelected = selectedEvidenceId === eid;
        return (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectCitation(eid)}
            className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-mono font-bold border transition-all ${
              isSelected
                ? "bg-safety-500 text-white border-safety-600 shadow-sm ring-2 ring-safety-200"
                : "bg-safety-50 text-safety-800 border-safety-300 hover:bg-safety-100 hover:border-safety-400 cursor-pointer"
            }`}
            title={`Click to inspect verbatim source chunk for ${eid}`}
          >
            [{eid}]
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  let badgeColor = "bg-emerald-50 text-emerald-800 border-emerald-300";
  let StatusIcon = CheckCircle2;
  let statusText = "Grounded Compliance Answer";

  if (status === "conflict_flagged") {
    badgeColor = "bg-amber-50 text-amber-900 border-amber-300";
    StatusIcon = AlertTriangle;
    statusText = "Regulatory Conflict Flagged";
  } else if (status === "abstained") {
    badgeColor = "bg-rose-50 text-rose-800 border-rose-300";
    StatusIcon = ShieldAlert;
    statusText = "Evidence Insufficient (Abstained)";
  }

  return (
    <div className="bg-white rounded-xl border border-steel-200 shadow-sm overflow-hidden">
      {/* Header bar */}
      <div className="px-5 py-3.5 bg-steel-50/70 border-b border-steel-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-steel-500" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-steel-700">
            Compliance Assessment
          </h3>
        </div>

        <div className="flex items-center space-x-2">
          <span
            className={`inline-flex items-center space-x-1.5 text-xs font-bold px-2.5 py-1 rounded-full border ${badgeColor}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            <span>{statusText}</span>
          </span>

          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 text-steel-500 hover:text-steel-800 hover:bg-steel-200/50 rounded-md transition-colors"
            title="Copy answer to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-600" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Answer Body */}
      <div className="p-5">
        <div className="prose prose-sm max-w-none text-steel-900 leading-relaxed text-sm font-normal">
          {renderInteractiveText(answer)}
        </div>
      </div>
    </div>
  );
};
