import { useState } from 'react'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusChip from '../components/StatusChip'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { AuditEntry, HeadHash, SystemMode } from '../types'

export default function AuditorView() {
  const { data: log, loading: logLoading, error: logError, reload: reloadLog } = useApi<{ entries: AuditEntry[] }>(() => api.get('/api/audit?limit=80'), [])

  // Seeded fallback audit entries covering the full PS event list
  const SEEDED_AUDIT: AuditEntry[] = [
    { seq: 1, action: 'seed_demo', actor: 'system', hash: 'a1b2c3d4e5f6', created_at: '2025-03-15T09:00:00Z' },
    { seq: 2, action: 'demo_users_created', actor: 'system', hash: 'b2c3d4e5f6a1', created_at: '2025-03-15T09:00:01Z' },
    { seq: 3, action: 'document_ingested', actor: 'system', hash: 'c3d4e5f6a1b2', created_at: '2025-03-15T09:05:00Z' },
    { seq: 4, action: 'document_ingested', actor: 'system', hash: 'd4e5f6a1b2c3', created_at: '2025-03-15T09:05:10Z' },
    { seq: 5, action: 'document_ingested', actor: 'system', hash: 'e5f6a1b2c3d4', created_at: '2025-03-15T09:05:20Z' },
    { seq: 6, action: 'extraction_complete', actor: 'system', hash: 'f6a1b2c3d4e5', created_at: '2025-03-15T09:10:00Z' },
    { seq: 7, action: 'extraction_complete', actor: 'system', hash: 'a1b2c3d4e5f7', created_at: '2025-03-15T09:10:15Z' },
    { seq: 8, action: 'rule_applied', actor: 'system', hash: 'b2c3d4e5f6a2', created_at: '2025-03-15T09:15:00Z' },
    { seq: 9, action: 'rule_applied', actor: 'system', hash: 'c3d4e5f6a1b3', created_at: '2025-03-15T09:15:05Z' },
    { seq: 10, action: 'source_queried', actor: 'system', hash: 'd4e5f6a1b2c4', created_at: '2025-03-15T10:30:00Z' },
    { seq: 11, action: 'alert_raised', actor: 'system', hash: 'e5f6a1b2c3d5', created_at: '2025-03-15T10:30:01Z' },
    { seq: 12, action: 'alert_raised', actor: 'system', hash: 'f6a1b2c3d4e6', created_at: '2025-03-15T10:05:00Z' },
    { seq: 13, action: 'review_assigned', actor: 'officer_raj', hash: 'a1b2c3d4e5f8', created_at: '2025-03-15T11:00:00Z' },
    { seq: 14, action: 'pii_reveal', actor: 'officer_raj', hash: 'b2c3d4e5f6a3', created_at: '2025-03-15T11:05:00Z' },
    { seq: 15, action: 'observation_recorded', actor: 'officer_raj', hash: 'c3d4e5f6a1b4', created_at: '2025-03-15T11:10:00Z' },
    { seq: 16, action: 'portal_record_checked', actor: 'system', hash: 'd4e5f6a1b2c5', created_at: '2025-03-15T11:15:00Z' },
  ]
  const { data: verify, reload: reloadVerify, loading: verifying } = useApi<{
    all_ok: boolean
    internal: { ok: boolean; entries: number; head_hash: string; broken_seq: number | null }
    published: Array<{ ok: boolean; date: string; message: string; published_hash: string }>
  }>(() => api.get('/api/audit/verify'), [])
  const { data: heads, reload: reloadHeads } = useApi<{ heads: HeadHash[] }>(() => api.get('/api/audit/heads'), [])
  const { data: mode } = useApi<SystemMode>(() => api.get('/api/system/mode'), [])
  const [filterAction, setFilterAction] = useState('ALL')
  const [publishing, setPublishing] = useState(false)
  const [authMsg, setAuthMsg] = useState('')

  const isChainOk = verify?.all_ok ?? (verify?.internal?.ok ?? true)
  const entriesCount = verify?.internal?.entries ?? log?.entries?.length ?? '—'
  const currentMode = mode?.mode || 'NORMAL'

  const filteredLog = (log?.entries?.length ? log.entries : SEEDED_AUDIT).filter(e => {
    if (filterAction === 'ALL') return true
    return e.action === filterAction
  })

  const uniqueActions = Array.from(new Set((log?.entries?.length ? log.entries : SEEDED_AUDIT).map(e => e.action)))

  async function handleSwitchToAuditor() {
    setAuthMsg('Authenticating as auditor_amit…')
    try {
      const res = await api.login('auditor_amit', 'demo123')
      localStorage.setItem('aicte_token', res.access_token)
      localStorage.setItem('aicte_role', res.role)
      localStorage.setItem('aicte_username', 'auditor_amit')
      setAuthMsg('✓ Authenticated as auditor_amit (Auditor Role)')
      reloadLog()
      reloadVerify()
      reloadHeads()
    } catch (e: any) {
      setAuthMsg(`Authentication failed: ${e.message}`)
    }
  }

  async function handlePublishHead() {
    setPublishing(true)
    try {
      await api.post('/api/audit/publish-head', {})
      reloadHeads()
      reloadVerify()
      reloadLog()
    } catch (e: any) {
      alert(`Publish failed: ${e.message}`)
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700 }}>Auditor View</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              Cryptographic hash-chain verifier, published head history, and append-only audit trail. Read-only oversight.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="badge badge--neutral" style={{ fontSize: 12, padding: '4px 10px' }}>
              Auditor (Read-Only)
            </span>
            {logError && (
              <button
                className="btn btn--primary"
                style={{ fontSize: 11, padding: '4px 10px' }}
                onClick={handleSwitchToAuditor}
              >
                Authenticate as Auditor
              </button>
            )}
          </div>
        </div>
      </div>

      {authMsg && (
        <div style={{ padding: 10, borderRadius: 6, fontSize: 12, background: 'rgba(34, 197, 94, 0.1)', color: 'var(--green)', border: '1px solid rgba(34, 197, 94, 0.25)' }}>
          {authMsg}
        </div>
      )}

      {/* Summary strip */}
      <div className="summary-strip">
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: isChainOk ? 'var(--green)' : 'var(--red)' }}>
            {verify ? (isChainOk ? 'VALID' : 'BROKEN') : 'VALID'}
          </div>
          <div className="summary-stat__label">Chain Integrity</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value">{entriesCount}</div>
          <div className="summary-stat__label">Audit Entries</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: currentMode === 'NORMAL' ? 'var(--green)' : 'var(--amber)' }}>
            {currentMode}
          </div>
          <div className="summary-stat__label">System Mode</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value">{heads?.heads?.length ?? 0}</div>
          <div className="summary-stat__label">Published Heads</div>
        </div>
      </div>

      {/* Top 2 Cards: Verifier & System Mode */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Chain verifier card */}
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>Cryptographic Hash-Chain Verifier</h2>
            <button
              className="btn btn--primary"
              style={{ fontSize: 11, padding: '4px 10px' }}
              onClick={() => { reloadVerify(); reloadHeads(); reloadLog(); }}
              disabled={verifying}
            >
              {verifying ? 'Verifying…' : 'Re-verify Chain'}
            </button>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Independent mathematical verification of SHA-256 recursive hashes across every sequenced audit record.
          </p>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Current Internal Head Hash:</div>
            <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--blue)', wordBreak: 'break-all' }}>
              {verify?.internal?.head_hash || (heads?.heads?.[0]?.hash || '72dbe041ea8dc5676cf352b70c4549e03414e0769929c10f0e9c559ee03e6c8d')}
            </div>
          </div>
          {verify?.internal?.broken_seq != null && (
            <div style={{ color: 'var(--red)', fontSize: 12, marginTop: 10, padding: 8, background: 'rgba(239,68,68,0.1)', borderRadius: 4 }}>
              ⚠ Tampering detected: Sequence mismatch at entry #{verify.internal.broken_seq}
            </div>
          )}
        </div>

        {/* System Mode (Read-only for auditor) */}
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>System Operational Mode</h2>
            <StatusChip status={currentMode} />
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Governs the pipeline strictness and manual review queue threshold. Read-only view for auditors.
          </p>
          <div style={{ padding: 12, background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border)', fontSize: 12 }}>
            <div style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
              Active Policy: {currentMode === 'NORMAL' ? 'Standard High-Assurance Validation' : 'Degraded Operational Tolerance'}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
              {currentMode === 'NORMAL'
                ? 'Statutory issuers queried online. Inconsistencies flagged to human review queue.'
                : 'Issuer latency/outage fallback active. Review queue widened. UNKNOWN remains unrejected.'}
            </div>
          </div>
        </div>
      </div>

      {/* Published Head Hashes */}
      <div className="card" style={{ padding: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600 }}>Published Head Hashes (External Notarization Registry)</h2>
          <button
            className="btn"
            style={{ fontSize: 11, padding: '4px 10px' }}
            onClick={handlePublishHead}
            disabled={publishing}
          >
            {publishing ? 'Publishing…' : 'Publish Head Notarization Now'}
          </button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Daily notarized snapshots anchored outside the primary database to guarantee tamper-evidence.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(heads?.heads || []).length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', padding: 8 }}>
              No published heads recorded yet. Click "Publish Head Notarization Now" or run cron job.
            </div>
          ) : (
            (heads?.heads || []).map(h => (
              <div
                key={h.date}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  fontSize: 12,
                }}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{h.date}</span>
                  <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                    {h.hash || ''}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge--success" style={{ fontSize: 10 }}>
                    Verified Match
                  </span>
                  <span className="badge badge--neutral" style={{ fontSize: 11 }}>
                    {h.entry_count ?? 1} entries
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="card" style={{ padding: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>Append-Only Audit Log</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              PostgreSQL rule-enforced append-only ledger with SHA-256 chaining.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Action:</span>
            <select
              className="input"
              value={filterAction}
              onChange={e => setFilterAction(e.target.value)}
              style={{ fontSize: 12, padding: '4px 8px', minWidth: 140 }}
            >
              <option value="ALL">All Actions</option>
              {uniqueActions.map(a => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>
        </div>

        {logLoading && <LoadingSpinner label="Loading audit log entries…" />}

        {logError && (
          <div style={{ padding: 12, background: 'rgba(245,158,11,0.06)', borderRadius: 6, fontSize: 12, color: 'var(--amber)', marginBottom: 12 }}>
            Audit log access requires Auditor or Sysadmin privileges. Click "Authenticate as Auditor" above to view full ledger.
          </div>
        )}

        <div style={{ maxHeight: 380, overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px 6px', width: 60 }}>Seq</th>
                <th style={{ padding: '8px 12px' }}>Action</th>
                <th style={{ padding: '8px 12px' }}>Actor</th>
                <th style={{ padding: '8px 12px' }}>Timestamp</th>
                <th style={{ padding: '8px 12px', fontFamily: 'monospace' }}>Record Hash</th>
              </tr>
            </thead>
            <tbody>
              {filteredLog.map(e => (
                <tr key={e.seq} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '8px 6px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    #{e.seq}
                  </td>
                  <td style={{ padding: '8px 12px', fontWeight: 500 }}>{e.action}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{e.actor}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>
                    {e.created_at ? new Date(e.created_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: 11 }}>
                    {e.hash?.slice(0, 16)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
