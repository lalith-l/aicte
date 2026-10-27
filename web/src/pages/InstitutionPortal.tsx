import { useState } from 'react'
import type { Finding } from '../types'
import LoadingSpinner from '../components/LoadingSpinner'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

interface ConsentItem {
  id: string
  institution_id: string
  document_types: string[] | string
  purpose: string
  expires_at: string
  revoked_at?: string | null
  created_at?: string
}

// Institution-facing finding: no tier codes, no defect codes, amber guidance only
function InstitutionFindingRow({ finding, onRectify }: { finding: Finding; note: string; onNoteChange: (v: string) => void; onRectify: () => void }) {
  const [note, setNote] = useState('')
  const clearanceGuide: Record<string, string> = {
    D04: 'Upload a fresh affidavit executed on or after the stamp paper purchase date.',
    D09: 'Submit a certified demarcation map from the Revenue Inspector confirming the campus area.',
    D02: 'Obtain a renewed Fire & Safety NOC from the State Disaster & Fire Services Department.',
    D13: 'The issuer portal is temporarily unavailable. No action needed — this will be re-checked automatically.',
  }
  const guidance = clearanceGuide[finding.source_code] ||
    (finding.recheck_recipe ? `To clear this item: ${finding.recheck_recipe}` : 'Contact the scrutiny officer for guidance on clearing this item.')

  return (
    <div className="card" style={{ padding: 16, borderLeft: '3px solid var(--amber)' }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
        {finding.source_code === 'D13' ? 'Issuer verification pending' :
         finding.source_code === 'D04' ? 'Document date inconsistency' :
         finding.source_code === 'D09' ? 'Land area discrepancy' :
         finding.source_code === 'D02' ? 'Certificate expired' :
         'Document requires attention'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10, lineHeight: 1.5 }}>
        {finding.reason.replace(/\[DEMO SEED\]\s*/i, '')}
      </div>
      <div style={{ padding: '8px 12px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 6, fontSize: 12, color: 'var(--amber)', marginBottom: 12 }}>
        <strong>To clear this item:</strong> {guidance}
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <input
          className="input"
          placeholder="Enter rectification note / reference number…"
          value={note}
          onChange={e => setNote(e.target.value)}
          style={{ flex: 1 }}
        />
        <button
          className="btn btn--primary"
          style={{ fontSize: 12, whiteSpace: 'nowrap' }}
          onClick={onRectify}
        >
          Submit Rectification
        </button>
      </div>
    </div>
  )
}

const AVAILABLE_DOCS = [
  { id: 'land_record', label: 'Land Deed & Title' },
  { id: 'noc', label: 'State Government NOC' },
  { id: 'fire_safety', label: 'Fire & Safety Certificate' },
  { id: 'affiliation', label: 'University Affiliation Order' },
]

export default function InstitutionPortal() {
  const { data, loading, reload } = useApi<{ deficiencies: Finding[] }>(() => api.get('/api/portal/deficiencies'), [])
  const { data: consent, reload: reloadConsent } = useApi<{ artifacts: ConsentItem[] }>(
    () => api.get('/api/portal/consent'),
    [],
  )

  const [selectedDocs, setSelectedDocs] = useState<string[]>(['noc', 'land_record'])
  const [purpose, setPurpose] = useState('Statutory verification against state & municipal mock issuers')
  const [expiryDays, setExpiryDays] = useState(30)
  const [rectifyNotes, setRectifyNotes] = useState<Record<string, string>>({})
  const [submittingConsent, setSubmittingConsent] = useState(false)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  function toggleDoc(docId: string) {
    setSelectedDocs(prev =>
      prev.includes(docId) ? prev.filter(d => d !== docId) : [...prev, docId]
    )
  }

  async function handleGrantConsent(e: React.FormEvent) {
    e.preventDefault()
    if (selectedDocs.length === 0) {
      setStatusMsg('Please select at least one document type for consent.')
      return
    }
    setSubmittingConsent(true)
    setStatusMsg(null)
    try {
      await api.post('/api/portal/consent', {
        document_types: selectedDocs,
        purpose,
        days: expiryDays,
      })
      setStatusMsg('Consent granted successfully via OAuth2/PKCE protocol.')
      reloadConsent()
    } catch (err: any) {
      setStatusMsg(err?.message || 'Failed to grant consent')
    } finally {
      setSubmittingConsent(false)
    }
  }

  async function handleRevoke(consentId: string) {
    try {
      await api.post(`/api/portal/consent/${consentId}/revoke`, {})
      reloadConsent()
    } catch (err: any) {
      alert(err?.message || 'Failed to revoke consent')
    }
  }

  async function handleRectify(findingId: string) {
    const note = rectifyNotes[findingId] || 'Rectification evidence uploaded (synthetic)'
    try {
      await api.post('/api/portal/rectify', { finding_id: findingId, note })
      setRectifyNotes(prev => ({ ...prev, [findingId]: '' }))
      reload()
    } catch (err: any) {
      alert(err?.message || 'Failed to submit rectification')
    }
  }

  const items = data?.deficiencies || []
  const consentList = consent?.artifacts || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1100 }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Institution Portal</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Statutory verification consent, deficiency rectification, and application status. Synthetic data only.
        </p>
      </div>

      {statusMsg && (
        <div style={{ padding: '10px 14px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', borderRadius: 6, fontSize: 13, color: 'var(--blue)' }}>
          ℹ {statusMsg}
        </div>
      )}

      {/* Consent Management Card */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>Consent Management (OAuth2 PKCE)</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              Grant time-bounded, scoped cryptographic authorization for officers to query external issuers on your behalf.
            </p>
          </div>
          <span className="badge badge--verified" style={{ fontSize: 11 }}>PKCE Enabled</span>
        </div>

        <form onSubmit={handleGrantConsent} style={{ background: 'rgba(255,255,255,0.02)', padding: 16, borderRadius: 8, border: '1px solid var(--border)' }}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
              Select Documents to Authorize:
            </label>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {AVAILABLE_DOCS.map(doc => (
                <label key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedDocs.includes(doc.id)}
                    onChange={() => toggleDoc(doc.id)}
                  />
                  <span>{doc.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: 12, marginBottom: 14 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Verification Purpose:
              </label>
              <input
                className="input"
                value={purpose}
                onChange={e => setPurpose(e.target.value)}
                placeholder="State purpose of verification"
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Validity Duration:
              </label>
              <select
                className="input"
                value={expiryDays}
                onChange={e => setExpiryDays(Number(e.target.value))}
              >
                <option value={15}>15 Days</option>
                <option value={30}>30 Days (Standard)</option>
                <option value={60}>60 Days</option>
                <option value={90}>90 Days</option>
                <option value={365}>1 Year</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn--primary"
            disabled={submittingConsent}
            style={{ fontSize: 13 }}
          >
            {submittingConsent ? 'Granting...' : 'Grant Consent'}
          </button>
        </form>

        {/* Existing Consents List */}
        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Active & Historical Consents ({consentList.length})
          </h3>
          {consentList.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', padding: 8 }}>
              No consent artifacts recorded.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {consentList.map(c => {
                const isRevoked = Boolean(c.revoked_at)
                const isExpired = new Date(c.expires_at).getTime() < Date.now()
                const docTypes = Array.isArray(c.document_types)
                  ? c.document_types
                  : typeof c.document_types === 'string'
                  ? JSON.parse(c.document_types || '[]')
                  : []

                return (
                  <div
                    key={c.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      gap: 12,
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{c.purpose}</div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          Expires: {new Date(c.expires_at).toLocaleDateString()}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>·</span>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {docTypes.map((dt: string) => (
                            <span key={dt} className="badge badge--neutral" style={{ fontSize: 10 }}>{dt}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {isRevoked ? (
                        <span className="badge badge--rejected" style={{ fontSize: 11 }}>Revoked</span>
                      ) : isExpired ? (
                        <span className="badge badge--unknown" style={{ fontSize: 11 }}>Expired</span>
                      ) : (
                        <>
                          <span className="badge badge--verified" style={{ fontSize: 11 }}>Active</span>
                          <button
                            className="btn btn--danger"
                            style={{ fontSize: 11, padding: '4px 10px' }}
                            onClick={() => handleRevoke(c.id)}
                          >
                            Revoke
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Items to Fix Section */}
      <div>
        <div style={{ marginBottom: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Items to Fix</h2>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            Address the deficiencies identified below and provide rectification evidence.
          </p>
        </div>

        {loading && <LoadingSpinner label="Loading items to fix…" />}

        {!loading && items.length === 0 && (
          <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>✓</div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>No items require rectification at this time.</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>All submitted documents have cleared preliminary validation.</div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {items.map(f => (
            <InstitutionFindingRow
              key={f.id}
              finding={{ ...f, application_id: f.application_id || '' }}
              note={rectifyNotes[f.id] || ''}
              onNoteChange={v => setRectifyNotes(prev => ({ ...prev, [f.id]: v }))}
              onRectify={() => handleRectify(f.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
