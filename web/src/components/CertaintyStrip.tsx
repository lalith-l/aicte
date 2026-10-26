import type { ExtractedField } from '../types'
import StatusChip from './StatusChip'

function barColor(r: string): string {
  if (r === 'TRUE') return 'var(--green)'
  if (r === 'FALSE') return 'var(--red)'
  return 'var(--grey)'
}

function resultIcon(r: string): string {
  if (r === 'TRUE') return '✓'
  if (r === 'FALSE') return '✗'
  return '?'
}

interface Props {
  docType: string
  fields: ExtractedField[]
  highlight?: boolean
}

export default function CertaintyStrip({ docType, fields, highlight }: Props) {
  return (
    <div className="certainty-strip">
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Certainty Strip — {docType} {highlight ? '· grey = UNKNOWN (source unavailable)' : ''}
      </div>
      {fields.map(f => (
        <div className="certainty-row" key={f.field}>
          <span className="certainty-field">{f.field}</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.value}</span>
          <div className="certainty-bar" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="certainty-bar__fill" style={{ width: `${f.confidence * 100}%`, background: barColor(f.result) }} />
          </div>
          <span className="certainty-icon" style={{ color: barColor(f.result) }}>{resultIcon(f.result)}</span>
          <StatusChip status={f.result} small />
          <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 40 }}>{Math.round(f.confidence * 100)}%</span>
        </div>
      ))}
      {fields.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: '8px 0' }}>No extracted fields for this document.</div>
      )}
    </div>
  )
}
