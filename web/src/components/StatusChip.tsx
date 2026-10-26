import type { TernaryResult, ApplicationStage, DocStatus } from "../types";

type AnyStatus = TernaryResult | ApplicationStage | DocStatus | string;

function chipClass(s: AnyStatus): string {
  const m: Record<string, string> = {
    TRUE: "chip--true",
    FALSE: "chip--false",
    UNKNOWN: "chip--unknown",
    VERIFIED: "chip--verified",
    MISMATCH_DETECTED: "chip--mismatch",
    EXPIRED: "chip--expired",
    VERIFICATION_PENDING: "chip--pending",
    SOURCE_UNAVAILABLE: "chip--unavailable",
    MANUAL_REVIEW_REQUIRED: "chip--review",
    UNREADABLE: "chip--mismatch",
    INGESTED: "chip--pending",
    SUBMITTED: "chip--pending",
    INGESTING: "chip--pending",
    EXTRACTING: "chip--pending",
    UNDER_REVIEW: "chip--review",
    DECISION_PENDING: "chip--review",
    APPROVED: "chip--verified",
    REJECTED: "chip--mismatch",
    WITHDRAWN: "chip--unknown",
    DRAFT: "chip--unknown",
    ACTIVE: "chip--verified",
    RETIRED: "chip--expired",
    MUST: "chip--false",
    SHOULD: "chip--review",
    COULD: "chip--unknown",
    NORMAL: "chip--verified",
    DEGRADED: "chip--mismatch",
    MAINTENANCE: "chip--review",
    low: "chip--unknown",
    medium: "chip--review",
    high: "chip--expired",
    critical: "chip--false",
    PENDING: "chip--unknown",
    ASSIGNED: "chip--pending",
    IN_REVIEW: "chip--review",
    RESOLVED: "chip--verified",
  };
  return m[s] || "chip--unknown";
}

export function tierClass(t: number): string {
  return `chip--tier${t}`;
}

export default function StatusChip({
  status,
  small,
}: {
  status: AnyStatus;
  small?: boolean;
}) {
  return (
    <span
      className={`chip ${chipClass(status)}`}
      style={small ? { fontSize: 10, padding: "2px 8px" } : {}}
    >
      {String(status).replace(/_/g, " ")}
    </span>
  );
}
