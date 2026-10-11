import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import SourcesDrawer from './components/SourcesDrawer.jsx'

export default function App() {
  const [sessions, setSessions] = useState([])
  const [documents, setDocuments] = useState([])
  const [stats, setStats] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [sources, setSources] = useState(null) // sources of the message open in the drawer
  const [error, setError] = useState(null)
  const streamRef = useRef(null)

  const refresh = useCallback(async () => {
    const [s, d, st] = await Promise.all([api.listSessions(), api.listDocuments(), api.getStats()])
    setSessions(s)
    setDocuments(d)
    setStats(st)
  }, [])

  useEffect(() => {
    refresh().catch((e) => setError(`Backend not reachable: ${e.message}`))
  }, [refresh])

  const openSession = useCallback(async (id) => {
    setActiveSession(id)
    setSources(null)
    const msgs = await api.listMessages(id)
    setMessages(msgs)
  }, [])

  const newChat = useCallback(() => {
    streamRef.current = null
    setActiveSession(null)
    setMessages([])
    setSources(null)
    setError(null)
  }, [])

  const clearCurrentChat = useCallback(async () => {
    if (streaming) return
    if (activeSession) {
      await api.deleteSession(activeSession).catch(() => {})
    }
    setActiveSession(null)
    setMessages([])
    setSources(null)
    setError(null)
    refresh().catch(() => {})
  }, [activeSession, streaming, refresh])

  const deleteSession = useCallback(async (id, e) => {
    e?.stopPropagation()
    await api.deleteSession(id).catch(() => {})
    if (activeSession === id) {
      setActiveSession(null)
      setMessages([])
      setSources(null)
    }
    refresh().catch(() => {})
  }, [activeSession, refresh])

  const clearAllHistory = useCallback(async () => {
    if (sessions.length === 0 && messages.length === 0) return
    if (!confirm('Are you sure you want to clear all chat history?')) return
    await api.clearAllSessions().catch(() => {})
    setActiveSession(null)
    setMessages([])
    setSources(null)
    refresh().catch(() => {})
  }, [sessions.length, messages.length, refresh])

  const send = useCallback(
    async (question) => {
      if (streaming) return
      setError(null)
      setStreaming(true)
      setSources(null)
      const controller = new AbortController()
      streamRef.current = controller
      const userMsg = { id: `local-u-${Date.now()}`, role: 'user', content: question }
      const botMsg = { id: `local-a-${Date.now()}`, role: 'assistant', content: '', citations: [], trace: [] }
      setMessages((m) => [...m, userMsg, botMsg])

      try {
        for await (const event of api.streamChat(question, activeSession, controller.signal)) {
          if (event.type === 'meta' && event.session_id) setActiveSession(event.session_id)
          else if (event.type === 'trace') setMessages((m) => replaceLast(m, { trace: event.trace }))
          else if (event.type === 'sources')
            setMessages((m) => replaceLast(m, { sources: event.sources }))
          else if (event.type === 'token')
            setMessages((m) => replaceLast(m, { content: (lastContent(m) + event.value) }))
          else if (event.type === 'done') {
            setMessages((m) =>
              replaceLast(m, { id: event.message_id, citations: event.citations, demo: event.demo })
            )
          } else if (event.type === 'error') setError(event.message)
        }
      } catch (e) {
        if (e.name === 'AbortError') {
          setMessages((m) =>
            lastContent(m).trim() ? m : replaceLast(m, { content: '_Stopped before any tokens arrived._' })
          )
        } else {
          setError(e.message)
        }
      } finally {
        streamRef.current = null
        setStreaming(false)
        refresh().catch(() => {})
      }
    },
    [activeSession, streaming, refresh]
  )

  const stop = useCallback(() => {
    streamRef.current?.abort()
  }, [])

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeSession={activeSession}
        onOpenSession={openSession}
        onNewChat={newChat}
        onDeleteSession={deleteSession}
        onClearAllHistory={clearAllHistory}
        documents={documents}
        stats={stats}
        onUpload={refresh}
      />
      <main className="main">
        <header className="topbar">
          <div className="brand-mini">
            <img src="/app_logo.png" className="app-logo mini" alt="PJ Logo" /> Company's Agent by PJ
          </div>
          <div className="topbar-actions">
            <div className="topbar-sub">
              {stats
                ? `${stats.documents} docs · ${stats.chunks} chunks · ${
                    stats.llm.model ? `${stats.llm.provider} (${stats.llm.model})` : 'demo mode - add GEMINI_API_KEY'
                  }`
                : 'connecting...'}
            </div>
            {(messages.length > 0 || activeSession) && (
              <button
                className="btn clear-chat-btn"
                onClick={clearCurrentChat}
                title="Clear current chat history"
              >
                <span className="btn-icon">🗑️</span> Clear Chat
              </button>
            )}
          </div>
        </header>
        {error && (
          <div className="error-banner" onClick={() => setError(null)}>
            {error} <span className="dismiss">✕</span>
          </div>
        )}
        <ChatWindow
          messages={messages}
          streaming={streaming}
          onSend={send}
          onStop={stop}
          onClear={clearCurrentChat}
          onOpenSources={(sources) => setSources(sources)}
          onFeedback={api.sendFeedback}
        />
      </main>
      {sources && <SourcesDrawer sources={sources} onClose={() => setSources(null)} />}
    </div>
  )
}

function lastContent(messages) {
  const last = messages[messages.length - 1]
  return last && last.role === 'assistant' ? last.content : ''
}

function replaceLast(messages, patch) {
  if (!messages.length) return messages
  const next = messages.slice()
  next[next.length - 1] = { ...next[next.length - 1], ...patch }
  return next
}
