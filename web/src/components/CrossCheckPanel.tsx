/** Beat 3 fallback: match-weight panel with a simulated badge until Splink (M6) is live. */

const WEIGHTS = [
  { field: 'Institution name', weight: 12.4, match: true },
  { field: 'Trust PAN (masked)', weight: 8.1, match: true },
  { field: 'Registered address', weight: 3.2, match: false },
  { field: 'Faculty identifiers', weight: 1.1, match: true },
]

export default function CrossCheckPanel() {
  return (
    <div className="card">
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>Cross-checks</span>
        <span className="placeholder-badge">simulated</span>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
        Splink probabilistic links are a Should-tier milestone (M6). This panel is seeded match weights so the dossier structure is complete for the demo.
      </p>
      {WEIGHTS.map((w) => (
        <div key={w.field} style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6, fontSize: 12 }}>
          <span style={{ flex: 1 }}>{w.field}</span>
          <div style={{ width: 90, height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(100, w.weight * 7)}%`, height: '100%', background: w.match ? 'var(--green)' : 'var(--amber)' }} />
          </div>
          <span style={{ color: w.match ? 'var(--green)' : 'var(--amber)', width: 48, textAlign: 'right' }}>
            {w.weight.toFixed(1)}
          </span>
        </div>
      ))}
    </div>
  )
}
