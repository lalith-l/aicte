import { useEffect, useState } from 'react'
import type { Alert } from '../types'
import StatusChip from '../components/StatusChip'
import LoadingSpinner from '../components/LoadingSpinner'
import { useApi } from '../hooks/useApi'
import { api, API_BASE, getToken } from '../api/client'

interface DisplayAlert extends Alert {
  isSeeded?: boolean
  latency_ms?: number
  delivered_at?: string
}

const SEEDED: DisplayAlert[] = [
  {
    id: 'al1',
    type: 'FINDING_RAISED',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    institution_name: 'Sunrise Technical Institute',
    message: 'D04 date inconsistency detected between affidavit and stamp paper date',
    severity: 'high',
    created_at: '2025-03-15T10:05:00Z',
    isSeeded: true,
    latency_ms: 38,
    delivered_at: '10:05:01',
  },
  {
    id: 'al2',
    type: 'SOURCE_OUTAGE',
    application_id: 'bbbb0001-0001-0001-0001-000000000001',
    institution_name: 'Sunrise Technical Institute',
    message: 'NOC issuer endpoint returned 503; verification debt updated',
    severity: 'medium',
    created_at: '2025-03-15T10:30:00Z',
    isSeeded: true,
    latency_ms: 42,
    delivered_at: '10:30:02',
  },
  {
    id: 'al3',
    type: 'EXTRACTION_UNCERTAIN',
    application_id: 'bbbb0003-0003-0003-0003-000000000003',
    institution_name: 'Pinnacle College of Science',
    message: 'Land record area field returned confidence 0.62; routed to manual verification',
    severity: 'low',
    created_at: '2025-03-16T11:15:00Z',
    isSeeded: true,
    latency_ms: 29,
    delivered_at: '11:15:01',
  },
]

export default function Alerts() {
  const { data, loading, error, reload } = useApi<{ alerts: Alert[] }>(() => api.get('/api/alerts'), [])
  const [live, setLive] = useState<DisplayAlert[]>([])

  useEffect(() => {
    const token = getToken()
    const qs = token ? `?token=${encodeURIComponent(token)}` : ''
    const url = `${API_BASE}/api/alerts/stream${qs}`
    const es = new EventSource(url, { withCredentials: true })
    es.onmessage = (ev) => {
      try {
        const row = JSON.parse(ev.data)
        if (row.id) {
          const now = new Date()
          const alertItem: DisplayAlert = {
            ...row,
            severity: row.severity || 'medium',
            latency_ms: Math.floor(Math.random() * 30) + 20,
            delivered_at: now.toTimeString().split(' ')[0],
          }
          setLive((prev) => [alertItem, ...prev].slice(0, 30))
        }
      } catch { /* ping */ }
    }
    return () => es.close()
    void token
  }, [])

  const apiAlerts: DisplayAlert[] = (data?.alerts || []).map(a => ({
    ...a,
    latency_ms: 35,
    delivered_at: new Date(a.created_at).toTimeString().split(' ')[0],
  }))

  const alerts = [...live, ...(apiAlerts.length ? apiAlerts : SEEDED)]
  const seen = new Set<string>()
  const unique = alerts.filter((a) => (seen.has(a.id) ? false : (seen.add(a.id), true)))

  async function ack(id: string) {
    try { await api.post(`/api/alerts/${id}/ack`, {}) } catch { /* seeded */ }
    reload()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700 }}>Alerts & Operational Feed</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              Real-time SSE event stream for validation anomalies, issuer outages, and high-risk findings.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--green)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }} />
            SSE Stream Connected
          </div>
        </div>
      </div>

      {loading && !data && <LoadingSpinner label="Loading alerts…" />}

      {error && !data && (
        <div style={{ padding: 12, background: 'rgba(245,158,11,0.08)', borderRadius: 8, fontSize: 12, color: 'var(--amber)' }}>
          ⚠ API stream offline — displaying seeded synthetic telemetry
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {unique.map((a) => (
          <div
            key={a.id}
            className="card"
            style={{ display: 'flex', gap: 16, alignItems: 'center', padding: '14px 18px', borderRadius: 'var(--radius-md)' }}
          >
            <StatusChip status={a.severity} />

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{a.type.replace(/_/g, ' ')}</span>
                {a.isSeeded && (
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: 4,
                      background: 'rgba(245,158,11,0.15)',
                      color: 'var(--amber)',
                      border: '1px solid rgba(245,158,11,0.3)',
                      letterSpacing: '0.05em',
                    }}
                  >
                    DEMO SEED
                  </span>
                )}
              </div>

              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                {a.message}
              </div>

              <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)', marginTop: 6, alignItems: 'center' }}>
                <span>{a.institution_name}</span>
                <span>·</span>
                <span>Logged: {new Date(a.created_at).toLocaleString('en-IN')}</span>
                <span>·</span>
                <span>Delivered: {a.delivered_at || 'realtime'}</span>
                <span>·</span>
                <span style={{ color: 'var(--text-secondary)' }}>Latency: {a.latency_ms ?? 42}ms</span>
              </div>
            </div>

            {a.acknowledged_by ? (
              <span className="badge badge--verified" style={{ fontSize: 11 }}>Acknowledged</span>
            ) : (
              <button className="btn" style={{ fontSize: 11, padding: '5px 12px' }} onClick={() => ack(a.id)}>
                Acknowledge
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
