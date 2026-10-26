import { useState } from 'react'
import type { ReviewItem } from '../types'
import StatusChip from '../components/StatusChip'
import LoadingSpinner from '../components/LoadingSpinner'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

const SEEDED_ITEMS: ReviewItem[] = [
  { id: 'ri001', application_id: 'bbbb0001-0001-0001-0001-000000000001', institution_name: 'Sunrise Technical Institute', institution_code: 'SUNRISE-001', level: 2, status: 'ASSIGNED', assigned_to_username: 'officer_raj', created_at: '2025-03-15T10:00:00Z', category: 'EOA Renewal', findings_count: 2 },
  { id: 'ri002', application_id: 'bbbb0003-0003-0003-0003-000000000003', institution_name: 'Pinnacle College of Science', institution_code: 'PINNACLE-001', level: 3, status: 'PENDING', created_at: '2025-03-10T09:00:00Z', category: 'EOA Renewal', findings_count: 4 },
  { id: 'ri003', application_id: 'bbbb0007-0007-0007-0007-000000000007', institution_name: 'Northstar Academy of Sciences', institution_code: 'NAS-001', level: 2, status: 'IN_REVIEW', assigned_to_username: 'supervisor_priya', created_at: '2025-03-12T13:00:00Z', category: 'EOA Renewal', findings_count: 3 },
  { id: 'ri004', application_id: 'bbbb0006-0006-0006-0006-000000000006', institution_name: 'Rajendra Institute of Management', institution_code: 'RIM-001', level: 1, status: 'PENDING', created_at: '2025-03-25T16:00:00Z', category: 'New Approval', findings_count: 1 },
  { id: 'ri005', application_id: 'bbbb0002-0002-0002-0002-000000000002', institution_name: 'Horizon Engineering College', institution_code: 'HORIZON-001', level: 0, status: 'PENDING', created_at: '2025-03-20T14:30:00Z', category: 'New Approval', findings_count: 0 },
]

const LEVEL_LABELS: Record<number, string> = {
  0: 'Level 0 — Automated',
  1: 'Level 1 — Tier 1 Defects',
  2: 'Level 2 — Tier 2 Cross-Checks',
  3: 'Level 3 — Deep Forensics',
}

interface Props { navigate: (path: string) => void }

export default function ReviewQueue({ navigate }: Props) {
  const [activeLevel, setActiveLevel] = useState<0 | 1 | 2 | 3>(2)
  const [assigning, setAssigning] = useState<string | null>(null)

  const { data, loading, error, reload } = useApi<{ items: ReviewItem[] }>(
    () => api.get(`/api/review-queue?level=${activeLevel}`),
    [activeLevel],
  )
  const { data: allData } = useApi<{ items: ReviewItem[] }>(
    () => api.get('/api/review-queue'),
    [],
  )

  const items: ReviewItem[] = data?.items?.length
    ? data.items
    : SEEDED_ITEMS.filter((i) => i.level === activeLevel)
  const allItems: ReviewItem[] = allData?.items?.length ? allData.items : SEEDED_ITEMS
  const countByLevel = (l: number) => allItems.filter((i) => i.level === l).length

  async function assignToMe(itemId: string) {
    setAssigning(itemId)
    try {
      await api.post(`/api/review-queue/${itemId}/assign`, { assignee: 'me' })
      reload()
    } catch {
      reload()
    }
    setAssigning(null)
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Review Queue</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Scrutiny work queue — tiered by defect severity. All data is synthetic.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid var(--border)' }}>
        {([0, 1, 2, 3] as const).map((level) => (
          <button
            key={level}
            onClick={() => setActiveLevel(level)}
            style={{
              padding: '10px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeLevel === level ? '2px solid var(--blue)' : '2px solid transparent',
              color: activeLevel === level ? 'var(--blue)' : 'var(--text-secondary)',
              fontSize: 13,
              fontWeight: activeLevel === level ? 600 : 400,
              cursor: 'pointer',
              marginBottom: -1,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            Level {level}
            {countByLevel(level) > 0 && (
              <span style={{
                background: activeLevel === level ? 'var(--blue)' : 'var(--grey-bg)',
                color: activeLevel === level ? 'white' : 'var(--text-muted)',
                borderRadius: 100,
                padding: '1px 7px',
                fontSize: 11,
              }}>
                {countByLevel(level)}
              </span>
            )}
          </button>
        ))}
      </div>

      <div style={{ marginBottom: 16, padding: '8px 16px', background: 'var(--bg-glass)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>{LEVEL_LABELS[activeLevel]}</strong>
        {activeLevel === 0 && ' — Machine-only review, no human assignment needed'}
        {activeLevel === 1 && ' — Missing docs, expired dates, checksum failures (Tier 1 defects D01-D08)'}
        {activeLevel === 2 && ' — Signature issues, issuer mismatches, source outages (Tier 2 defects D10-D13)'}
        {activeLevel === 3 && ' — Deep forensics, cross-institution checks (Tier 3 defects D09, D14-D19)'}
      </div>

      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(245,158,11,0.08)', borderRadius: 8, fontSize: 12, color: 'var(--amber)', marginBottom: 16 }}>
          API unavailable — showing seeded synthetic queue
        </div>
      )}
      {loading && !data && <LoadingSpinner label="Loading review queue…" />}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((item) => (
          <div key={item.id} className="card" style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 200, cursor: 'pointer' }} onClick={() => navigate(`/applications/${item.application_id}`)}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{item.institution_name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                {item.institution_code} · {item.category} · {item.findings_count ?? 0} findings
              </div>
            </div>
            <StatusChip status={item.status} small />
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 120 }}>
              {item.assigned_to_username || 'Unassigned'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {new Date(item.created_at).toLocaleDateString('en-IN')}
            </div>
            {item.status === 'PENDING' && (
              <button
                className="btn btn--primary"
                style={{ fontSize: 11 }}
                disabled={assigning === item.id}
                onClick={() => assignToMe(item.id)}
              >
                {assigning === item.id ? 'Assigning…' : 'Assign to me'}
              </button>
            )}
            <button className="btn" style={{ fontSize: 11 }} onClick={() => navigate(`/applications/${item.application_id}`)}>
              Open dossier
            </button>
          </div>
        ))}
        {items.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
            No items at this level. DEGRADED mode widens the queue without auto-rejecting UNKNOWN.
          </div>
        )}
      </div>
    </div>
  )
}
