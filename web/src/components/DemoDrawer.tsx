import { useState } from 'react'
import { api } from '../api/client'

const ROLES = [
  'institution_user',
  'scrutiny_officer',
  'supervisor',
  'auditor',
  'rules_admin',
  'sysadmin',
]

const ROLE_USERS: Record<string, string> = {
  institution_user: 'sunrise_admin',
  scrutiny_officer: 'officer_raj',
  supervisor: 'supervisor_priya',
  auditor: 'auditor_amit',
  rules_admin: 'rules_meera',
  sysadmin: 'sysadmin_dev',
}

export default function DemoDrawer({ onRolePreview }: { onRolePreview?: (role: string) => void }) {
  const [open, setOpen] = useState(false)
  const [chaos, setChaos] = useState(false)
  const [role, setRole] = useState(localStorage.getItem('aicte_role') || 'scrutiny_officer')
  const [mode, setMode] = useState<'NORMAL' | 'DEGRADED'>('NORMAL')
  const [resetting, setResetting] = useState(false)
  const [resetMsg, setResetMsg] = useState('')

  async function toggleChaos() {
    const next = !chaos
    setChaos(next)
    try {
      await api.post('/api/demo/chaos', { enabled: next })
    } catch { /* mock may not be running */ }
  }

  async function setSystemMode(m: 'NORMAL' | 'DEGRADED') {
    setMode(m)
    try {
      await api.put('/api/system/mode', { mode: m, reason: 'demo drawer toggle' })
    } catch { /* API may not be running */ }
  }

  async function resetDatabase() {
    setResetting(true)
    setResetMsg('')
    try {
      await api.post('/api/system/reset-demo', {})
      setResetMsg('✓ Database reset to Sunrise seed')
    } catch {
      setResetMsg('⚠ Reset endpoint unavailable (run seed_demo.py manually)')
    } finally {
      setResetting(false)
    }
  }

  return (
    <>
      <button className="demo-drawer__toggle" onClick={() => setOpen(!open)}>DEMO</button>
      <div className={`demo-drawer ${open ? 'demo-drawer--open' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--purple)' }}>Demo Controls</h3>
          <button className="btn" style={{ fontSize: 11, padding: '4px 8px' }} onClick={() => setOpen(false)}>✕</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Chaos Switch */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Chaos Switch
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 6 }}>
              <div className={`toggle ${chaos ? 'toggle--active' : ''}`} onClick={toggleChaos}>
                <div className="toggle__knob" />
              </div>
              <div>
                <div style={{ fontSize: 13 }}>{chaos ? '🔴 Issuers returning 503' : '🟢 Normal'}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {chaos ? 'SOURCE_UNAVAILABLE — not a rejection' : 'All issuers online'}
                </div>
              </div>
            </div>
          </div>

          {/* Role Switcher */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Role Switcher
            </label>
            <select
              value={role}
              onChange={async e => {
                const next = e.target.value
                setRole(next)
                onRolePreview?.(next)
                const username = ROLE_USERS[next]
                if (username) {
                  try {
                    const res = await api.login(username, 'demo123')
                    localStorage.setItem('aicte_token', res.access_token)
                    localStorage.setItem('aicte_role', res.role)
                    localStorage.setItem('aicte_username', username)
                  } catch { /* demo token already set */ }
                }
              }}
              style={{ width: '100%', marginTop: 6, padding: '8px 12px', background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: 13 }}
            >
              {ROLES.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
            </select>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              Current token role: <strong>{localStorage.getItem('aicte_role') || 'not logged in'}</strong>
            </div>
          </div>

          {/* System Mode */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              System Mode
            </label>
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <button className={`btn ${mode === 'NORMAL' ? 'btn--primary' : ''}`} onClick={() => setSystemMode('NORMAL')} style={{ flex: 1, fontSize: 12 }}>NORMAL</button>
              <button className={`btn ${mode === 'DEGRADED' ? 'btn--danger' : ''}`} onClick={() => setSystemMode('DEGRADED')} style={{ flex: 1, fontSize: 12 }}>DEGRADED</button>
            </div>
            {mode === 'DEGRADED' && (
              <div style={{ marginTop: 6, fontSize: 11, color: 'var(--amber)' }}>
                ⚠ Wider review queue — uncertain evidence passes
              </div>
            )}
          </div>

          {/* Reset Database */}
          <div>
            <button className="btn btn--danger" style={{ width: '100%' }} onClick={resetDatabase} disabled={resetting}>
              {resetting ? '⏳ Resetting…' : '🔄 Reset Database'}
            </button>
            {resetMsg && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{resetMsg}</div>}
          </div>

          {/* Audit Chain Demonstration */}
          <div style={{ padding: 12, background: 'rgba(99, 102, 241, 0.08)', borderRadius: 8, border: '1px solid rgba(99, 102, 241, 0.2)', fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            <div style={{ fontWeight: 600, color: 'var(--purple)', marginBottom: 4 }}>Audit Chain Verification Test:</div>
            Tamper any row in the database → Verifier immediately detects broken sequence. Even if recomputed internally, the published external head still fails.
            <button
              className="btn"
              style={{ width: '100%', fontSize: 11, marginTop: 8, padding: '4px 8px' }}
              onClick={async () => {
                try {
                  await api.post('/api/audit/publish-head', {})
                  alert('Published today external head hash.')
                } catch (e: any) {
                  alert(e?.message || 'Error publishing head')
                }
              }}
            >
              Anchor / Publish Daily Head
            </button>
          </div>

          <div style={{ padding: 12, background: 'rgba(245,158,11,0.08)', borderRadius: 8, fontSize: 11, color: 'var(--amber)', lineHeight: 1.5 }}>
            All data is synthetic. This drawer is only visible in demo mode. Do not use for production decisions.
          </div>
        </div>
      </div>
    </>
  )
}
