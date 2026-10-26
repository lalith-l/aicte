import { useApi } from '../hooks/useApi'
import { api } from '../api/client'

export default function HeadHashFooter() {
  const { data } = useApi<{
    status: string
    published_head?: { date: string; head_hash?: string; hash?: string; entry_count?: number }
    sandbox: string
  }>(() => api.get('/api/health'), [])

  const hash = data?.published_head?.head_hash || data?.published_head?.hash || ''
  return (
    <div className="app-footer">
      <span>All data is synthetic</span>
      <span>Sandbox: {data?.sandbox || 'OS-level, reduced isolation'}</span>
      <span className="app-footer__hash">
        Published head {data?.published_head?.date || '—'} · {hash ? `${hash.slice(0, 16)}…` : 'not published yet'}
      </span>
    </div>
  )
}
