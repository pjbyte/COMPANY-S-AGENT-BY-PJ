// Thin API client. The chat call consumes a Server-Sent Events stream
// manually (fetch + ReadableStream) because EventSource cannot POST.

export async function fetchJSON(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function* streamChat(question, sessionId, signal) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      try {
        yield JSON.parse(line.slice(5).trim())
      } catch {
        // ignore malformed keepalive chunks
      }
    }
  }
}

export const listSessions = () => fetchJSON('/api/sessions')
export const listMessages = (id) => fetchJSON(`/api/sessions/${id}/messages`)
export const deleteSession = (id) => fetchJSON(`/api/sessions/${id}`, { method: 'DELETE' })
export const clearAllSessions = () => fetchJSON('/api/sessions', { method: 'DELETE' })
export const listDocuments = () => fetchJSON('/api/documents')
export const deleteDocument = (id) => fetchJSON(`/api/documents/${id}`, { method: 'DELETE' })
export const getStats = () => fetchJSON('/api/stats')
export const sendFeedback = (message_id, rating) =>
  fetchJSON('/api/feedback', { method: 'POST', body: JSON.stringify({ message_id, rating }) })

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/documents/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}
