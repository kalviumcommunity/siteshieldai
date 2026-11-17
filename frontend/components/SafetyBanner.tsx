"use client";

import React from "react";
import { AlertTriangle, Info } from "lucide-react";

interface SafetyBannerProps {
  isDemoMode?: boolean;
}

export const SafetyBanner: React.FC<SafetyBannerProps> = ({ isDemoMode }) => {
  return (
    <div className="bg-steel-900 text-steel-200 text-xs px-4 py-2.5 border-b border-steel-800">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-safety-400 shrink-0" />
          <p className="font-medium text-steel-300">
            <strong className="text-white">Safety Precaution:</strong> Site Shield AI is an
            assistive decision-support system. All regulatory claims, numeric values, and citations
            must be verified by the Engineer of Record (EoR) or certified safety inspector before
            field execution.
          </p>
        </div>

        {isDemoMode && (
          <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-400/30 text-[11px] font-semibold whitespace-nowrap">
            <Info className="w-3 h-3" />
            <span>DEMONSTRATION DATA MODE ACTIVE</span>
          </div>
        )}
      </div>
    </div>
  );
};
