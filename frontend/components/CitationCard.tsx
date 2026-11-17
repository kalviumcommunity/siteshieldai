"use client";

import React from "react";
import { CitationItem } from "@/types/compliance";
import { formatDocType } from "@/lib/utils";
import { ExternalLink, Hash, Bookmark, Layers, Calendar } from "lucide-react";

interface CitationCardProps {
  citation: CitationItem;
  isSelected: boolean;
  onSelect: () => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  isSelected,
  onSelect,
}) => {
  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl border transition-all cursor-pointer ${
        isSelected
          ? "bg-safety-50/50 border-safety-500 shadow-md ring-2 ring-safety-200"
          : "bg-white border-steel-200 hover:border-steel-300 hover:shadow-sm"
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="bg-steel-900 text-white font-mono text-xs font-bold px-2 py-0.5 rounded">
            [{citation.evidence_id}]
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-steel-100 text-steel-700 border border-steel-200">
            {formatDocType(citation.doc_type)}
          </span>
          <span className="text-[11px] font-mono text-steel-500">
            {citation.version}
          </span>
        </div>

        <div className="text-right">
          <span
            className="text-[10px] font-mono font-semibold text-steel-400 bg-steel-50 px-1.5 py-0.5 rounded border border-steel-200"
            title="Cosine similarity retrieval score"
          >
            Score: {(citation.retrieval_score * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Document Title */}
      <h4 className="text-xs font-bold text-steel-900 mt-2 line-clamp-1">
        {citation.doc_title}
      </h4>

      {/* Section path or Clause */}
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-steel-600">
        {citation.section_id && (
          <span className="inline-flex items-center space-x-0.5 font-medium text-safety-800">
            <Bookmark className="w-3 h-3 text-safety-600" />
            <span>{citation.section_id}</span>
          </span>
        )}
        <span className="inline-flex items-center space-x-0.5">
          <Layers className="w-3 h-3 text-steel-400" />
          <span>Pages {citation.page_start}–{citation.page_end}</span>
        </span>
        {citation.project_id && (
          <span className="inline-flex items-center space-x-0.5">
            <Hash className="w-3 h-3 text-steel-400" />
            <span>{citation.project_id}</span>
          </span>
        )}
        {citation.effective_date && (
          <span className="inline-flex items-center space-x-0.5">
            <Calendar className="w-3 h-3 text-steel-400" />
            <span>Eff: {citation.effective_date}</span>
          </span>
        )}
      </div>

      {/* Verbatim Excerpt Preview */}
      <div className="mt-2.5 bg-steel-50 rounded-lg p-2.5 border border-steel-100 text-[11px] font-mono text-steel-700 line-clamp-3">
        {citation.text_verbatim}
      </div>

      {/* Footer action */}
      <div className="mt-2.5 pt-2 border-t border-steel-100 flex items-center justify-between text-[11px]">
        <span className="text-steel-400">
          Method: <strong className="uppercase font-semibold">{citation.extraction_method}</strong>
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
          className="text-safety-600 font-bold hover:text-safety-700 inline-flex items-center space-x-1"
        >
          <span>Inspect Excerpt</span>
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};
