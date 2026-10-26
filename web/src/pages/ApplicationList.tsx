import { useState } from 'react'
import type { Application } from '../types'
import StatusChip from '../components/StatusChip'
import LoadingSpinner from '../components/LoadingSpinner'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

// Seeded synthetic applications
const SEEDED_APPLICATIONS: Application[] = [
  {
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
    findings_count: 2,
    unknowns_count: 1,
    verified_count: 3,
    created_at: '2025-03-15T10:00:00Z',
  },
  {
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
    findings_count: 0,
    unknowns_count: 0,
    verified_count: 0,
    created_at: '2025-03-20T14:30:00Z',
  },
  {
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
    findings_count: 4,
    unknowns_count: 2,
    verified_count: 2,
    created_at: '2025-03-10T09:00:00Z',
  },
  {
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
    findings_count: 0,
    unknowns_count: 0,
    verified_count: 6,
    created_at: '2025-02-28T11:00:00Z',
  },
  {
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
    findings_count: 6,
    unknowns_count: 0,
    verified_count: 1,
    created_at: '2025-02-15T08:00:00Z',
  },
  {
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
    findings_count: 1,
    unknowns_count: 3,
    verified_count: 2,
    created_at: '2025-03-25T16:00:00Z',
  },
  {
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
    findings_count: 3,
    unknowns_count: 1,
    verified_count: 4,
    created_at: '2025-03-12T13:00:00Z',
  },
  {
    id: 'bbbb0008-0008-0008-0008-000000000008',
    institution_id: '88888888-8888-8888-8888-888888888888',
    institution_name: 'Eastern Polytechnic Institute',
    institution_code: 'EPI-001',
    city: 'Bhubaneswar',
    state: 'Odisha',
    declared_category: 'Intake Enhancement',
    academic_year: '2025-26',
    stage: 'INGESTING',
    risk_score: undefined,
    findings_count: 0,
    unknowns_count: 0,
    verified_count: 0,
    created_at: '2025-03-28T10:00:00Z',
  },
]

function riskBar(score: number | undefined) {
  if (score === undefined) return null
  const color = score > 0.7 ? 'var(--red)' : score > 0.4 ? 'var(--amber)' : 'var(--green)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${score * 100}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color }}>{Math.round(score * 100)}%</span>
    </div>
  )
}

function formatCategory(cat: string | undefined): string {
  if (!cat) return '—'
  if (cat === 'new_institution' || cat === 'New Approval') {
    return 'New Institution (Assumed Category — PLACEHOLDER mapping)'
  }
  return cat
}

function renderFindingsStatus(app: Application) {
  const findingsCount = app.findings_count ?? 0
  const unknownsCount = app.unknowns_count ?? 0
  const verifiedCount = app.verified_count ?? 0
  const checkedDocs = app.checked_docs_count ?? 0

  const hasBeenChecked = checkedDocs > 0 || findingsCount > 0 || unknownsCount > 0 || verifiedCount > 0 ||
    ['UNDER_REVIEW', 'DECISION_PENDING', 'APPROVED', 'REJECTED'].includes(app.stage)

  if (!hasBeenChecked || (findingsCount === 0 && unknownsCount === 0 && verifiedCount === 0)) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          padding: '3px 8px',
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 500,
          background: 'rgba(255, 255, 255, 0.04)',
          color: 'var(--text-muted)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <span style={{ fontSize: 9 }}>○</span> Not checked yet
      </span>
    )
  }

  if (findingsCount === 0 && unknownsCount === 0 && verifiedCount > 0) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          padding: '3px 8px',
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 600,
          background: 'rgba(34, 197, 94, 0.1)',
          color: 'var(--green)',
          border: '1px solid rgba(34, 197, 94, 0.25)',
        }}
      >
        <span>✓</span> Clean ({verifiedCount} verified)
      </span>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 10, fontSize: 12, alignItems: 'center' }}>
      {findingsCount > 0 ? (
        <span style={{ color: 'var(--red)', fontWeight: 600 }}>⚠ {findingsCount} {findingsCount === 1 ? 'finding' : 'findings'}</span>
      ) : (
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>0 findings</span>
      )}
      {unknownsCount > 0 ? (
        <span style={{ color: 'var(--amber)', fontWeight: 500 }}>? {unknownsCount} unknown</span>
      ) : null}
      {verifiedCount > 0 ? (
        <span style={{ color: 'var(--green)', fontSize: 11 }}>✓ {verifiedCount} verified</span>
      ) : null}
    </div>
  )
}

const STAGES = ['All', 'SUBMITTED', 'INGESTING', 'EXTRACTING', 'UNDER_REVIEW', 'DECISION_PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN']
const CATEGORIES = ['All', 'EOA Renewal', 'New Approval', 'Intake Enhancement']
const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Newest First' },
  { value: 'date_asc', label: 'Oldest First' },
  { value: 'risk_desc', label: 'Highest Risk' },
  { value: 'risk_asc', label: 'Lowest Risk' },
  { value: 'institution', label: 'Institution A-Z' },
]

interface Props { navigate: (path: string) => void }

