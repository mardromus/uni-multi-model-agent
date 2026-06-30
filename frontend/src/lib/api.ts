import type { AgentResponse, ToolInfo, UploadedFile } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse<UploadedFile>(response)
}

export async function sendChat(
  message: string,
  fileIds: string[],
  sessionId?: string,
): Promise<{ response: AgentResponse; session_id: string }> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      file_ids: fileIds,
      session_id: sessionId,
    }),
  })
  return handleResponse(response)
}

export async function analyzeStream(
  message: string,
  fileIds: string[],
  onEvent: (event: Record<string, unknown>) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      file_ids: fileIds,
      stream: true,
    }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  if (!response.body) throw new Error('No response body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          onEvent(event)
        } catch {
          // skip malformed events
        }
      }
    }
  }
}

export async function getTools(): Promise<ToolInfo[]> {
  const response = await fetch(`${API_BASE}/tools`)
  const data = await handleResponse<{ tools: ToolInfo[] }>(response)
  return data.tools
}

export async function healthCheck(): Promise<{ status: string; tools_available: string[] }> {
  const response = await fetch(`${API_BASE}/health`)
  return handleResponse(response)
}
