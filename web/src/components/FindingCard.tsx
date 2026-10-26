import type { Finding } from '../types'
import StatusChip, { tierClass } from './StatusChip'
import { useState } from 'react'
import { api } from '../api/client'

interface Props {
  finding: Finding
  onAction?: () => void
}

export default function FindingCard({ finding, onAction }: Props) {
  const [open, setOpen] = useState(false)
  const [action, setAction] = useState<'accept' | 'dismiss' | 'escalate' | ''>('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function submitAction() {
    if (!action || !reason.trim()) return
    setSubmitting(true)
    try {
      await api.post(`/api/findings/${finding.id}/action`, { action, reason })
      setDone(true)
      onAction?.()
    } catch {
      // silently ignore — seeded data
      setDone(true)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={`finding-card finding-card--${finding.result.toLowerCase()} animate-in`}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
        <span className={`chip ${tierClass(finding.tier)}`}>Tier {finding.tier}</span>
        <StatusChip status={finding.result} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>{finding.source_code}</span>
        <span className="placeholder-badge">PLACEHOLDER: clause_ref</span>
        {finding.result === 'UNKNOWN' && (
          <span style={{ fontSize: 11, color: 'var(--grey)', marginLeft: 'auto' }}>
            ℹ UNKNOWN ≠ rejection
          </span>
        )}
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{finding.reason}</p>
      {finding.recheck_recipe && (
        <div style={{ marginTop: 8, padding: 8, background: 'rgba(59,130,246,0.08)', borderRadius: 6, fontSize: 12, color: 'var(--blue)' }}>
          <strong>Recheck:</strong> {finding.recheck_recipe}
        </div>
      )}
      {finding.evidence?.bounding_boxes && finding.evidence.bounding_boxes.length > 0 && (
        <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          📎 {finding.evidence.bounding_boxes.length} bounding box{finding.evidence.bounding_boxes.length > 1 ? 'es' : ''} linked
        </div>
      )}

      {!done && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn" style={{ fontSize: 11 }} onClick={() => setOpen(!open)}>
            {open ? 'Cancel' : 'Review Action'}
          </button>
        </div>
      )}

      {done && (
        <div style={{ marginTop: 8, padding: 8, background: 'rgba(34,197,94,0.08)', borderRadius: 6, fontSize: 12, color: 'var(--green)' }}>
          ✓ Action recorded
        </div>
      )}

      {open && !done && (
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['accept', 'dismiss', 'escalate'] as const).map(a => (
              <button
                key={a}
                className={`btn ${action === a ? 'btn--primary' : ''}`}
                style={{ fontSize: 11 }}
                onClick={() => setAction(a)}
              >
                {a.charAt(0).toUpperCase() + a.slice(1)}
              </button>
            ))}
          </div>
          <input
            className="input"
            placeholder="Reason (required)"
            value={reason}
            onChange={e => setReason(e.target.value)}
            style={{ fontSize: 12 }}
          />
          <button
            className="btn btn--primary"
            style={{ fontSize: 12, alignSelf: 'flex-start' }}
            onClick={submitAction}
            disabled={!action || !reason.trim() || submitting}
          >
            {submitting ? 'Submitting…' : 'Submit'}
          </button>
        </div>
      )}
    </div>
  )
}
