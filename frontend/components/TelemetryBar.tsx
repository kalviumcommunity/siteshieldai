"use client";

import React from "react";
import { LatencyBreakdown } from "@/types/compliance";
import { Clock, Cpu, ShieldCheck, Database, Zap } from "lucide-react";

interface TelemetryBarProps {
  queryId: string;
  latency: LatencyBreakdown;
  disclaimer: string;
}

export const TelemetryBar: React.FC<TelemetryBarProps> = ({
  queryId,
  latency,
  disclaimer,
}) => {
  return (
    <div className="bg-steel-50 border border-steel-200 rounded-xl p-4 text-xs text-steel-600">
      {/* Top row: Stage latency pills */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-steel-200">
        <div className="flex items-center space-x-1.5 font-mono text-[11px] text-steel-500">
          <Clock className="w-3.5 h-3.5" />
          <span>Audit ID: <strong className="text-steel-800">{queryId}</strong></span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-white border border-steel-200" title="Embedding Generation">
            <Cpu className="w-3 h-3 text-steel-400" />
            <span>Embed: <strong>{latency.embedding}ms</strong></span>
          </span>
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-white border border-steel-200" title="Vector Search Retrieval">
            <Database className="w-3 h-3 text-steel-400" />
            <span>Search: <strong>{latency.retrieval}ms</strong></span>
          </span>
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-white border border-steel-200" title="LLM Grounded Generation">
            <Zap className="w-3 h-3 text-steel-400" />
            <span>Gen: <strong>{latency.generation}ms</strong></span>
          </span>
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-white border border-steel-200" title="3-Stage Citation Validation">
            <ShieldCheck className="w-3 h-3 text-steel-400" />
            <span>Audit: <strong>{latency.validation}ms</strong></span>
          </span>
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-steel-900 text-white font-bold" title="End-to-End Latency">
            <span>Total: {latency.total}ms</span>
          </span>
        </div>
      </div>

      {/* Bottom row: Standard Compliance Disclaimer */}
      <div className="pt-2.5 text-[11px] text-steel-500 leading-relaxed italic">
        {disclaimer}
      </div>
    </div>
  );
};
