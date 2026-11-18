"use client";

import React from "react";
import { DEMO_SCENARIOS, DemoScenario } from "@/lib/demoData";
import { CheckCircle2, AlertTriangle, ShieldAlert, Sparkles } from "lucide-react";

interface QuickPromptsProps {
  onSelectScenario: (scenario: DemoScenario) => void;
  disabled?: boolean;
}

export const QuickPrompts: React.FC<QuickPromptsProps> = ({
  onSelectScenario,
  disabled,
}) => {
  return (
    <div className="mt-4">
      <div className="flex items-center space-x-1.5 mb-2.5">
        <Sparkles className="w-4 h-4 text-safety-500" />
        <span className="text-xs font-bold uppercase tracking-wider text-steel-500">
          Try Demonstration Scenarios (Realistic Data)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {DEMO_SCENARIOS.map((scenario) => {
          let badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
          let Icon = CheckCircle2;
          let label = "Grounded Answer";

          if (scenario.category === "conflict") {
            badgeColor = "bg-amber-50 text-amber-700 border-amber-200";
            Icon = AlertTriangle;
            label = "Conflict Flagged";
          } else if (scenario.category === "abstention") {
            badgeColor = "bg-rose-50 text-rose-700 border-rose-200";
            Icon = ShieldAlert;
            label = "Abstention Refusal";
          }

          return (
            <button
              key={scenario.id}
              onClick={() => onSelectScenario(scenario)}
              disabled={disabled}
              className="text-left p-3 rounded-lg border border-steel-200 bg-white hover:border-safety-400 hover:shadow-sm transition-all group disabled:opacity-50 disabled:cursor-not-allowed flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeColor}`}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{label}</span>
                  </span>
                  <span className="text-[10px] font-mono text-steel-400">
                    {scenario.projectId}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-steel-800 group-hover:text-safety-700 line-clamp-1">
                  {scenario.title}
                </h4>
                <p className="text-[11px] text-steel-500 mt-1 line-clamp-2">
                  &ldquo;{scenario.query}&rdquo;
                </p>
              </div>

              <div className="mt-2.5 pt-2 border-t border-steel-100 flex items-center justify-between text-[10px] text-steel-400">
                <span>Jurisdiction: {scenario.jurisdiction}</span>
                <span className="font-semibold text-safety-600 group-hover:underline">
                  Load query &rarr;
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
