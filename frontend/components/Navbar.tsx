"use client";

import React from "react";
import { ShieldCheck, HardHat, Activity, AlertCircle, Database } from "lucide-react";

interface NavbarProps {
  backendOnline: boolean;
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
  selectedProject: string;
  onSelectProject: (proj: string) => void;
  selectedJurisdiction: string;
  onSelectJurisdiction: (jur: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  backendOnline,
  isDemoMode,
  onToggleDemoMode,
  selectedProject,
  onSelectProject,
  selectedJurisdiction,
  onSelectJurisdiction,
}) => {
  return (
    <header className="border-b border-steel-200 bg-white sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Identity */}
          <div className="flex items-center space-x-3">
            <div className="bg-safety-500 text-white p-2 rounded-lg shadow-inner flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight text-steel-900">
                  SITE SHIELD <span className="text-safety-600">AI</span>
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider bg-steel-100 text-steel-700 border border-steel-200">
                  v0.1.0
                </span>
              </div>
              <p className="text-xs text-steel-500 font-medium hidden sm:block">
                Construction Regulatory Compliance & Grounded Retrieval
              </p>
            </div>
          </div>

          {/* Project & Jurisdiction Selectors */}
          <div className="hidden md:flex items-center space-x-3 text-sm">
            <div className="flex items-center space-x-1.5 bg-steel-50 border border-steel-200 rounded-md px-2.5 py-1.5">
              <HardHat className="w-4 h-4 text-steel-500" />
              <span className="text-xs text-steel-500 font-semibold uppercase">Project:</span>
              <select
                value={selectedProject}
                onChange={(e) => onSelectProject(e.target.value)}
                aria-label="Select Project"
                className="bg-transparent text-steel-800 font-medium text-xs focus:outline-none cursor-pointer"
              >
                <option value="#104">#104 (Metro Line 4)</option>
                <option value="#108">#108 (Commercial Tower B)</option>
                <option value="ALL">All Projects</option>
              </select>
            </div>

            <div className="flex items-center space-x-1.5 bg-steel-50 border border-steel-200 rounded-md px-2.5 py-1.5">
              <Database className="w-4 h-4 text-steel-500" />
              <span className="text-xs text-steel-500 font-semibold uppercase">Jurisdiction:</span>
              <select
                value={selectedJurisdiction}
                onChange={(e) => onSelectJurisdiction(e.target.value)}
                aria-label="Select Jurisdiction"
                className="bg-transparent text-steel-800 font-medium text-xs focus:outline-none cursor-pointer"
              >
                <option value="IN-KA">IN-KA (India - Karnataka)</option>
                <option value="US-CA">US-CA (California CBC)</option>
                <option value="GLOBAL">Global / Unspecified</option>
              </select>
            </div>
          </div>

          {/* Right Status Controls */}
          <div className="flex items-center space-x-3">
            {/* Backend Connectivity Status */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                backendOnline
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : isDemoMode
                  ? "bg-amber-50 text-amber-800 border-amber-300"
                  : "bg-rose-50 text-rose-700 border-rose-200"
              }`}
              title={
                backendOnline
                  ? "FastAPI Backend is connected at http://localhost:8000"
                  : isDemoMode
                  ? "Demo Mode Active: Using verified demonstration data"
                  : "Backend disconnected. Toggle Demo Mode to test UI."
              }
            >
              <Activity
                className={`w-3.5 h-3.5 ${
                  backendOnline
                    ? "text-emerald-500 animate-pulse"
                    : isDemoMode
                    ? "text-amber-500"
                    : "text-rose-500"
                }`}
              />
              <span className="hidden sm:inline">
                {backendOnline ? "API Online" : isDemoMode ? "Demo Mode" : "API Offline"}
              </span>
            </div>

            {/* Demo Mode Toggle Button */}
            <button
              onClick={onToggleDemoMode}
              className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors border ${
                isDemoMode
                  ? "bg-safety-500 text-white border-safety-600 shadow-sm"
                  : "bg-white text-steel-600 border-steel-300 hover:bg-steel-50"
              }`}
              title="Toggle Demonstration Mode with realistic test scenarios"
            >
              {isDemoMode ? "Demo On" : "Demo Off"}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
