import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import TraceBar from './TraceBar.jsx'

const SUGGESTIONS = [
  'How many annual leave days do I get and how many carry forward?',
  'What are the password requirements for company accounts?',
  'I clicked a phishing link - what should I do?',
  'How much is the home office setup stipend?',
]

export default function ChatWindow({ messages, streaming, onSend, onStop, onClear, onOpenSources, onFeedback }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  const submit = (e) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || streaming) return
    setInput('')
    onSend(q)
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length > 0 && (
          <div className="chat-control-bar">
            <span className="chat-counter">Active conversation · {messages.length} message{messages.length === 1 ? '' : 's'}</span>
            <button
              type="button"
              className="btn btn-sm btn-clear"
              onClick={onClear}
              title="Clear current chat history"
            >
              🗑️ Clear chat history
            </button>
          </div>
        )}
        {messages.length === 0 && (
          <div className="hero">
            <div className="hero-badge">
              <img src="/app_logo.png" className="hero-logo" alt="PJ Emblem" />
            </div>
            <h1>Company's Agent by PJ</h1>
            <p>
              Ask your company's HR, IT, and workplace policies anything. Grounded answers with
              page-level citations, retrieved by hybrid search and audited by an agent loop.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => onSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Message
            key={m.id}
            message={m}
            onOpenSources={onOpenSources}
            onFeedback={onFeedback}
            isStreamingTail={streaming && i === messages.length - 1 && m.role === 'assistant'}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <form className="composer" onSubmit={submit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about leave, IT security, expenses..."
          disabled={streaming}
        />
        {streaming ? (
          <button type="button" className="btn primary" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn primary" disabled={!input.trim()}>
            Send
          </button>
        )}
      </form>
    </div>
  )
}

function Message({ message, onOpenSources, onFeedback, isStreamingTail }) {
  const [feedback, setFeedback] = useState(null)
  if (message.role === 'user') {
    return <div className="msg user"><div className="bubble">{message.content}</div></div>
  }
  const sources = message.sources || message.citations || []
  return (
    <div className="msg assistant">
      {message.trace && message.trace.length > 0 && <TraceBar trace={message.trace} />}
      <div className="bubble">
        {message.content ? (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        ) : (
          <span className="thinking">retrieving and reasoning…</span>
        )}
        {message.demo && <div className="demo-badge">demo mode (no LLM key)</div>}
      </div>
      {sources.length > 0 && (
        <div className="citation-row">
          <span className="citation-label">Sources:</span>
          {sources.map((c) => (
            <button key={c.index} className="chip" onClick={() => onOpenSources(sources)}>
              [{c.index}] {c.doc_title} · p{c.page}
            </button>
          ))}
        </div>
      )}
      {!isStreamingTail && message.content && (
        <div className="feedback">
          <button
            className={`icon-btn ${feedback === 1 ? 'good' : ''}`}
            onClick={() => {
              setFeedback(1)
              onFeedback?.(message.id, 1).catch(() => {})
            }}
            title="Good answer"
          >
            👍
          </button>
          <button
            className={`icon-btn ${feedback === -1 ? 'bad' : ''}`}
            onClick={() => {
              setFeedback(-1)
              onFeedback?.(message.id, -1).catch(() => {})
            }}
            title="Bad answer"
          >
            👎
          </button>
        </div>
      )}
    </div>
  )
}
