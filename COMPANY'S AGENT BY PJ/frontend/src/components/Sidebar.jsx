import { useRef, useState } from 'react'
import * as api from '../api.js'
import UploadModal from './UploadModal.jsx'

export default function Sidebar({
  sessions,
  activeSession,
  onOpenSession,
  onNewChat,
  onDeleteSession,
  onClearAllHistory,
  documents,
  stats,
  onUpload,
}) {
  const [showUpload, setShowUpload] = useState(false)
  return (
    <aside className="sidebar">
      <div className="brand">
        <img src="/app_logo.png" className="app-logo sidebar-logo" alt="PJ Logo" />
        <div>
          <div className="brand-name">Company's Agent by PJ</div>
          <div className="brand-tag">Agentic Policy & Knowledge AI</div>
        </div>
      </div>

      <button className="btn primary block new-chat-btn" onClick={onNewChat}>
        <span>+</span> New chat
      </button>

      <div className="section">
        <div className="section-title row">
          <span>Conversations</span>
          {sessions.length > 0 && (
            <button
              className="link danger-link"
              onClick={onClearAllHistory}
              title="Clear all conversation history"
            >
              Clear all
            </button>
          )}
        </div>
        <div className="session-list">
          {sessions.length === 0 && <div className="empty">No conversations yet</div>}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeSession ? 'active' : ''}`}
            >
              <button
                className="session-title-btn"
                onClick={() => onOpenSession(s.id)}
                title={s.title}
              >
                <span className="session-icon">💬</span>
                <span className="session-label">{s.title}</span>
              </button>
              <button
                className="session-delete-btn"
                title="Delete this chat"
                onClick={(e) => onDeleteSession?.(s.id, e)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="section grow">
        <div className="section-title row">
          Knowledge base
          <button className="link" onClick={() => setShowUpload(true)}>
            + Upload
          </button>
        </div>
        <div className="doc-list">
          {documents.length === 0 && <div className="empty">No documents indexed</div>}
          {documents.map((d) => (
            <div key={d.doc_id} className="doc" title={d.filename}>
              <span className="doc-icon">PDF</span>
              <span className="doc-name">{d.title}</span>
              <span className="doc-chunks">{d.chunks}</span>
              <button
                className="icon-btn"
                title="Delete"
                onClick={async () => {
                  if (!confirm(`Remove "${d.title}" from the index?`)) return
                  await api.deleteDocument(d.doc_id)
                  onUpload()
                }}
              >
                🗑
              </button>
            </div>
          ))}
        </div>
      </div>

      {stats && (
        <div className="stats">
          <div>Model <b>{stats.embeddings.provider}</b> · {stats.embeddings.model}</div>
          <div>
            Hybrid search <b>on</b> · Reranker <b>{stats.reranker.enabled ? 'on' : 'off'}</b>
          </div>
          <div>
            Feedback: 👍 {stats.feedback.up} · 👎 {stats.feedback.down}
          </div>
        </div>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onDone={() => {
            setShowUpload(false)
            onUpload()
          }}
        />
      )}
    </aside>
  )
}
