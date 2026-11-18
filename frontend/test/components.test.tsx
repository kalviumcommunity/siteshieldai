import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Navbar } from "@/components/Navbar";
import { SafetyBanner } from "@/components/SafetyBanner";
import { QueryInput } from "@/components/QueryInput";
import { AnswerSection } from "@/components/AnswerSection";
import { CitationCard } from "@/components/CitationCard";
import { ExcerptViewer } from "@/components/ExcerptViewer";
import { ConflictBanner } from "@/components/ConflictBanner";
import { AbstentionBanner } from "@/components/AbstentionBanner";
import { TelemetryBar } from "@/components/TelemetryBar";
import { DEMO_SCENARIOS } from "@/lib/demoData";

describe("Frontend UI Components & Workflow", () => {
  it("Navbar renders brand, status pill, and selector options", () => {
    const handleToggleDemo = vi.fn();
    const handleSelectProject = vi.fn();
    const handleSelectJurisdiction = vi.fn();

    render(
      <Navbar
        backendOnline={true}
        isDemoMode={false}
        onToggleDemoMode={handleToggleDemo}
        selectedProject="#104"
        onSelectProject={handleSelectProject}
        selectedJurisdiction="IN-KA"
        onSelectJurisdiction={handleSelectJurisdiction}
      />
    );

    expect(screen.getByText(/SITE SHIELD/i)).toBeInTheDocument();
    expect(screen.getByText(/API Online/i)).toBeInTheDocument();
    expect(screen.getByText(/#104/i)).toBeInTheDocument();
  });

  it("SafetyBanner shows official precaution and demo badge when active", () => {
    render(<SafetyBanner isDemoMode={true} />);
    expect(screen.getByText(/Safety Precaution:/i)).toBeInTheDocument();
    expect(
      screen.getByText(/DEMONSTRATION DATA MODE ACTIVE/i)
    ).toBeInTheDocument();
  });

  it("QueryInput triggers submission and filters toggle", () => {
    const handleChangeQuery = vi.fn();
    const handleSubmit = vi.fn();
    const handleChangeFilters = vi.fn();
    const handleReset = vi.fn();

    render(
      <QueryInput
        query="What is curing duration?"
        onChangeQuery={handleChangeQuery}
        onSubmit={handleSubmit}
        isLoading={false}
        filters={{
          project_id: "#104",
          jurisdiction: "IN-KA",
          doc_types: null,
          include_superseded: false,
        }}
        onChangeFilters={handleChangeFilters}
        onReset={handleReset}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /Audit Question/i });
    expect(submitBtn).toBeEnabled();
    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledTimes(1);

    // Toggle filters tray
    const filterBtn = screen.getByRole("button", { name: /Filters/i });
    fireEvent.click(filterBtn);
    expect(
      screen.getByText(/Project Scoping \(OQ-06 Data Isolation\)/i)
    ).toBeInTheDocument();
  });

  it("AnswerSection renders answer text with clickable citation badges", () => {
    const handleSelectCitation = vi.fn();
    const demoResponse = DEMO_SCENARIOS[0].response;

    render(
      <AnswerSection
        answer={demoResponse.answer}
        status={demoResponse.status}
        onSelectCitation={handleSelectCitation}
        selectedEvidenceId="E1"
      />
    );

    expect(screen.getByText(/Compliance Assessment/i)).toBeInTheDocument();
    expect(screen.getByText(/14 days/i)).toBeInTheDocument();

    // Click inline citation tag [E1]
    const citationBtn = screen.getByRole("button", { name: /\[E1\]/i });
    fireEvent.click(citationBtn);
    expect(handleSelectCitation).toHaveBeenCalledWith("E1");
  });

  it("CitationCard displays full chunk metadata and selection action", () => {
    const handleSelect = vi.fn();
    const citation = DEMO_SCENARIOS[0].response.citations[0];

    render(
      <CitationCard
        citation={citation}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    expect(screen.getByText(/\[E1\]/i)).toBeInTheDocument();
    expect(screen.getByText(citation.doc_title)).toBeInTheDocument();
    expect(screen.getByText(/Pages 14–14/i)).toBeInTheDocument();

    const inspectBtn = screen.getByText(/Inspect Excerpt/i);
    fireEvent.click(inspectBtn);
    expect(handleSelect).toHaveBeenCalledTimes(1);
  });

  it("ExcerptViewer renders verbatim extracted text and hierarchy breadcrumbs", () => {
    const handleClose = vi.fn();
    const citation = DEMO_SCENARIOS[0].response.citations[0];

    render(<ExcerptViewer citation={citation} onClose={handleClose} />);

    expect(
      screen.getByText(/Source Provenance Inspector/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Verbatim Chunk Text/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/NOT REAL REGULATION/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Grounded & Verified/i)).toBeInTheDocument();
  });

  it("ConflictBanner displays side-by-side comparison and precedence notes", () => {
    const conflicts = DEMO_SCENARIOS[1].response.conflicts;

    render(<ConflictBanner conflicts={conflicts} />);

    expect(
      screen.getByText(/Regulatory Discrepancy & Conflict Detected/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Source Document A/i)).toBeInTheDocument();
    expect(screen.getByText(/Source Document B/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Governing Precedence Ruling:/i)
    ).toBeInTheDocument();
  });

  it("AbstentionBanner presents refusal reason and actionable recommendations", () => {
    const reason =
      "No certified fireproofing submittals found in indexed project corpus.";

    render(<AbstentionBanner reason={reason} query="Fireproofing thickness?" />);

    expect(
      screen.getByText(/Safety Abstention: Insufficient Regulatory Evidence/i)
    ).toBeInTheDocument();
    expect(screen.getByText(reason)).toBeInTheDocument();
    expect(screen.getByText(/Upload Governing Code:/i)).toBeInTheDocument();
  });

  it("TelemetryBar renders latency telemetry and disclaimer", () => {
    const latency = DEMO_SCENARIOS[0].response.latency_ms;

    render(
      <TelemetryBar
        queryId="qry_test_999"
        latency={latency}
        disclaimer="Assistive system disclaimer test."
      />
    );

    expect(screen.getByText(/qry_test_999/i)).toBeInTheDocument();
    expect(screen.getByText(/Total: 87ms/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Assistive system disclaimer test./i)
    ).toBeInTheDocument();
  });

  it("Executes complete question-to-citation inspection workflow in Home component", async () => {
    // Import Home component dynamically or directly
    const Home = (await import("@/app/page")).default;

    // Mock global fetch to return the supported compliance scenario
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/health")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: "ok", service: "Site Shield AI", version: "0.1.0" }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => DEMO_SCENARIOS[0].response,
      });
    });

    render(<Home />);

    // 1. Verify initial empty state
    expect(screen.getByText(/No Question Audited Yet/i)).toBeInTheDocument();

    // 2. Click a demonstration scenario card
    const demoCard = screen.getByText(/Foundation Slab Curing \(Grounded Answer\)/i);
    await act(async () => {
      fireEvent.click(demoCard);
    });

    // 3. Verify grounded answer is presented with [E1] citation
    expect(screen.getByText(/Compliance Assessment/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/Under high moisture conditions, foundation slabs shall be cured/i).length
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("button", { name: /\[E1\]/i }).length).toBeGreaterThanOrEqual(1);

    // 4. Verify citation cards are rendered
    expect(screen.getAllByText(/Foundation Concrete Specification \(DEMO\)/i).length).toBeGreaterThanOrEqual(1);

    // 5. Verify excerpt viewer is populated with verbatim text
    expect(screen.getByText(/Source Provenance Inspector/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Clause 4.2.1 Under high moisture conditions/i).length).toBeGreaterThanOrEqual(1);

    // 6. Switch to citation [E2] by clicking its tag
    const e2Btns = screen.getAllByRole("button", { name: /\[E2\]/i });
    await act(async () => {
      fireEvent.click(e2Btns[0]);
    });

    // 7. Verify excerpt viewer updates to show E2 text
    expect(screen.getAllByText(/Clause 4.2.2 Clear cover for foundation reinforcement/i).length).toBeGreaterThanOrEqual(1);
  });
});
