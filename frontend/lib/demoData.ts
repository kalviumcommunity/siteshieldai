import { QueryResponse } from "@/types/compliance";

export interface DemoScenario {
  id: string;
  title: string;
  query: string;
  projectId: string;
  jurisdiction: string;
  category: "supported" | "conflict" | "abstention";
  response: QueryResponse;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "curing-high-moisture",
    title: "Foundation Slab Curing (Grounded Answer)",
    query: "What is the minimum curing duration for foundation slabs under high moisture conditions?",
    projectId: "#104",
    jurisdiction: "IN-KA",
    category: "supported",
    response: {
      query_id: "demo_qry_supported_104",
      status: "supported",
      answer:
        "Under high moisture conditions, foundation slabs shall be cured for a minimum of 14 days [E1]. Reinforcement clear cover for all foundation elements exposed to groundwater shall maintain at least 50 mm [E2].",
      citations: [
        {
          evidence_id: "E1",
          chunk_id: "demo_chk_fnd_curing_01",
          doc_id: "doc_spec_foundation_v2",
          doc_title: "Foundation Concrete Specification (DEMO)",
          doc_type: "spec",
          version: "v2.0",
          effective_date: "2024-02-01",
          jurisdiction: "IN-KA",
          project_id: "#104",
          section_id: "Clause 4.2.1",
          section_path: ["4.0 Concrete Curing Specification", "4.2 High Moisture Conditions"],
          page_start: 14,
          page_end: 14,
          content_type: "prose",
          extraction_method: "native",
          retrieval_score: 0.8842,
          text_verbatim:
            "[DEMONSTRATION DATA ONLY — NOT REAL REGULATION]\nClause 4.2.1 Under high moisture conditions, foundation slabs shall be cured for 14 days prior to backfilling or heavy loading. Curing shall be maintained continuously using wet burlap coverings.",
        },
        {
          evidence_id: "E2",
          chunk_id: "demo_chk_rebar_cover_02",
          doc_id: "doc_spec_foundation_v2",
          doc_title: "Foundation Concrete Specification (DEMO)",
          doc_type: "spec",
          version: "v2.0",
          effective_date: "2024-02-01",
          jurisdiction: "IN-KA",
          project_id: "#104",
          section_id: "Clause 4.2.2",
          section_path: ["4.0 Concrete Curing Specification", "4.2 Cover & Reinforcement"],
          page_start: 15,
          page_end: 15,
          content_type: "prose",
          extraction_method: "native",
          retrieval_score: 0.8125,
          text_verbatim:
            "[DEMONSTRATION DATA ONLY — NOT REAL REGULATION]\nClause 4.2.2 Clear cover for foundation reinforcement shall be at least 50 mm against formwork and 75 mm against soil in wet ground environments.",
        },
      ],
      conflicts: [],
      abstention_reason: null,
      latency_ms: {
        embedding: 14,
        retrieval: 22,
        generation: 48,
        validation: 3,
        total: 87,
      },
      disclaimer:
        "DEMONSTRATION DATA ONLY: Site Shield AI is an assistive decision-support tool. All citations, clauses, and calculations must be verified by a licensed Engineer of Record before construction execution.",
    },
  },
  {
    id: "curing-conflict",
    title: "Curing Duration Conflict (Spec vs Inspection Report)",
    query: "What is the mandatory foundation concrete curing period?",
    projectId: "#104",
    jurisdiction: "IN-KA",
    category: "conflict",
    response: {
      query_id: "demo_qry_conflict_209",
      status: "conflict_flagged",
      answer:
        "Governing Project Specification requires foundation slabs to be cured for 14 days [E1]. Historical inspection report 'Site Inspection Report 01' (v1.0) noted: Foundation slabs were cured for 7 days before formwork removal [E2].",
      citations: [
        {
          evidence_id: "E1",
          chunk_id: "demo_chk_spec_cur_01",
          doc_id: "doc_gov_spec_v2",
          doc_title: "Governing Concrete Specification (DEMO)",
          doc_type: "spec",
          version: "v2.0",
          effective_date: "2024-01-01",
          jurisdiction: "IN-KA",
          project_id: "#104",
          section_id: "Clause 3.1",
          section_path: ["3.0 Curing Protocol"],
          page_start: 6,
          page_end: 6,
          content_type: "prose",
          extraction_method: "native",
          retrieval_score: 0.912,
          text_verbatim:
            "[DEMONSTRATION DATA ONLY — NOT REAL REGULATION]\nClause 3.1 Foundation slabs shall be cured for 14 days under continuous wet conditions. No premature loading or stripping is permitted.",
        },
        {
          evidence_id: "E2",
          chunk_id: "demo_chk_rep_cur_02",
          doc_id: "doc_site_rep_01",
          doc_title: "Site Inspection Report 01 (DEMO)",
          doc_type: "report",
          version: "v1.0",
          effective_date: "2023-10-12",
          jurisdiction: "IN-KA",
          project_id: "#104",
          section_id: "Field Observation 4",
          section_path: ["Inspection Notes", "Pour Area B"],
          page_start: 2,
          page_end: 2,
          content_type: "prose",
          extraction_method: "native",
          retrieval_score: 0.798,
          text_verbatim:
            "[DEMONSTRATION DATA ONLY — NOT REAL REGULATION]\nField Observation 4: Subcontractor stripped forms early. Foundation slabs were cured for 7 days before formwork removal. Non-conformance log opened.",
        },
      ],
      conflicts: [
        {
          conflict_type: "report_vs_code_divergence",
          source_a: {
            doc_id: "doc_gov_spec_v2",
            doc_title: "Governing Concrete Specification (DEMO)",
            version: "v2.0",
            effective_date: "2024-01-01",
            section_id: "Clause 3.1",
            page_start: 6,
            excerpt: "Foundation slabs shall be cured for 14 days.",
          },
          source_b: {
            doc_id: "doc_site_rep_01",
            doc_title: "Site Inspection Report 01 (DEMO)",
            version: "v1.0",
            effective_date: "2023-10-12",
            section_id: "Field Observation 4",
            page_start: 2,
            excerpt: "Foundation slabs were cured for 7 days before formwork removal.",
          },
          summary:
            "Governing Specification requires 14 days curing, whereas Historical Inspection Report records 7 days curing on site.",
          precedence_note:
            "Governing specifications and building codes take legal precedence over historical site inspection reports. Past inspection notes document historical site deviations and do not modify project specifications.",
        },
      ],
      abstention_reason: null,
      latency_ms: {
        embedding: 16,
        retrieval: 25,
        generation: 52,
        validation: 4,
        total: 97,
      },
      disclaimer:
        "DEMONSTRATION DATA ONLY: Site Shield AI flagged a regulatory divergence. Please verify with the Project Quality Manager and Engineer of Record.",
    },
  },
  {
    id: "unsupported-abstention",
    title: "Uncovered Query (Safety Abstention Gate)",
    query: "What is the fireproofing coating thickness required for steel truss assembly T-9?",
    projectId: "#104",
    jurisdiction: "IN-KA",
    category: "abstention",
    response: {
      query_id: "demo_qry_abstain_311",
      status: "abstained",
      answer:
        "The retrieved documents do not contain sufficient regulatory evidence to answer this requirement.",
      citations: [],
      conflicts: [],
      abstention_reason:
        "Gate 1/2 Abstention: The indexed project corpus contains structural foundation specifications and excavation manuals, but no certified fireproofing submittals or structural steel fire-resistance ratings for assembly T-9.",
      latency_ms: {
        embedding: 11,
        retrieval: 18,
        generation: 2,
        validation: 1,
        total: 32,
      },
      disclaimer:
        "DEMONSTRATION DATA ONLY: Site Shield AI refused to extrapolate or fabricate safety-critical structural fireproofing requirements. Consult certified structural drawings and UL fire resistance assemblies.",
    },
  },
];
