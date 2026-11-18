"use client";

import React, { useState } from "react";
import { Search, SlidersHorizontal, ArrowRight, Loader2, X, RotateCcw } from "lucide-react";
import { DocumentType, QueryFilters } from "@/types/compliance";

interface QueryInputProps {
  query: string;
  onChangeQuery: (val: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  filters: QueryFilters;
  onChangeFilters: (filters: QueryFilters) => void;
  onReset: () => void;
}

const AVAILABLE_DOC_TYPES: { id: DocumentType; label: string }[] = [
  { id: "code", label: "Building Code" },
  { id: "spec", label: "Technical Specification" },
  { id: "report", label: "Inspection Report" },
  { id: "safety_manual", label: "Safety Manual" },
  { id: "drawing_note", label: "Drawing Note" },
  { id: "addendum", label: "Addendum" },
];

export const QueryInput: React.FC<QueryInputProps> = ({
  query,
  onChangeQuery,
  onSubmit,
  isLoading,
  filters,
  onChangeFilters,
  onReset,
}) => {
  const [showFilters, setShowFilters] = useState(false);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && query.trim()) {
        onSubmit();
      }
    }
  };

  const toggleDocType = (docType: DocumentType) => {
    const current = filters.doc_types || [];
    const exists = current.includes(docType);
    let updated: DocumentType[];
    if (exists) {
      updated = current.filter((t) => t !== docType);
    } else {
      updated = [...current, docType];
    }
    onChangeFilters({
      ...filters,
      doc_types: updated.length > 0 ? updated : null,
    });
  };

  const activeFilterCount =
    (filters.project_id ? 1 : 0) +
    (filters.jurisdiction ? 1 : 0) +
    (filters.doc_types?.length ? filters.doc_types.length : 0) +
    (filters.include_superseded ? 1 : 0);

  return (
    <div className="bg-white rounded-xl border border-steel-200 shadow-sm overflow-hidden">
      <div className="p-4 sm:p-5">
        <label htmlFor="query-textarea" className="block text-xs font-bold text-steel-700 uppercase tracking-wider mb-2">
          Regulatory Compliance Query
        </label>

        {/* Text Input Area */}
        <div className="relative">
          <textarea
            id="query-textarea"
            rows={3}
            value={query}
            onChange={(e) => onChangeQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a regulatory compliance or engineering requirement question (e.g., 'What is minimum curing duration for foundation slabs under high moisture?')..."
            className="w-full text-sm text-steel-900 placeholder-steel-400 border border-steel-200 rounded-lg p-3 pr-10 focus:outline-none focus:ring-2 focus:ring-safety-500 focus:border-safety-500 transition-shadow resize-none"
            disabled={isLoading}
          />
          {query && !isLoading && (
            <button
              onClick={() => onChangeQuery("")}
              className="absolute right-3 top-3 text-steel-400 hover:text-steel-600 transition-colors"
              title="Clear text"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Controls row */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2.5">
          {/* Filter toggle & reset buttons */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                showFilters || activeFilterCount > 0
                  ? "bg-steel-100 text-steel-900 border-steel-300"
                  : "bg-white text-steel-600 border-steel-200 hover:bg-steel-50"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-steel-500" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span className="bg-safety-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full ml-1">
                  {activeFilterCount}
                </span>
              )}
            </button>

            {query && (
              <button
                type="button"
                onClick={onReset}
                disabled={isLoading}
                className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium text-steel-500 hover:text-steel-800 transition-colors"
                title="Reset query and results"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>

          {/* Submit Action Button */}
          <div className="flex items-center space-x-2">
            <span className="text-[11px] text-steel-400 hidden sm:inline">
              Press <kbd className="px-1.5 py-0.5 bg-steel-100 border border-steel-200 rounded font-mono text-[10px]">Enter</kbd> to submit
            </span>
            <button
              type="button"
              onClick={onSubmit}
              disabled={isLoading || !query.trim()}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider bg-safety-500 hover:bg-safety-600 text-white shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying Corpus...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Audit Question</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Expandable Filters Tray */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-steel-100 bg-steel-50/70 -mx-4 sm:-mx-5 px-4 sm:px-5 pb-2 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Project Filter */}
              <div>
                <label className="block font-semibold text-steel-700 mb-1">
                  Project Scoping (OQ-06 Data Isolation)
                </label>
                <input
                  type="text"
                  value={filters.project_id || ""}
                  onChange={(e) =>
                    onChangeFilters({
                      ...filters,
                      project_id: e.target.value.trim() || null,
                    })
                  }
                  placeholder="e.g. #104 or leave empty for all"
                  className="w-full text-xs border border-steel-200 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-safety-500"
                />
              </div>

              {/* Jurisdiction Filter */}
              <div>
                <label className="block font-semibold text-steel-700 mb-1">
                  Jurisdiction Code
                </label>
                <input
                  type="text"
                  value={filters.jurisdiction || ""}
                  onChange={(e) =>
                    onChangeFilters({
                      ...filters,
                      jurisdiction: e.target.value.trim() || null,
                    })
                  }
                  placeholder="e.g. IN-KA, US-CA"
                  className="w-full text-xs border border-steel-200 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-safety-500"
                />
              </div>

              {/* Include Superseded Toggle */}
              <div className="flex items-center space-x-2 pt-4">
                <input
                  id="include-superseded-toggle"
                  type="checkbox"
                  checked={filters.include_superseded}
                  onChange={(e) =>
                    onChangeFilters({
                      ...filters,
                      include_superseded: e.target.checked,
                    })
                  }
                  className="w-4 h-4 text-safety-600 rounded border-steel-300 focus:ring-safety-500 cursor-pointer"
                />
                <label
                  htmlFor="include-superseded-toggle"
                  className="font-semibold text-steel-700 cursor-pointer"
                >
                  Include Superseded Revisions (Historical Audit)
                </label>
              </div>
            </div>

            {/* Document Types Multi-select Chips */}
            <div className="mt-3">
              <span className="block font-semibold text-steel-700 mb-1.5">
                Target Document Types:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {AVAILABLE_DOC_TYPES.map((dt) => {
                  const isSelected = filters.doc_types?.includes(dt.id) ?? false;
                  return (
                    <button
                      key={dt.id}
                      type="button"
                      onClick={() => toggleDocType(dt.id)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border transition-all ${
                        isSelected
                          ? "bg-steel-800 text-white border-steel-800 font-semibold shadow-xs"
                          : "bg-white text-steel-600 border-steel-200 hover:border-steel-400"
                      }`}
                    >
                      {dt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
