import type { BoundingBox } from '../types'
import { API_BASE, getToken } from '../api/client'

interface Props {
  docId: string
  title: string
  pageCount: number
  boxes: BoundingBox[]
  fileRef?: string
}

export default function PdfViewer({ docId, title, pageCount, boxes, fileRef }: Props) {
  const token = getToken()
  const pdfUrl = `${API_BASE}/api/documents/${docId}/file${token ? `?token=${encodeURIComponent(token)}` : ''}`
  const linked = boxes.filter((b) => b.doc_id === docId)

  return (
    <div className="pdf-viewer">
      <div className="pdf-viewer__page">
        <div className="pdf-viewer__header">
          <span className="pdf-viewer__stamp">SYNTHETIC</span>
          <h3>{title}</h3>
          <p>AICTE Approval Process Prototype · page 1 of {pageCount}</p>
        </div>
        <div className="pdf-viewer__body">
          <div className="pdf-viewer__line" />
          <div className="pdf-viewer__line short" />
          <div className="pdf-viewer__field" style={{ top: 86, left: 28 }}>Institution / document fields (extracted)</div>
          {linked.map((b, i) => (
            <div
              key={`${b.page}-${i}`}
              className={`bbox bbox--tier${i === 0 ? '1' : '2'}`}
              style={{
                left: Math.max(12, Math.min(b.x / 2, 280)),
                top: Math.max(70, Math.min(b.y / 2.2, 200)),
                width: Math.max(80, b.w),
                height: Math.max(18, b.h),
              }}
              title={`Evidence box page ${b.page}`}
            >
              evidence p{b.page}
            </div>
          ))}
          {linked.length === 0 && (
            <div className="pdf-viewer__empty">No evidence bounding boxes on this page</div>
          )}
        </div>
        <div className="pdf-viewer__footer">
          OS-level sandbox, reduced isolation · {fileRef || 'seeded facsimile'}
        </div>
      </div>
      <div className="pdf-viewer__actions">
        <a className="btn" href={pdfUrl} target="_blank" rel="noreferrer">Open PDF bytes</a>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {linked.length} overlay{linked.length === 1 ? '' : 's'} · coloured by finding tier
        </span>
      </div>
    </div>
  )
}
