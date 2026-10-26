import { useState } from 'react'
import { api, setToken } from '../api/client'

const DEMO_USERS = [
  { username: 'officer_raj', password: 'demo123', role: 'scrutiny_officer', label: 'Scrutiny Officer' },
  { username: 'supervisor_priya', password: 'demo123', role: 'supervisor', label: 'Supervisor' },
  { username: 'auditor_amit', password: 'demo123', role: 'auditor', label: 'Auditor' },
  { username: 'rules_meera', password: 'demo123', role: 'rules_admin', label: 'Rules Admin' },
  { username: 'sunrise_admin', password: 'demo123', role: 'institution_user', label: 'Institution User' },
  { username: 'sysadmin_dev', password: 'demo123', role: 'sysadmin', label: 'System Admin' },
]

interface Props {
  onLogin: (username: string, role: string) => void
}

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.login(username, password)
      setToken(res.access_token, res.role)
      onLogin(username, res.role)
    } catch {
      // Fallback: demo login without real API
      const demo = DEMO_USERS.find(u => u.username === username && u.password === password)
      if (demo) {
        setToken('demo-token-' + Date.now(), demo.role)
        localStorage.setItem('aicte_username', demo.username)
        onLogin(demo.username, demo.role)
      } else {
        setError('Invalid credentials. Use demo users below.')
      }
    } finally {
      setLoading(false)
    }
  }

  async function quickLogin(u: typeof DEMO_USERS[0]) {
    setLoading(true)
    setError('')
    try {
      const res = await api.login(u.username, u.password)
      setToken(res.access_token, res.role)
      localStorage.setItem('aicte_username', u.username)
      onLogin(u.username, res.role)
    } catch {
      setToken('demo-token-' + Date.now(), u.role)
      localStorage.setItem('aicte_username', u.username)
      onLogin(u.username, u.role)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.03em' }}>AICTE Validator</div>
          <div style={{ fontSize: 12, color: 'var(--amber)', marginTop: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Synthetic Data Prototype
          </div>
          <div style={{ marginTop: 8, padding: '6px 16px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, display: 'inline-block', fontSize: 11, color: 'var(--amber)' }}>
            ⚠ All data is synthetic — for demonstration only
          </div>
        </div>

        {/* Login form */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Sign In</h2>
          <form onSubmit={handleLogin}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Username</label>
                <input
                  className="input"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="officer_raj"
                  required
                  autoComplete="username"
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Password</label>
                <input
                  className="input"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="demo123"
                  required
                  autoComplete="current-password"
                />
              </div>
              {error && <div style={{ fontSize: 12, color: 'var(--red)', padding: '8px 12px', background: 'var(--red-bg)', borderRadius: 6 }}>{error}</div>}
              <button className="btn btn--primary" type="submit" disabled={loading} style={{ marginTop: 4 }}>
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
            </div>
          </form>
        </div>

        {/* Quick login buttons */}
        <div className="card">
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Quick Demo Login (password: demo123)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {DEMO_USERS.map(u => (
              <button key={u.username} className="btn" style={{ fontSize: 11, flexDirection: 'column', alignItems: 'flex-start', padding: '8px 12px', gap: 2 }} onClick={() => quickLogin(u)}>
                <span style={{ fontWeight: 600 }}>{u.label}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{u.username}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
