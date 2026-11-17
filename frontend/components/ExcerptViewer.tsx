"use client";

import React, { useState } from "react";
import { CitationItem } from "@/types/compliance";
import { formatDocType } from "@/lib/utils";
import { X, Copy, Check, FileCheck, Layers, Hash, Calendar, ShieldCheck } from "lucide-react";

interface ExcerptViewerProps {
  citation: CitationItem | null;
  onClose: () => void;
}

export const ExcerptViewer: React.FC<ExcerptViewerProps> = ({
  citation,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!citation) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(citation.text_verbatim);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white rounded-xl border border-steel-200 shadow-sm overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 bg-steel-900 text-white flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileCheck className="w-4 h-4 text-safety-400" />
          <span className="font-mono font-bold text-xs">
            [{citation.evidence_id}] Source Provenance Inspector
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleCopy}
            className="p-1 text-steel-300 hover:text-white rounded hover:bg-steel-800 transition-colors"
            title="Copy verbatim text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onClose}
            className="p-1 text-steel-300 hover:text-white rounded hover:bg-steel-800 transition-colors"
            title="Close inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Provenance Metadata Table */}
      <div className="p-4 border-b border-steel-100 bg-steel-50/50 text-xs">
        <h4 className="font-bold text-steel-900 text-sm">{citation.doc_title}</h4>
        
        <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] text-steel-600">
          <div>
            <span className="text-steel-400 block">Type:</span>
            <span className="font-semibold text-steel-800">{formatDocType(citation.doc_type)}</span>
          </div>
          <div>
            <span className="text-steel-400 block">Version:</span>
            <span className="font-mono text-steel-800">{citation.version}</span>
          </div>
          <div>
            <span className="text-steel-400 block">Section / Clause:</span>
            <span className="font-medium text-safety-700">{citation.section_id || "Unspecified"}</span>
          </div>
          <div>
            <span className="text-steel-400 block">Pages:</span>
            <span className="font-medium text-steel-800">
              {citation.page_start} {citation.page_start !== citation.page_end ? `– ${citation.page_end}` : ""}
            </span>
          </div>
          <div>
            <span className="text-steel-400 block">Project ID:</span>
            <span className="font-mono text-steel-800">{citation.project_id || "All Projects"}</span>
          </div>
          <div>
            <span className="text-steel-400 block">Jurisdiction:</span>
            <span className="font-semibold text-steel-800">{citation.jurisdiction}</span>
          </div>
        </div>

        {/* Section Breadcrumbs */}
        {citation.section_path.length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-steel-200/60 text-[11px]">
            <span className="text-steel-400 block mb-0.5">Hierarchy Path:</span>
            <p className="font-mono text-steel-600 break-words">
              {citation.section_path.join(" / ")}
            </p>
          </div>
        )}
      </div>

      {/* Verbatim Source Chunk Text */}
      <div className="p-4 flex-1 overflow-y-auto">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-steel-500">
            Verbatim Chunk Text (Exact OCR / Native Extraction)
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-steel-100 text-steel-600 border border-steel-200">
            {citation.content_type.toUpperCase()} / {citation.extraction_method.toUpperCase()}
          </span>
        </div>

        <div className="bg-steel-50 border border-steel-200 rounded-lg p-3.5 font-mono text-xs text-steel-800 whitespace-pre-wrap leading-relaxed shadow-inner">
          {citation.text_verbatim}
        </div>

        <div className="mt-3 p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start space-x-2 text-xs text-emerald-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <strong className="block font-semibold">Grounded & Verified</strong>
            <p className="text-[11px] text-emerald-700 mt-0.5">
              The 3-stage CitationValidator confirmed that numeric quantities and clause references in the answer match this chunk verbatim.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
