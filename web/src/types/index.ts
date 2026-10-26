// All shared TypeScript types for AICTE Validator
// All data is synthetic

export interface User {
  user_id: string;
  username: string;
  role: UserRole;
  institution_id: string | null;
}

export type UserRole =
  | "institution_user"
  | "scrutiny_officer"
  | "supervisor"
  | "auditor"
  | "rules_admin"
  | "sysadmin";

export type ApplicationStage =
  | "SUBMITTED"
  | "INGESTING"
  | "EXTRACTING"
  | "UNDER_REVIEW"
  | "DECISION_PENDING"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN";

export type TernaryResult = "TRUE" | "FALSE" | "UNKNOWN";

export type DocStatus =
  | "INGESTED"
  | "VERIFIED"
  | "MISMATCH_DETECTED"
  | "EXPIRED"
  | "VERIFICATION_PENDING"
  | "SOURCE_UNAVAILABLE"
  | "MANUAL_REVIEW_REQUIRED"
  | "UNREADABLE";

export interface ExtractedField {
  field: string;
  value: string;
  normalized?: string;
  confidence: number;
  result: TernaryResult;
  page?: number;
  extractor?: string;
}

export interface BoundingBox {
  doc_id: string;
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Document {
  id: string;
  application_id: string;
  type_declared: string;
  type_detected?: string;
  file_ref?: string;
  sha256?: string;
  page_count: number;
  status?: DocStatus;
  extracted_fields?: ExtractedField[];
}

export interface Finding {
  id: string;
  application_id: string;
  source_code: string;
  tier: number;
  result: TernaryResult;
  reason: string;
  recheck_recipe?: string;
  clause_ref?: string;
  evidence?: {
    documents?: string[];
    fields?: string[];
    bounding_boxes?: BoundingBox[];
    status?: string;
    last_attempt?: string;
  };
  created_at?: string;
}

export interface ReviewerAction {
  id: string;
  finding_id: string;
  action: "accept" | "dismiss" | "escalate" | "request_info";
  reason: string;
  user_id: string;
  created_at: string;
}

export interface Application {
  id: string;
  institution_id: string;
  institution_name?: string;
  institution_code?: string;
  city?: string;
  state?: string;
  declared_category: string;
  academic_year: string;
  stage: ApplicationStage;
  risk_score?: number;
  findings_count?: number;
  unknowns_count?: number;
  verified_count?: number;
  checked_docs_count?: number;
  created_at?: string;
  synthetic_data?: boolean;
}

export interface ReviewItem {
  id: string;
  application_id: string;
  institution_name?: string;
  institution_code?: string;
  level: 0 | 1 | 2 | 3;
  status: "PENDING" | "ASSIGNED" | "IN_REVIEW" | "RESOLVED";
  assigned_to?: string;
  assigned_to_username?: string;
  created_at: string;
  category?: string;
  findings_count?: number;
}

export interface Alert {
  id: string;
  type: string;
  application_id?: string;
  institution_name?: string;
  message: string;
  severity: "low" | "medium" | "high" | "critical";
  delivered_at?: string;
  acknowledged_by?: string;
  created_at: string;
}

export interface AuditEntry {
  seq: number;
  action: string;
  table_name?: string;
  row_id?: string;
  actor?: string;
  data?: Record<string, unknown>;
  hash: string;
  prev_hash?: string | null;
  created_at: string;
}

export interface Rule {
  id: string;
  name: string;
  description: string;
  clause_ref: string;
  severity: "MUST" | "SHOULD" | "COULD";
  status: "DRAFT" | "ACTIVE" | "RETIRED";
  version: string;
  conditions?: Array<{
    field: string;
    operator: string;
    target_value: unknown;
  }>;
  is_placeholder?: boolean;
}

export interface WhatIfResult {
  rule_id: string;
  rule_name: string;
  result: TernaryResult;
  flipped_from?: TernaryResult;
  is_placeholder: boolean;
  reason: string;
}

export interface Report {
  report_id: string;
  application_id: string;
  generated_at: string;
  summary: {
    total_documents: number;
    verified: number;
    findings: number;
    unknowns: number;
    verification_debt: number;
  };
  findings: Finding[];
  recommendation: string;
  overall_result: TernaryResult;
  is_synthetic: boolean;
}

export interface SystemMode {
  mode: "NORMAL" | "DEGRADED" | "MAINTENANCE";
  changed_at: string;
  reason?: string;
}

export interface HeadHash {
  date: string;
  hash: string;
  entry_count: number;
}
