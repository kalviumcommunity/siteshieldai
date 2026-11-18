"use client";

import React from "react";
import { ShieldAlert, AlertCircle, UploadCloud, HelpCircle } from "lucide-react";

interface AbstentionBannerProps {
  reason?: string | null;
  query: string;
}

export const AbstentionBanner: React.FC<AbstentionBannerProps> = ({
  reason,
  query,
}) => {
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-start space-x-3.5">
        <div className="p-2.5 rounded-lg bg-rose-500 text-white shrink-0 shadow-sm">
          <ShieldAlert className="w-6 h-6 stroke-[2.2]" />
        </div>

        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-bold text-rose-950">
              Safety Abstention: Insufficient Regulatory Evidence
            </h3>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full border border-rose-200">
              Zero Hallucination Gate
            </span>
          </div>

          <p className="text-xs text-rose-900 mt-1.5 leading-relaxed">
            Site Shield AI determined that the indexed document corpus does not contain sufficient verified facts to ground a compliant answer.
            In accordance with construction safety requirements, the model refused to extrapolate or guess.
          </p>

          {/* Reason Box */}
          {reason && (
            <div className="mt-3 p-3 bg-white rounded-lg border border-rose-200 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-rose-700 block mb-1">
                Abstention Audit Reason:
              </span>
              <p className="font-mono text-steel-800 text-[11px] leading-relaxed">
                {reason}
              </p>
            </div>
          )}

          {/* Recommended Actions */}
          <div className="mt-4 pt-3 border-t border-rose-200/70 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-steel-700">
            <div className="flex items-start space-x-2">
              <UploadCloud className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>
                <strong>Upload Governing Code:</strong> Ingest the relevant design standard, submittal, or specification into the project corpus.
              </span>
            </div>
            <div className="flex items-start space-x-2">
              <HelpCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>
                <strong>Refine Question:</strong> Verify project ID or check if query terms match technical construction nomenclature.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
