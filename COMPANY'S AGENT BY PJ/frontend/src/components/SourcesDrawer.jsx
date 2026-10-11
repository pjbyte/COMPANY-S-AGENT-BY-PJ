export default function SourcesDrawer({ sources, onClose }) {
  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div>
          <div className="drawer-title">Retrieved sources</div>
          <div className="drawer-sub">Chunks the agent used, ranked by relevance</div>
        </div>
        <button className="icon-btn" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="drawer-body">
        {sources.map((c) => (
          <details key={c.index} className="source-card" open={c.index === 1}>
            <summary>
              <span className="chip static">[{c.index}]</span>
              <b>{c.doc_title}</b>
              <span className="muted"> · page {c.page}{c.section ? ` · ${c.section}` : ''} · score {c.score}</span>
            </summary>
            <p className="source-text">{c.snippet}...</p>
          </details>
        ))}
      </div>
    </aside>
  )
}
