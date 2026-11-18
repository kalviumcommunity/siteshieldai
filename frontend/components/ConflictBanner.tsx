"use client";

import React, { useState } from "react";
import { ConflictItem } from "@/types/compliance";
import { formatConflictType } from "@/lib/utils";
import { AlertTriangle, ChevronDown, ChevronUp, Scale, FileText, ArrowRight } from "lucide-react";

interface ConflictBannerProps {
  conflicts: ConflictItem[];
}

export const ConflictBanner: React.FC<ConflictBannerProps> = ({ conflicts }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="bg-amber-50/90 border border-amber-300 rounded-xl p-4 sm:p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-lg bg-amber-500 text-white shrink-0 shadow-xs">
          <AlertTriangle className="w-5 h-5 stroke-[2.5]" />
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-bold text-amber-950">
              Regulatory Discrepancy & Conflict Detected ({conflicts.length})
            </h3>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
              Legal Precedence Alert
            </span>
          </div>
          <p className="text-xs text-amber-800 mt-1">
            Site Shield AI identified divergent specifications or revisions across the retrieved documents.
            Review the side-by-side comparison below.
          </p>
        </div>
      </div>

      {/* Conflict Items List */}
      <div className="mt-4 space-y-3">
        {conflicts.map((conflict, idx) => {
          const isExpanded = expandedIndex === idx;
          return (
            <div
              key={idx}
              className="bg-white rounded-lg border border-amber-200 shadow-xs overflow-hidden"
            >
              {/* Conflict Header Accordion Button */}
              <button
                type="button"
                onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-amber-50/50 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <Scale className="w-4 h-4 text-amber-600 shrink-0" />
                  <span className="text-xs font-bold text-steel-900">
                    {formatConflictType(conflict.conflict_type)}
                  </span>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-steel-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-steel-500" />
                )}
              </button>

              {/* Accordion Body */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-amber-100 text-xs">
                  {/* Summary */}
                  <p className="text-steel-800 font-medium mb-3">
                    {conflict.summary}
                  </p>

                  {/* Side-by-Side Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                    {/* Source A */}
                    <div className="p-3 rounded-lg border border-steel-200 bg-steel-50/60">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-bold text-steel-600 uppercase">
                          Source Document A
                        </span>
                        <span className="font-mono text-[10px] text-steel-500">
                          {conflict.source_a.version}
                        </span>
                      </div>
                      <h5 className="font-bold text-steel-900 text-xs line-clamp-1">
                        {conflict.source_a.doc_title}
                      </h5>
                      <span className="text-[11px] text-safety-700 font-medium block mt-0.5">
                        {conflict.source_a.section_id || "Page " + conflict.source_a.page_start}
                      </span>
                      <blockquote className="mt-2 text-[11px] font-mono text-steel-700 bg-white p-2 rounded border border-steel-200 italic">
                        &ldquo;{conflict.source_a.excerpt}&rdquo;
                      </blockquote>
                    </div>

                    {/* Source B */}
                    <div className="p-3 rounded-lg border border-steel-200 bg-steel-50/60">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-bold text-steel-600 uppercase">
                          Source Document B
                        </span>
                        <span className="font-mono text-[10px] text-steel-500">
                          {conflict.source_b.version}
                        </span>
                      </div>
                      <h5 className="font-bold text-steel-900 text-xs line-clamp-1">
                        {conflict.source_b.doc_title}
                      </h5>
                      <span className="text-[11px] text-safety-700 font-medium block mt-0.5">
                        {conflict.source_b.section_id || "Page " + conflict.source_b.page_start}
                      </span>
                      <blockquote className="mt-2 text-[11px] font-mono text-steel-700 bg-white p-2 rounded border border-steel-200 italic">
                        &ldquo;{conflict.source_b.excerpt}&rdquo;
                      </blockquote>
                    </div>
                  </div>

                  {/* Precedence Guidance Note */}
                  <div className="p-2.5 rounded-lg bg-amber-100/70 border border-amber-300 text-amber-900 text-xs flex items-start space-x-2">
                    <Scale className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                    <div>
                      <strong className="block font-bold">Governing Precedence Ruling:</strong>
                      <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                        {conflict.precedence_note}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
