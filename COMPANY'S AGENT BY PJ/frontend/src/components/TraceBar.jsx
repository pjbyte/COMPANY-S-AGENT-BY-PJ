// Renders the agent's decision path as step pills, e.g.
// rewrite → route: policy_docs → retrieve 5 → grade 3/5 → generate → audit ✓

const ICONS = {
  start: '▶',
  rewrite_query: '✎',
  route: '🧭',
  retrieve: '🔎',
  grade_documents: '⚖',
  retry_retrieve: '↻',
  web_search: '🌐',
  generate: '✍',
  check_grounded: '🛡',
  regenerate: '🔁',
  web_generate: '🌐',
  direct_generate: '💬',
  smalltalk_generate: '👋',
  no_docs: '∅',
  build_citations: '📚',
  end: '■',
}

export default function TraceBar({ trace }) {
  if (!trace?.length) return null
  return (
    <div className="tracebar" title="The agent's decision path for this answer">
      {trace.map((t, i) => (
        <span key={i} className={`pill step-${t.step}`}>
          <span className="pill-icon">{ICONS[t.step] || '·'}</span>
          <span className="pill-step">{t.step.replace(/_/g, ' ')}</span>
          <span className="pill-detail">{t.detail}</span>
        </span>
      ))}
    </div>
  )
}
