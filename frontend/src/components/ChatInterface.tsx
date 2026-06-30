import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Moon, Sun, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { MessageBubble } from '@/components/MessageBubble'
import { FileUpload } from '@/components/FileUpload'
import { ToolExecutionPanel } from '@/components/ToolExecutionPanel'
import { ExtractedTextPanel } from '@/components/ExtractedTextPanel'
import { ReasoningPanel } from '@/components/ReasoningPanel'
import { analyzeStream } from '@/lib/api'
import type { AgentResponse, ChatMessage, PlanStep, UploadedFile } from '@/types'

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })
  const [lastResponse, setLastResponse] = useState<AgentResponse | null>(null)
  const [liveSteps, setLiveSteps] = useState<PlanStep[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(async () => {
    if (!input.trim() && files.length === 0) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      timestamp: new Date(),
      files: [...files],
    }

    const loadingMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setInput('')
    const currentFiles = [...files]
    setFiles([])
    setIsLoading(true)
    setLiveSteps([])

    try {
      let finalResponse: AgentResponse | null = null

      await analyzeStream(input, currentFiles.map((f) => f.file_id), (event) => {
        if (event.event === 'plan_step' && event.step) {
          setLiveSteps((prev) => {
            const step = event.step as PlanStep
            const existing = prev.findIndex((s) => s.step_number === step.step_number)
            if (existing >= 0) {
              const updated = [...prev]
              updated[existing] = step
              return updated
            }
            return [...prev, step]
          })
        }
        if (event.event === 'complete' && event.response) {
          finalResponse = event.response as AgentResponse
          if (event.session_id) setSessionId(event.session_id as string)
        }
      })

      if (finalResponse) {
        setLastResponse(finalResponse)
        setMessages((prev) =>
          prev.map((m) =>
            m.isLoading
              ? {
                  ...m,
                  isLoading: false,
                  content: finalResponse!.final_answer,
                  response: finalResponse!,
                }
              : m,
          ),
        )
      }
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.isLoading
            ? {
                ...m,
                isLoading: false,
                content: `Error: ${e instanceof Error ? e.message : 'Something went wrong'}`,
              }
            : m,
        ),
      )
    } finally {
      setIsLoading(false)
      setLiveSteps([])
    }
  }, [input, files])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    setMessages([])
    setLastResponse(null)
    setLiveSteps([])
    setSessionId(undefined)
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold">Universal Multi-Modal Agent</h1>
          <p className="text-xs text-muted-foreground">
            Text · Images · PDFs · Audio
            {sessionId && ` · Session: ${sessionId.slice(0, 8)}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={clearChat} title="Clear chat">
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDarkMode(!darkMode)}
            title="Toggle dark mode"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                <p className="text-lg font-medium mb-2">Welcome to the Multi-Modal Agent</p>
                <p className="text-sm max-w-md">
                  Upload images, PDFs, or audio files and ask questions. The agent will automatically
                  plan and execute the right tools for your task.
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="border-t p-4 space-y-3 shrink-0">
            <FileUpload files={files} onFilesChange={setFiles} disabled={isLoading} />
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question or describe what to do with your files..."
                className="min-h-[60px] resize-none"
                disabled={isLoading}
              />
              <Button onClick={handleSend} disabled={isLoading || (!input.trim() && files.length === 0)} size="icon" className="shrink-0">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Side panel */}
        <div className="hidden lg:flex w-80 xl:w-96 border-l flex-col gap-4 p-4 overflow-y-auto shrink-0">
          <ToolExecutionPanel response={lastResponse} liveSteps={liveSteps} />
          <ExtractedTextPanel response={lastResponse} />
          <ReasoningPanel response={lastResponse} />
        </div>
      </div>
    </div>
  )
}