export default function ApplicationList({ navigate }: Props) {
  const [stageFilter, setStageFilter] = useState('All')
  const [categoryFilter, setCategoryFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('date_desc')

  const { data, loading, error } = useApi<{ applications: Application[] }>(
    () => api.get('/api/applications/'),
    []
  )

  const apps: Application[] = data?.applications?.length
    ? data.applications
    : SEEDED_APPLICATIONS

  const filtered = apps
    .filter(a => stageFilter === 'All' || a.stage === stageFilter)
    .filter(a => categoryFilter === 'All' || a.declared_category === categoryFilter)
    .filter(a => !search || (a.institution_name || '').toLowerCase().includes(search.toLowerCase()) || (a.institution_code || '').toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'date_desc') return (b.created_at || '') > (a.created_at || '') ? 1 : -1
      if (sortBy === 'date_asc') return (a.created_at || '') > (b.created_at || '') ? 1 : -1
      if (sortBy === 'risk_desc') return (b.risk_score || 0) - (a.risk_score || 0)
      if (sortBy === 'risk_asc') return (a.risk_score || 0) - (b.risk_score || 0)
      if (sortBy === 'institution') return (a.institution_name || '').localeCompare(b.institution_name || '')
      return 0
    })

  const stats = {
    total: apps.length,
    underReview: apps.filter(a => a.stage === 'UNDER_REVIEW').length,
    approved: apps.filter(a => a.stage === 'APPROVED').length,
    highRisk: apps.filter(a => (a.risk_score || 0) > 0.7).length,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Applications</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            {apps.length} applications loaded · All data is synthetic
          </p>
        </div>
        <div>
          {data?.applications ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 600,
                background: 'rgba(34, 197, 94, 0.12)',
                color: 'var(--green)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--green)' }}></span>
              Live PostgreSQL API ({apps.length} records)
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 600,
                background: 'rgba(245, 158, 11, 0.12)',
                color: 'var(--amber)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--amber)' }}></span>
              Offline Seeded Data
            </span>
          )}
        </div>
      </div>

      {/* Stats strip */}
      <div className="summary-strip" style={{ marginBottom: 20 }}>
        <div className="summary-stat">
          <div className="summary-stat__value">{stats.total}</div>
          <div className="summary-stat__label">Total</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: 'var(--amber)' }}>{stats.underReview}</div>
          <div className="summary-stat__label">Under Review</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: 'var(--green)' }}>{stats.approved}</div>
          <div className="summary-stat__label">Closed by officer</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: 'var(--red)' }}>{stats.highRisk}</div>
          <div className="summary-stat__label">High Risk</div>
        </div>
      </div>

      {/* Filters - single compact horizontal flex row */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, alignItems: 'center', width: '100%' }}>
        <input
          className="input"
          placeholder="Search institution…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 2, minWidth: 200 }}
        />
        <select className="input" value={stageFilter} onChange={e => setStageFilter(e.target.value)} style={{ flex: 1, minWidth: 140 }}>
          {STAGES.map(s => <option key={s} value={s}>{s === 'All' ? 'All Stages' : s.replace(/_/g, ' ')}</option>)}
        </select>
        <select className="input" value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} style={{ flex: 1, minWidth: 150 }}>
          {CATEGORIES.map(c => <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>)}
        </select>
        <select className="input" value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ flex: 1, minWidth: 140 }}>
          {SORT_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {loading && !data && <LoadingSpinner label="Loading applications…" />}
      {error && !data && (
        <div style={{ padding: 12, background: 'rgba(245,158,11,0.08)', borderRadius: 8, fontSize: 12, color: 'var(--amber)', marginBottom: 16 }}>
          ⚠ API unavailable — showing seeded synthetic data
        </div>
      )}

      {/* Applications table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🔍</div>
            <div>No applications match the current filters.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {filtered.map(app => (
              <div
                key={app.id}
                className="card"
                style={{ cursor: 'pointer', padding: '16px 20px', borderRadius: 'var(--radius-md)' }}
                onClick={() => navigate(`/applications/${app.id}`)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                  {/* Institution info */}
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{app.institution_name || app.institution_id}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {app.institution_code} · {app.city}, {app.state}
                    </div>
                  </div>

                  {/* Category + Year */}
                  <div style={{ minWidth: 180, maxWidth: 280 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{formatCategory(app.declared_category)}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{app.academic_year}</div>
                  </div>

                  {/* Stage chip */}
                  <StatusChip status={app.stage} small />

                  {/* Findings or Not yet checked */}
                  {renderFindingsStatus(app)}

                  {/* Risk score */}
                  <div style={{ minWidth: 90 }}>
                    {app.risk_score !== undefined ? riskBar(app.risk_score) : (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No score yet</span>
                    )}
                  </div>

                  {/* Date */}
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 80, textAlign: 'right' }}>
                    {app.created_at ? new Date(app.created_at).toLocaleDateString('en-IN') : '—'}
                  </div>

                  {/* Arrow */}
                  <div style={{ color: 'var(--text-muted)', fontSize: 16 }}>›</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
