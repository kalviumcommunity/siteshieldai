export type DocumentType =
  | "code"
  | "spec"
  | "report"
  | "safety_manual"
  | "drawing_note"
  | "addendum"
  | "other";

export type ContentType = "prose" | "table" | "mixed";

export type ExtractionMethod = "native" | "ocr" | "hybrid";

export type QueryStatus = "supported" | "conflict_flagged" | "abstained";

export type ConflictType =
  | "version_supersession"
  | "report_vs_code_divergence"
  | "cross_document_value_mismatch";

export interface QueryFilters {
  project_id?: string | null;
  jurisdiction?: string | null;
  doc_types?: DocumentType[] | null;
  include_superseded: boolean;
}

export interface QueryRequest {
  query: string;
  filters?: QueryFilters;
  top_k?: number;
  stream?: boolean;
}

export interface CitationItem {
  evidence_id: string;
  chunk_id: string;
  doc_id: string;
  doc_title: string;
  doc_type: DocumentType;
  version: string;
  effective_date?: string | null;
  jurisdiction: string;
  project_id?: string | null;
  section_id?: string | null;
  section_path: string[];
  page_start: number;
  page_end: number;
  content_type: ContentType;
  extraction_method: ExtractionMethod;
  retrieval_score: number;
  text_verbatim: string;
}

export interface ConflictSourceRef {
  doc_id: string;
  doc_title: string;
  version: string;
  effective_date?: string | null;
  section_id?: string | null;
  page_start: number;
  excerpt: string;
}

export interface ConflictItem {
  conflict_type: ConflictType;
  source_a: ConflictSourceRef;
  source_b: ConflictSourceRef;
  summary: string;
  precedence_note: string;
}

export interface LatencyBreakdown {
  embedding: number;
  retrieval: number;
  generation: number;
  validation: number;
  total: number;
}

export interface QueryResponse {
  query_id: string;
  status: QueryStatus;
  answer: string;
  citations: CitationItem[];
  conflicts: ConflictItem[];
  abstention_reason?: string | null;
  latency_ms: LatencyBreakdown;
  disclaimer: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}
