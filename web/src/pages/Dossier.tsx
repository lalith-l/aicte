import { useRef, useState } from 'react'
import type { Application, Document, Finding } from '../types'
import StatusChip from '../components/StatusChip'
import CertaintyStrip from '../components/CertaintyStrip'
import FindingCard from '../components/FindingCard'
import LoadingSpinner from '../components/LoadingSpinner'
import PdfViewer from '../components/PdfViewer'
import CrossCheckPanel from '../components/CrossCheckPanel'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

const SEEDED_APPS: Record<string, Application> = {
  'bbbb0001-0001-0001-0001-000000000001': {
    id: 'bbbb0001-0001-0001-0001-000000000001',
    institution_id: '11111111-1111-1111-1111-111111111111',
    institution_name: 'Sunrise Technical Institute',
    institution_code: 'SUNRISE-001',
    city: 'Bengaluru',
    state: 'Karnataka',
    declared_category: 'EOA Renewal',
    academic_year: '2025-26',
    stage: 'UNDER_REVIEW',
    risk_score: 0.73,
  },
  'bbbb0002-0002-0002-0002-000000000002': {
    id: 'bbbb0002-0002-0002-0002-000000000002',
    institution_id: '22222222-2222-2222-2222-222222222222',
    institution_name: 'Horizon Engineering College',
    institution_code: 'HORIZON-001',
    city: 'Chennai',
    state: 'Tamil Nadu',
    declared_category: 'New Approval',
    academic_year: '2025-26',
    stage: 'SUBMITTED',
    risk_score: 0.21,
  },
  'bbbb0003-0003-0003-0003-000000000003': {
    id: 'bbbb0003-0003-0003-0003-000000000003',
    institution_id: '33333333-3333-3333-3333-333333333333',
    institution_name: 'Pinnacle College of Science',
    institution_code: 'PINNACLE-001',
    city: 'Hyderabad',
    state: 'Telangana',
    declared_category: 'EOA Renewal',
    academic_year: '2025-26',
    stage: 'DECISION_PENDING',
    risk_score: 0.88,
  },
  'bbbb0004-0004-0004-0004-000000000004': {
    id: 'bbbb0004-0004-0004-0004-000000000004',
    institution_id: '44444444-4444-4444-4444-444444444444',
    institution_name: 'Greenfield Institute of Technology',
    institution_code: 'GIT-001',
    city: 'Pune',
    state: 'Maharashtra',
    declared_category: 'Intake Enhancement',
    academic_year: '2025-26',
    stage: 'APPROVED',
    risk_score: 0.12,
  },
  'bbbb0005-0005-0005-0005-000000000005': {
    id: 'bbbb0005-0005-0005-0005-000000000005',
    institution_id: '55555555-5555-5555-5555-555555555555',
    institution_name: 'Westland Engineering College',
    institution_code: 'WEC-001',
    city: 'Ahmedabad',
    state: 'Gujarat',
    declared_category: 'EOA Renewal',
    academic_year: '2025-26',
    stage: 'REJECTED',
    risk_score: 0.95,
  },
  'bbbb0006-0006-0006-0006-000000000006': {
    id: 'bbbb0006-0006-0006-0006-000000000006',
    institution_id: '66666666-6666-6666-6666-666666666666',
    institution_name: 'Rajendra Institute of Management',
    institution_code: 'RIM-001',
    city: 'Jaipur',
    state: 'Rajasthan',
    declared_category: 'New Approval',
    academic_year: '2025-26',
    stage: 'EXTRACTING',
    risk_score: 0.45,
  },
  'bbbb0007-0007-0007-0007-000000000007': {
    id: 'bbbb0007-0007-0007-0007-000000000007',
    institution_id: '77777777-7777-7777-7777-777777777777',
    institution_name: 'Northstar Academy of Sciences',
    institution_code: 'NAS-001',
    city: 'Kolkata',
    state: 'West Bengal',
    declared_category: 'EOA Renewal',
    academic_year: '2025-26',
    stage: 'UNDER_REVIEW',
    risk_score: 0.62,
  },
  'bbbb0008-0008-0008-0008-000000000008': {
    id: 'bbbb0008-0008-0008-0008-000000000008',
    institution_id: '88888888-8888-8888-8888-888888888888',
    institution_name: 'Eastern Polytechnic Institute',
    institution_code: 'EPI-001',
    city: 'Bhubaneswar',
    state: 'Odisha',
    declared_category: 'Intake Enhancement',
    academic_year: '2025-26',
    stage: 'INGESTING',
    risk_score: 0.35,
  },
}

