import { useState } from 'react'
import type { Rule } from '../types'
import StatusChip from '../components/StatusChip'
import LoadingSpinner from '../components/LoadingSpinner'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

export default function RulesAdmin() {
  const { data, loading, error, reload } = useApi<{ rules: Rule[]; persisted?: any[] }>(() => api.get('/api/rules'), [])
  const [filterSeverity, setFilterSeverity] = useState('ALL')
  const [search, setSearch] = useState('')
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null)
  const [candidateClause, setCandidateClause] = useState('')
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [whatIfResult, setWhatIfResult] = useState<any | null>(null)
  const [actionMsg, setActionMsg] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null)
  const [authLoading, setAuthLoading] = useState(false)

  const rules = data?.rules || []
  const totalCount = rules.length
  const placeholderCount = rules.filter(r => r.is_placeholder || r.clause_ref === 'PLACEHOLDER').length
  const activeCount = rules.filter(r => r.status === 'ACTIVE').length

  const filteredRules = rules.filter(r => {
    if (filterSeverity !== 'ALL' && r.severity !== filterSeverity) return false
    if (!search) return true
    const q = search.toLowerCase()
    return (
      r.name.toLowerCase().includes(q) ||
      r.id.toLowerCase().includes(q) ||
      r.description.toLowerCase().includes(q) ||
      (r.clause_ref && r.clause_ref.toLowerCase().includes(q))
    )
  })

  async function handleQuickAuth() {
    setAuthLoading(true)
    try {
      const res = await api.login('rules_meera', 'demo123')
      localStorage.setItem('aicte_token', res.access_token)
      localStorage.setItem('aicte_role', res.role)
      localStorage.setItem('aicte_username', 'rules_meera')
      setActionMsg({ text: 'Authenticated as rules_meera (Rules Admin)', type: 'success' })
      reload()
    } catch (e: any) {
      setActionMsg({ text: `Auth failed: ${e.message}`, type: 'error' })
    } finally {
      setAuthLoading(false)
    }
  }

  async function approve(id: string) {
    setActionMsg(null)
    const rule = rules.find(r => r.id === id)
    if (rule && (rule.is_placeholder || rule.clause_ref === 'PLACEHOLDER')) {
      setActionMsg({
        text: '⛔ Blocked by Fail-Closed Gate: This rule has clause_ref = "PLACEHOLDER". A human official must enter the official AICTE handbook clause before this rule can be activated. The system will not approve placeholder rules.',
        type: 'error',
      })
      return
    }
    try {
      await api.post(`/api/rules/${id}/approve`, {})
      setActionMsg({ text: `✓ Rule ${id} approved successfully`, type: 'success' })
      reload()
    } catch (e: any) {
      const errStr = String(e)
      if (errStr.includes('PLACEHOLDER') || errStr.includes('400')) {
        setActionMsg({
          text: '⛔ Blocked by Fail-Closed Gate: Rules with PLACEHOLDER clause_ref cannot be approved. A human official must input the official AICTE handbook clause.',
          type: 'error',
        })
      } else {
        setActionMsg({ text: `Approval failed: ${errStr}`, type: 'error' })
      }
    }
  }

  async function runWhatIf(rule: Rule) {
    setSelectedRule(rule)
    setCandidateClause(rule.clause_ref || '4.1(a)')
    setWhatIfLoading(true)
    setWhatIfResult(null)
    try {
      const res = await api.post<any>('/api/rules/what-if', {
        rule_id: rule.id,
        candidate_clause_ref: '4.1(a)',
      })
      setWhatIfResult(res)
    } catch (e: any) {
      setActionMsg({ text: `What-If simulation failed: ${e.message}`, type: 'error' })
    } finally {
      setWhatIfLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Rules Admin & Handbook Register</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            Human-owned handbook register. Rules evaluate strictly to UNKNOWN and cannot be activated until official clauses are populated.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span className="badge badge--neutral" style={{ fontSize: 12, padding: '4px 10px' }}>
            Fail-Closed Gate Active
          </span>
          {rules.length > 0 && (
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
              Connected to Register API ({rules.length} norms)
            </span>
          )}
        </div>
      </div>

      {/* Summary strip */}
      <div className="summary-strip">
        <div className="summary-stat">
          <div className="summary-stat__value">{totalCount}</div>
          <div className="summary-stat__label">Total Norms</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: 'var(--amber)' }}>{placeholderCount}</div>
          <div className="summary-stat__label">Placeholder Norms</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: activeCount > 0 ? 'var(--green)' : 'var(--text-muted)' }}>
            {activeCount}
          </div>
          <div className="summary-stat__label">Active Norms</div>
        </div>
        <div className="summary-stat">
          <div className="summary-stat__value" style={{ color: 'var(--blue)' }}>Strict UNKNOWN</div>
          <div className="summary-stat__label">Eval Logic</div>
        </div>
      </div>

      {/* Action / Notification Banner */}
      {actionMsg && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            lineHeight: 1.5,
            background:
              actionMsg.type === 'error'
                ? 'rgba(239, 68, 68, 0.12)'
                : actionMsg.type === 'success'
                ? 'rgba(34, 197, 94, 0.12)'
                : 'rgba(59, 130, 246, 0.12)',
            color:
              actionMsg.type === 'error'
                ? 'var(--red)'
                : actionMsg.type === 'success'
                ? 'var(--green)'
                : 'var(--blue)',
            border: `1px solid ${
              actionMsg.type === 'error'
                ? 'rgba(239, 68, 68, 0.3)'
                : actionMsg.type === 'success'
                ? 'rgba(34, 197, 94, 0.3)'
                : 'rgba(59, 130, 246, 0.3)'
            }`,
          }}
        >
          {actionMsg.text}
        </div>
      )}

      {/* Loading state */}
      {loading && !data && <LoadingSpinner label="Loading register norms from API…" />}

      {/* Error state */}
      {error && !data && (
        <div className="card" style={{ padding: 20, textAlign: 'center', background: 'rgba(245, 158, 11, 0.05)' }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🔒</div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--amber)' }}>Rules Admin Access Restricted</h3>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', maxWidth: 500, margin: '8px auto 16px' }}>
            Viewing and configuring the handbook register requires an authenticated session with Rules Admin or Scrutiny Officer role.
          </p>
          <button
            className="btn btn--primary"
            onClick={handleQuickAuth}
            disabled={authLoading}
          >
            {authLoading ? 'Authenticating…' : 'Authenticate as Rules Admin (rules_meera)'}
          </button>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <input
          className="input"
          placeholder="Search rule name, ID, or description…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 2, minWidth: 200 }}
        />
        <select
          className="input"
          value={filterSeverity}
          onChange={e => setFilterSeverity(e.target.value)}
          style={{ flex: 1, minWidth: 140 }}
        >
          <option value="ALL">All Severities</option>
          <option value="MUST">MUST</option>
          <option value="SHOULD">SHOULD</option>
          <option value="COULD">COULD</option>
        </select>
      </div>

      {/* What-If Simulation Panel (Modal/Drawer) */}
      {selectedRule && (
        <div
          className="card"
          style={{
            padding: 20,
            border: '1px solid var(--blue)',
            background: 'rgba(59, 130, 246, 0.04)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <span className="badge badge--info" style={{ marginBottom: 6 }}>What-If Simulation</span>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>{selectedRule.name} ({selectedRule.id})</h3>
            </div>
            <button
              className="btn"
              style={{ fontSize: 11, padding: '4px 8px' }}
              onClick={() => { setSelectedRule(null); setWhatIfResult(null); }}
            >
              ✕ Close
            </button>
          </div>

          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>
            Simulate the impact of transitioning this handbook norm from PLACEHOLDER to an active handbook clause across historical synthetic applications.
          </p>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Candidate Clause Ref:</label>
            <input
              className="input"
              value={candidateClause}
              onChange={e => setCandidateClause(e.target.value)}
              placeholder="e.g. 4.1(a) or Annexure 6"
              style={{ width: 200, fontSize: 12 }}
            />
            <button
              className="btn btn--primary"
              style={{ fontSize: 12 }}
              onClick={() => runWhatIf(selectedRule)}
              disabled={whatIfLoading}
            >
              {whatIfLoading ? 'Simulating…' : 'Run What-If Evaluation'}
            </button>
          </div>

          {whatIfResult && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, padding: 12, background: 'rgba(0,0,0,0.25)', borderRadius: 6 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total Evaluated</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{whatIfResult.total_evaluated} apps</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Flips to Deficient</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--red)' }}>{whatIfResult.flips_to_deficient}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Flips to Unknown</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--amber)' }}>{whatIfResult.flips_to_unknown}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Flips to Pass</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>{whatIfResult.flips_to_pass}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Rules list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filteredRules.map(r => (
          <div key={r.id} className="card" style={{ padding: '16px 20px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span>
                  <StatusChip status={r.severity} small />
                  <StatusChip status={r.status} small />
                  {r.is_placeholder && (
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 600,
                        background: 'rgba(245, 158, 11, 0.12)',
                        color: 'var(--amber)',
                        border: '1px dashed var(--amber)',
                        letterSpacing: '0.04em',
                      }}
                    >
                      PLACEHOLDER: Clause Reference
                    </span>
                  )}
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                  {r.description}
                </p>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, fontFamily: 'monospace' }}>
                  Norm ID: <span style={{ color: 'var(--text-secondary)' }}>{r.id}</span> · Clause Ref:{' '}
                  <span style={{ color: r.clause_ref === 'PLACEHOLDER' ? 'var(--amber)' : 'var(--blue)' }}>
                    {r.clause_ref}
                  </span>
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button
                  className="btn"
                  style={{ fontSize: 12, padding: '6px 12px' }}
                  onClick={() => runWhatIf(r)}
                >
                  What-If Simulation
                </button>
                <button
                  className="btn btn--primary"
                  style={{
                    fontSize: 12,
                    padding: '6px 12px',
                    opacity: (r.is_placeholder || r.clause_ref === 'PLACEHOLDER') ? 0.5 : 1,
                    cursor: (r.is_placeholder || r.clause_ref === 'PLACEHOLDER') ? 'not-allowed' : 'pointer',
                  }}
                  onClick={() => approve(r.id)}
                  title={(r.is_placeholder || r.clause_ref === 'PLACEHOLDER') ? 'Cannot approve: clause_ref is PLACEHOLDER' : 'Attempt rule activation'}
                >
                  Approve Rule
                </button>
              </div>
            </div>

            {/* Conditions snippet */}
            {r.conditions && r.conditions.length > 0 && (
              <div
                style={{
                  marginTop: 12,
                  padding: '8px 12px',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  fontSize: 11,
                  display: 'flex',
                  gap: 16,
                  color: 'var(--text-muted)',
                }}
              >
                <span><strong>Evaluates field:</strong> {r.conditions[0].field}</span>
                <span><strong>Operator:</strong> {r.conditions[0].operator}</span>
                <span><strong>Target:</strong> {String(r.conditions[0].target_value)}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
