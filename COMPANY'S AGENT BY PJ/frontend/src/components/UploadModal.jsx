import { useRef, useState } from 'react'
import { uploadDocument } from '../api.js'

export default function UploadModal({ onClose, onDone }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const upload = async (file) => {
    if (!file) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await uploadDocument(file))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <div className="drawer-title">Add a document to the knowledge base</div>
            <div className="drawer-sub">PDF only. It will be parsed, chunked, embedded and searchable.</div>
          </div>
          <button className="icon-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            upload(e.dataTransfer.files?.[0])
          }}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => upload(e.target.files?.[0])}
          />
          {busy ? 'Parsing, chunking and embedding…' : 'Drag a PDF here, or click to browse'}
        </div>

        {error && <div className="error-banner">{error}</div>}
        {result && (
          <div className="upload-result">
            ✅ <b>{result.title}</b>: {result.pages} pages → {result.chunks} chunks indexed.
            <button className="btn primary" onClick={onDone}>
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