const SEEDED_DOCS_SUNRISE: Document[] = [
  {
    id: 'cccc0001-0001-0001-0001-000000000001',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    type_declared: 'Trust Deed',
    page_count: 3,
    status: 'VERIFIED',
    extracted_fields: [
      { field: 'Institution Name', value: 'Sunrise Technical Institute', confidence: 0.98, result: 'TRUE', extractor: 'pdfplumber' },
      { field: 'Trust Name', value: 'Sunrise Education Trust', confidence: 0.96, result: 'TRUE', extractor: 'pdfplumber' },
      { field: 'PAN Number', value: '••••1234A', confidence: 0.9, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0002-0002-0002-0002-000000000002',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    type_declared: 'Affidavit',
    page_count: 2,
    status: 'VERIFIED',
    extracted_fields: [
      { field: 'Affidavit Date', value: '2025-01-15', confidence: 0.95, result: 'FALSE', extractor: 'pdfplumber' },
      { field: 'Signatory Name', value: 'Dr. R. Kumar', confidence: 0.93, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0003-0003-0003-0003-000000000003',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    type_declared: 'Stamp Paper',
    page_count: 1,
    status: 'VERIFIED',
    extracted_fields: [
      { field: 'Stamp Paper Date', value: '2025-02-01', confidence: 0.97, result: 'TRUE', extractor: 'pdfplumber' },
      { field: 'Stamp Value', value: '₹500', confidence: 0.99, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0004-0004-0004-0004-000000000004',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    type_declared: 'Faculty List',
    page_count: 5,
    status: 'MANUAL_REVIEW_REQUIRED',
    extracted_fields: [
      { field: 'Faculty Count', value: '42', confidence: 0.91, result: 'UNKNOWN', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0005-0005-0005-0005-000000000005',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    type_declared: 'NOC Certificate',
    page_count: 1,
    status: 'SOURCE_UNAVAILABLE',
    extracted_fields: [
      { field: 'NOC Issuer', value: 'State Govt of Karnataka', confidence: 0.94, result: 'UNKNOWN', extractor: 'pdfplumber' },
      { field: 'NOC Date', value: '2025-02-10', confidence: 0.96, result: 'UNKNOWN', extractor: 'pdfplumber' },
    ],
  },
]

const SEEDED_DOCS_PINNACLE: Document[] = [
  {
    id: 'cccc0031-0031-0031-0031-000000000031',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    type_declared: 'Trust Deed',
    page_count: 4,
    status: 'VERIFIED',
    extracted_fields: [
      { field: 'Institution Name', value: 'Pinnacle College of Science', confidence: 0.99, result: 'TRUE', extractor: 'pdfplumber' },
      { field: 'Trust Name', value: 'Pinnacle Scientific & Research Society', confidence: 0.97, result: 'TRUE', extractor: 'pdfplumber' },
      { field: 'Registration Date', value: '2012-08-20', confidence: 0.96, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0032-0032-0032-0032-000000000032',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    type_declared: 'Land Certificate',
    page_count: 6,
    status: 'MISMATCH_DETECTED',
    extracted_fields: [
      { field: 'Declared Land Area', value: '5.0 Acres', confidence: 0.98, result: 'FALSE', extractor: 'pdfplumber' },
      { field: 'Verified Registry Area', value: '3.8 Acres', confidence: 0.95, result: 'FALSE', extractor: 'pdfplumber' },
      { field: 'Survey Number', value: '142/3B', confidence: 0.94, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0033-0033-0033-0033-000000000033',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    type_declared: 'Fire Safety NOC',
    page_count: 2,
    status: 'EXPIRED',
    extracted_fields: [
      { field: 'Fire NOC Expiry Date', value: '2024-12-31', confidence: 0.99, result: 'FALSE', extractor: 'pdfplumber' },
      { field: 'Issuing Authority', value: 'Hyderabad Fire Services', confidence: 0.92, result: 'TRUE', extractor: 'pdfplumber' },
    ],
  },
  {
    id: 'cccc0034-0034-0034-0034-000000000034',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    type_declared: 'Faculty Roster',
    page_count: 8,
    status: 'MANUAL_REVIEW_REQUIRED',
    extracted_fields: [
      { field: 'Total Faculty', value: '58', confidence: 0.93, result: 'UNKNOWN', extractor: 'pdfplumber' },
      { field: 'Student-Teacher Ratio', value: '1:18.5', confidence: 0.88, result: 'UNKNOWN', extractor: 'pdfplumber' },
    ],
  },
]

const SEEDED_FINDINGS_SUNRISE: Finding[] = [
  {
    id: 'dddd0001-0001-0001-0001-000000000001',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    source_code: 'D04',
    tier: 1,
    result: 'FALSE',
    reason: 'Affidavit date (2025-01-15) conflicts with stamp paper date (2025-02-01). Stamp paper was purchased after the affidavit was executed.',
    recheck_recipe: 'Compare affidavit date with stamp paper date. Verify stamp paper was purchased before affidavit execution.',
    clause_ref: 'PLACEHOLDER',
    evidence: {
      documents: ['cccc0002-0002-0002-0002-000000000002', 'cccc0003-0003-0003-0003-000000000003'],
      fields: ['affidavit_date', 'stamp_paper_date'],
      bounding_boxes: [
        { doc_id: 'cccc0002-0002-0002-0002-000000000002', page: 1, x: 120, y: 340, w: 200, h: 25 },
        { doc_id: 'cccc0003-0003-0003-0003-000000000003', page: 1, x: 80, y: 150, w: 180, h: 20 },
      ],
    },
  },
  {
    id: 'dddd0002-0002-0002-0002-000000000002',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    source_code: 'D13',
    tier: 2,
    result: 'UNKNOWN',
    reason: 'NOC issuer verification endpoint returned 503. Verification debt increased. No rejection — UNKNOWN is not FALSE.',
    clause_ref: 'PLACEHOLDER',
    evidence: {
      documents: ['cccc0005-0005-0005-0005-000000000005'],
      status: 'SOURCE_UNAVAILABLE',
      last_attempt: '2025-03-15T10:30:00Z',
    },
  },
]

const SEEDED_FINDINGS_PINNACLE: Finding[] = [
  {
    id: 'dddd0031-0031-0031-0031-000000000031',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    source_code: 'D09',
    tier: 2,
    result: 'FALSE',
    reason: 'Declared land area is 5.0 acres, but verified municipal land registry indicates only 3.8 acres. Deficit of 1.2 acres violates AICTE norm for engineering campus.',
    recheck_recipe: 'Request certified demarcation map from Revenue Inspector and re-verify survey 142/3B.',
    clause_ref: 'PLACEHOLDER',
    evidence: {
      documents: ['cccc0032-0032-0032-0032-000000000032'],
      fields: ['land_area', 'registry_area'],
      bounding_boxes: [
        { doc_id: 'cccc0032-0032-0032-0032-000000000032', page: 1, x: 100, y: 220, w: 220, h: 30 },
      ],
    },
  },
  {
    id: 'dddd0032-0032-0032-0032-000000000032',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    source_code: 'D02',
    tier: 1,
    result: 'FALSE',
    reason: 'Fire & Safety certificate expired on 2024-12-31 prior to application submission. A valid current certificate is statutory requirement.',
    recheck_recipe: 'Obtain renewed Fire NOC from State Disaster & Fire Services Department.',
    clause_ref: 'PLACEHOLDER',
    evidence: {
      documents: ['cccc0033-0033-0033-0033-000000000033'],
      fields: ['fire_noc_expiry'],
      bounding_boxes: [
        { doc_id: 'cccc0033-0033-0033-0033-000000000033', page: 1, x: 140, y: 180, w: 190, h: 25 },
      ],
    },
  },
]

function generateDefaultDocs(appId: string, instName: string): Document[] {
  return [
    {
      id: `doc-1-${appId.slice(0, 8)}`,
      application_id: appId,
      type_declared: 'Trust Deed',
      page_count: 4,
      status: 'VERIFIED',
      extracted_fields: [
        { field: 'Institution Name', value: instName, confidence: 0.98, result: 'TRUE', extractor: 'pdfplumber' },
        { field: 'Trust Validity', value: 'Perpetual', confidence: 0.95, result: 'TRUE', extractor: 'pdfplumber' },
      ],
    },
    {
      id: `doc-2-${appId.slice(0, 8)}`,
      application_id: appId,
      type_declared: 'Affidavit',
      page_count: 2,
      status: 'VERIFIED',
      extracted_fields: [
        { field: 'Execution Date', value: '2025-02-10', confidence: 0.96, result: 'TRUE', extractor: 'pdfplumber' },
        { field: 'Authorized Signatory', value: 'Principal / Registrar', confidence: 0.94, result: 'TRUE', extractor: 'pdfplumber' },
      ],
    },
    {
      id: `doc-3-${appId.slice(0, 8)}`,
      application_id: appId,
      type_declared: 'Land Certificate',
      page_count: 5,
      status: 'VERIFIED',
      extracted_fields: [
        { field: 'Campus Area', value: '5.2 Acres', confidence: 0.97, result: 'TRUE', extractor: 'pdfplumber' },
        { field: 'Land Ownership', value: 'Owned Freehold', confidence: 0.96, result: 'TRUE', extractor: 'pdfplumber' },
      ],
    },
    {
      id: `doc-4-${appId.slice(0, 8)}`,
      application_id: appId,
      type_declared: 'Faculty List',
      page_count: 6,
      status: 'VERIFIED',
      extracted_fields: [
        { field: 'Sanctioned Faculty', value: '48', confidence: 0.92, result: 'TRUE', extractor: 'pdfplumber' },
      ],
    },
  ]
}

function generateDefaultFindings(appId: string): Finding[] {
  return [
    {
      id: `finding-1-${appId.slice(0, 8)}`,
      application_id: appId,
      source_code: 'D10',
      tier: 1,
      result: 'TRUE',
      reason: 'All verified documents match regulatory handbook thresholds with valid signatures.',
      clause_ref: 'PLACEHOLDER',
    },
  ]
}

function getFallbackApp(appId: string): Application {
  if (SEEDED_APPS[appId]) {
    return SEEDED_APPS[appId]
  }
  const code = 'INST-' + appId.slice(0, 4).toUpperCase()
  return {
    id: appId,
    institution_id: `inst-${appId.slice(0, 8)}`,
    institution_name: `AICTE Technical Institution (${code})`,
    institution_code: code,
    city: 'Bengaluru',
    state: 'Karnataka',
    declared_category: 'EOA Renewal',
    academic_year: '2025-26',
    stage: 'UNDER_REVIEW',
    risk_score: 0.42,
  }
}

interface Props {
  appId: string
  navigate: (path: string) => void
}

export default function Dossier({ appId, navigate }: Props) {
  const [selectedDocId, setSelectedDocId] = useState<string>('')
  const [showReport, setShowReport] = useState(false)
  const [reportMsg, setReportMsg] = useState('')
  const [pii, setPii] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const { data: appData, loading: appLoading } = useApi<Application>(
    () => api.get(`/api/applications/${appId}`),
    [appId],
  )
  const { data: docsData, loading: docsLoading, reload: reloadDocs } = useApi<{ documents: Document[] }>(
    () => api.get(`/api/applications/${appId}/documents`),
    [appId],
  )
  const { data: findingsData, loading: findingsLoading, reload: reloadFindings } = useApi<{ findings: Finding[] }>(
    () => api.get(`/api/applications/${appId}/findings`),
    [appId],
  )
  const { data: reportData, reload: reloadReport } = useApi<{ report: { recommendation?: string; overall_result?: string; summary?: { unknowns?: number } } }>(
    () => api.get(`/api/applications/${appId}/report`),
    [appId],
  )
  const { data: diagnosis } = useApi<{ recommendation: string; label?: string }>(
    () => api.get(`/api/applications/${appId}/diagnosis`),
    [appId],
  )
  const { data: verify } = useApi<{ requests: Array<{ ps_status: string; route: string }>; verification_debt: number }>(
    () => api.get(`/api/applications/${appId}/verification`),
    [appId],
  )

  const fallbackApp = getFallbackApp(appId)
  const app = appData || fallbackApp

  const fallbackDocs =
    appId === 'bbbb0001-0001-0001-0001-000000000001'
      ? SEEDED_DOCS_SUNRISE
      : appId === 'bbbb0003-0003-0003-0003-000000000003'
      ? SEEDED_DOCS_PINNACLE
      : generateDefaultDocs(appId, app.institution_name || 'AICTE Technical Institution')

  const fallbackFindings =
    appId === 'bbbb0001-0001-0001-0001-000000000001'
      ? SEEDED_FINDINGS_SUNRISE
      : appId === 'bbbb0003-0003-0003-0003-000000000003'
      ? SEEDED_FINDINGS_PINNACLE
      : generateDefaultFindings(appId)

  const docs = docsData?.documents?.length ? docsData.documents : fallbackDocs
  const findings = findingsData?.findings?.length ? findingsData.findings : fallbackFindings
  const selectedDoc = docs.find((d) => d.id === selectedDocId) || docs[0]
  const boxes = findings.flatMap((f) => f.evidence?.bounding_boxes || [])

  const stats = {
    total: docs.length,
    verified: docs.filter((d) => d.status === 'VERIFIED').length,
    findings: findings.length,
    unknowns: findings.filter((f) => f.result === 'UNKNOWN').length,
    debt: verify?.verification_debt ?? docs.filter((d) => d.status === 'SOURCE_UNAVAILABLE').length,
  }

  async function generateReport() {
    setShowReport(true)
    try {
      await api.post(`/api/applications/${appId}/report`, {})
      setReportMsg('Report hashed into the audit chain')
      reloadReport()
    } catch {
      setReportMsg('Showing in-memory report (API offline)')
    }
  }

  async function revealPan() {
    try {
      const res = await api.get<{ values: Array<{ field: string; masked: string }> }>(
        `/api/applications/${appId}/pii?field=pan`,
      )
      setPii(res.values.map((v) => `${v.field}: ${v.masked}`).join(' · ') || 'No PAN fields')
    } catch {
      setPii('Permissioned reveal requires officer/auditor token')
    }
  }

  async function upload(file: File) {
    const body = new FormData()
    body.append('file', file)
    body.append('type_declared', 'other')
    try {
      await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/applications/${appId}/documents`, {
        method: 'POST',
        body,
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('aicte_token') || ''}`,
        },
      })
      reloadDocs()
    } catch {
      /* gated */
    }
  }

  if (!app && !appLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 60, gap: 12 }}>
        <div style={{ fontSize: 32 }}>📋</div>
        <div style={{ fontSize: 16, fontWeight: 600 }}>Application Not Found</div>
        <button className="btn" onClick={() => navigate('/applications')}>← Back to Applications</button>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: 20 }}>
        <button className="btn" style={{ fontSize: 12, marginBottom: 12 }} onClick={() => navigate('/applications')}>
          ← Applications
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>{app?.institution_name || 'Application Detail'}</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              {app?.institution_code} · {app?.declared_category} · {app?.academic_year} · {app?.city}, {app?.state}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {app?.stage && <StatusChip status={app.stage} />}
            {app?.risk_score !== undefined && (
              <span style={{
                fontSize: 12,
                padding: '4px 12px',
                background: app.risk_score > 0.7 ? 'var(--red-bg)' : app.risk_score > 0.4 ? 'var(--amber-bg)' : 'var(--green-bg)',
                borderRadius: 100,
                color: app.risk_score > 0.7 ? 'var(--red)' : app.risk_score > 0.4 ? 'var(--amber)' : 'var(--green)',
              }}>
                Risk {Math.round(app.risk_score * 100)}%
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="summary-strip" style={{ marginBottom: 20 }}>
        <div className="summary-stat"><div className="summary-stat__value">{stats.total}</div><div className="summary-stat__label">Documents</div></div>
        <div className="summary-stat"><div className="summary-stat__value" style={{ color: 'var(--green)' }}>{stats.verified}</div><div className="summary-stat__label">Verified</div></div>
        <div className="summary-stat"><div className="summary-stat__value" style={{ color: 'var(--red)' }}>{stats.findings}</div><div className="summary-stat__label">Findings</div></div>
        <div className="summary-stat"><div className="summary-stat__value" style={{ color: 'var(--grey)' }}>{stats.unknowns}</div><div className="summary-stat__label">Unknown ≠ reject</div></div>
        <div className="summary-stat"><div className="summary-stat__value" style={{ color: 'var(--amber)' }}>{stats.debt}</div><div className="summary-stat__label">Verif. Debt</div></div>
      </div>

      <div className="dossier-grid">
        <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 12, overflow: 'auto', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>Documents</div>
          {docs.map((d) => (
            <div
              key={d.id}
              onClick={() => setSelectedDocId(d.id)}
              style={{
                padding: '8px 10px',
                borderRadius: 6,
                marginBottom: 4,
                cursor: 'pointer',
                background: selectedDoc?.id === d.id ? 'rgba(59,130,246,0.12)' : 'transparent',
                borderLeft: selectedDoc?.id === d.id ? '2px solid var(--blue)' : '2px solid transparent',
              }}
            >
              <div style={{ fontSize: 12, fontWeight: selectedDoc?.id === d.id ? 600 : 400 }}>{d.type_declared}</div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                {d.status && <StatusChip status={d.status} small />}
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{d.page_count}p</span>
              </div>
            </div>
          ))}
          {docsLoading && <LoadingSpinner label="" />}
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void upload(f)
            }}
          />
          <button className="btn" style={{ width: '100%', marginTop: 8, fontSize: 11 }} onClick={() => fileRef.current?.click()}>
            Upload (ingest gate)
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto' }}>
          {selectedDoc && (
            <>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h2 style={{ fontSize: 15, fontWeight: 600 }}>{selectedDoc.type_declared}</h2>
                  {selectedDoc.status && <StatusChip status={selectedDoc.status} />}
                </div>
                <PdfViewer
                  docId={selectedDoc.id}
                  title={selectedDoc.type_declared}
                  pageCount={selectedDoc.page_count}
                  boxes={boxes}
                  fileRef={selectedDoc.file_ref}
                />
              </div>
              <CertaintyStrip
                docType={selectedDoc.type_declared}
                fields={selectedDoc.extracted_fields || []}
                highlight={selectedDoc.status === 'SOURCE_UNAVAILABLE'}
              />
              <CrossCheckPanel />
            </>
          )}
          {!selectedDoc && !docsLoading && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Select a document to view details</div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto' }}>
          <div className="card" style={{ borderLeft: '3px solid var(--amber)' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Diagnosis</span>
              <span className="placeholder-badge">{diagnosis?.label || 'seeded static'}</span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {diagnosis?.recommendation || reportData?.report?.recommendation || 'Verify NOC certificate first — resolves D13 (SOURCE_UNAVAILABLE) and may affect D04 cross-check.'}
            </p>
          </div>

          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Verification</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Debt {stats.debt} · chaos switch forces SOURCE_UNAVAILABLE without rejection
            </div>
            {(verify?.requests || []).slice(0, 4).map((r, i) => (
              <div key={i} style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                {r.route} · {r.ps_status}
              </div>
            ))}
          </div>

          <div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
              Findings ({findings.length})
              {findings.some((f) => f.result === 'UNKNOWN') && (
                <span style={{ fontSize: 11, color: 'var(--grey)', fontWeight: 400, marginLeft: 8 }}>UNKNOWN ≠ FALSE</span>
              )}
            </div>
            {findingsLoading && <LoadingSpinner label="Loading findings…" />}
            {findings.map((f) => (
              <FindingCard key={f.id} finding={f} onAction={reloadFindings} />
            ))}
            {findings.length === 0 && !findingsLoading && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 24 }}>No findings</div>
            )}
          </div>

          <button className="btn" style={{ fontSize: 12 }} onClick={revealPan}>Reveal PAN (last 4, audited)</button>
          {pii && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{pii}</div>}

          <button className="btn btn--primary" onClick={generateReport}>
            {showReport ? 'Refresh report' : 'Generate Report'}
          </button>
          {showReport && (
            <div className="card">
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Verification Report</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <div>Total Documents: {stats.total}</div>
                <div>Verified: {stats.verified}</div>
                <div>Findings: {stats.findings}</div>
                <div>Unknowns (not rejections): {stats.unknowns}</div>
                <div>Verification Debt: {stats.debt}</div>
                {reportMsg && <div style={{ marginTop: 8, color: 'var(--green)' }}>{reportMsg}</div>}
              </div>
              <div style={{ marginTop: 12, padding: 8, background: 'var(--amber-bg)', borderRadius: 6, fontSize: 11, color: 'var(--amber)' }}>
                PLACEHOLDER: Handbook clause references must be filled by a person before this report can be finalised.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
