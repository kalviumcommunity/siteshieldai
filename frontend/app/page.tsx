"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { SafetyBanner } from "@/components/SafetyBanner";
import { QuickPrompts } from "@/components/QuickPrompts";
import { QueryInput } from "@/components/QueryInput";
import { AnswerSection } from "@/components/AnswerSection";
import { CitationCard } from "@/components/CitationCard";
import { ExcerptViewer } from "@/components/ExcerptViewer";
import { ConflictBanner } from "@/components/ConflictBanner";
import { AbstentionBanner } from "@/components/AbstentionBanner";
import { TelemetryBar } from "@/components/TelemetryBar";
import { QueryFilters, QueryResponse, CitationItem } from "@/types/compliance";
import { checkBackendHealth, executeQuery, ApiClientError } from "@/lib/api";
import { DemoScenario } from "@/lib/demoData";
import { BookOpen, AlertCircle, RefreshCw, FileSearch, HelpCircle } from "lucide-react";

export default function Home() {
  // App state
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<QueryFilters>({
    project_id: "#104",
    jurisdiction: "IN-KA",
    doc_types: null,
    include_superseded: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  // Active citation and excerpt inspection
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);

  // Backend status and demo mode
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true); // default true for initial safety

  // Check backend health on mount
  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      const res = await checkBackendHealth();
      if (isMounted) {
        setBackendOnline(res.online);
        if (res.online) {
          setIsDemoMode(false);
        }
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Update active citation when selectedEvidenceId changes or response updates
  useEffect(() => {
    if (response && response.citations.length > 0) {
      if (selectedEvidenceId) {
        const found = response.citations.find((c) => c.evidence_id === selectedEvidenceId);
        setActiveCitation(found || response.citations[0]);
      } else {
        setSelectedEvidenceId(response.citations[0].evidence_id);
        setActiveCitation(response.citations[0]);
      }
    } else {
      setActiveCitation(null);
      setSelectedEvidenceId(null);
    }
  }, [response, selectedEvidenceId]);

  // Handle Query Submission
  const handleSubmitQuery = async (overrideQuery?: string) => {
    const q = (overrideQuery || query).trim();
    if (!q) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await executeQuery(
        {
          query: q,
          filters,
          top_k: 5,
        },
        { useDemoFallback: isDemoMode || !backendOnline }
      );

      setResponse(res);
      if (res.citations.length > 0) {
        setSelectedEvidenceId(res.citations[0].evidence_id);
        setActiveCitation(res.citations[0]);
      } else {
        setSelectedEvidenceId(null);
        setActiveCitation(null);
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred while communicating with Site Shield AI.");
      }
      setResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Quick Demonstration Scenario Selection
  const handleSelectScenario = (scenario: DemoScenario) => {
    setQuery(scenario.query);
    setFilters((prev) => ({
      ...prev,
      project_id: scenario.projectId,
      jurisdiction: scenario.jurisdiction,
    }));
    setError(null);
    setResponse(scenario.response);
    if (scenario.response.citations.length > 0) {
      setSelectedEvidenceId(scenario.response.citations[0].evidence_id);
      setActiveCitation(scenario.response.citations[0]);
    } else {
      setSelectedEvidenceId(null);
      setActiveCitation(null);
    }
  };

  const handleReset = () => {
    setQuery("");
    setResponse(null);
    setError(null);
    setSelectedEvidenceId(null);
    setActiveCitation(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-steel-900">
      {/* Navigation Header */}
      <Navbar
        backendOnline={backendOnline}
        isDemoMode={isDemoMode}
        onToggleDemoMode={() => setIsDemoMode(!isDemoMode)}
        selectedProject={filters.project_id || "ALL"}
        onSelectProject={(proj) =>
          setFilters((f) => ({ ...f, project_id: proj === "ALL" ? null : proj }))
        }
        selectedJurisdiction={filters.jurisdiction || "GLOBAL"}
        onSelectJurisdiction={(jur) =>
          setFilters((f) => ({ ...f, jurisdiction: jur === "GLOBAL" ? null : jur }))
        }
      />

      {/* Safety Compliance Precaution Banner */}
      <SafetyBanner isDemoMode={isDemoMode} />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Top Query Interface */}
        <div className="mb-6">
          <QueryInput
            query={query}
            onChangeQuery={setQuery}
            onSubmit={() => handleSubmitQuery()}
            isLoading={isLoading}
            filters={filters}
            onChangeFilters={setFilters}
            onReset={handleReset}
          />

          {/* Quick Scenario Starter Prompts */}
          <QuickPrompts
            onSelectScenario={handleSelectScenario}
            disabled={isLoading}
          />
        </div>

        {/* Error Alert Display */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start space-x-3 shadow-xs">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs">
              <strong className="block font-bold mb-0.5">Connection or Execution Error</strong>
              <p className="leading-relaxed">{error}</p>
              <div className="mt-2 flex items-center space-x-2">
                <button
                  onClick={() => handleSubmitQuery()}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-600 text-white font-semibold hover:bg-rose-700 transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry Question</span>
                </button>
                <button
                  onClick={() => setIsDemoMode(true)}
                  className="px-2.5 py-1 rounded bg-white border border-rose-300 text-rose-800 font-semibold hover:bg-rose-100 transition-colors"
                >
                  Switch to Demo Mode
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading Indicator State */}
        {isLoading && (
          <div className="bg-white rounded-xl border border-steel-200 p-8 shadow-sm text-center mb-6">
            <div className="inline-flex p-3 rounded-full bg-safety-50 text-safety-600 mb-3 animate-spin">
              <RefreshCw className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-steel-900">
              Auditing Construction Regulations...
            </h3>
            <p className="text-xs text-steel-500 mt-1 max-w-md mx-auto">
              Extracting candidate chunks, checking version supersession, verifying 3-stage citations, and assembling grounded response.
            </p>
          </div>
        )}

        {/* Results Workspace: Dual Pane for Desktop & Responsive Tablet */}
        {response && !isLoading && (
          <div className="space-y-6">
            {/* Top Warning Banners: Conflicts or Abstentions */}
            {response.status === "conflict_flagged" && (
              <ConflictBanner conflicts={response.conflicts} />
            )}

            {response.status === "abstained" && (
              <AbstentionBanner
                reason={response.abstention_reason}
                query={query}
              />
            )}

            {/* Split Screen Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column (7 cols): Grounded Answer & Citations */}
              <div className="lg:col-span-7 space-y-6">
                {/* Answer presentation */}
                <AnswerSection
                  answer={response.answer}
                  status={response.status}
                  onSelectCitation={(eid) => {
                    setSelectedEvidenceId(eid);
                    const match = response.citations.find((c) => c.evidence_id === eid);
                    if (match) setActiveCitation(match);
                  }}
                  selectedEvidenceId={selectedEvidenceId}
                />

                {/* Source Citation Cards Grid */}
                {response.citations.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-1.5">
                        <BookOpen className="w-4 h-4 text-steel-500" />
                        <h4 className="text-xs font-bold uppercase tracking-wider text-steel-700">
                          Source Citations ({response.citations.length})
                        </h4>
                      </div>
                      <span className="text-[11px] text-steel-400">
                        Click card to inspect source text
                      </span>
                    </div>

                    <div className="space-y-3">
                      {response.citations.map((citation) => (
                        <CitationCard
                          key={citation.evidence_id}
                          citation={citation}
                          isSelected={selectedEvidenceId === citation.evidence_id}
                          onSelect={() => {
                            setSelectedEvidenceId(citation.evidence_id);
                            setActiveCitation(citation);
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column (5 cols): Excerpt Viewer Panel */}
              <div className="lg:col-span-5 sticky top-20">
                {activeCitation ? (
                  <ExcerptViewer
                    citation={activeCitation}
                    onClose={() => setActiveCitation(null)}
                  />
                ) : (
                  <div className="bg-white rounded-xl border border-dashed border-steel-300 p-8 text-center text-steel-400">
                    <FileSearch className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <h4 className="text-xs font-bold text-steel-600">
                      No Source Excerpt Selected
                    </h4>
                    <p className="text-[11px] mt-1">
                      Click any <span className="font-mono font-bold text-safety-600">[E#]</span> badge or citation card to inspect the verbatim extracted chunk.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Telemetry Bar */}
            <TelemetryBar
              queryId={response.query_id}
              latency={response.latency_ms}
              disclaimer={response.disclaimer}
            />
          </div>
        )}

        {/* Empty state when no query or response */}
        {!response && !isLoading && !error && (
          <div className="bg-white rounded-xl border border-steel-200 p-10 text-center shadow-xs">
            <div className="w-12 h-12 rounded-full bg-steel-50 text-steel-400 flex items-center justify-center mx-auto mb-3">
              <HelpCircle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-steel-800">
              No Question Audited Yet
            </h3>
            <p className="text-xs text-steel-500 max-w-md mx-auto mt-1 leading-relaxed">
              Enter a construction compliance question above or select one of the demonstration scenarios to test grounded answers, inline citations, conflict flagging, and safety abstentions.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
