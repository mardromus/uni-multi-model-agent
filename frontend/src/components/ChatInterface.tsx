import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Moon, Sun, Trash2, Zap, Bot, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { MessageBubble } from '@/components/MessageBubble'
import { FileUpload } from '@/components/FileUpload'
import { ToolExecutionPanel } from '@/components/ToolExecutionPanel'
import { ExtractedTextPanel } from '@/components/ExtractedTextPanel'
import { ReasoningPanel } from '@/components/ReasoningPanel'
import { analyzeStream } from '@/lib/api'
import type { AgentResponse, ChatMessage, PlanStep, UploadedFile } from '@/types'

const CAPABILITY_CARDS = [
  { icon: '🖼️', title: 'Image OCR', desc: 'Extract text from any image with confidence scores' },
  { icon: '📄', title: 'PDF Analysis', desc: 'Parse documents, find action items, summarize' },
  { icon: '🎙️', title: 'Audio Transcription', desc: 'Convert speech to text with Whisper AI' },
  { icon: '▶️', title: 'YouTube Summary', desc: 'Fetch & summarize any YouTube video transcript' },
  { icon: '🔬', title: 'Code Analysis', desc: 'Explain code, detect bugs, measure complexity' },
  { icon: '🧠', title: 'Cross-Input Reasoning', desc: 'Combine multiple files for unified insights' },
]

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(true)
  const [lastResponse, setLastResponse] = useState<AgentResponse | null>(null)
  const [liveSteps, setLiveSteps] = useState<PlanStep[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [streamingContent, setStreamingContent] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    document.documentElement.classList.toggle('light', !darkMode)
  }, [darkMode])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      const scrollHeight = textarea.scrollHeight
      textarea.style.height = `${Math.min(Math.max(scrollHeight, 52), 160)}px`
    }
  }, [input])

  const getConversationHistory = useCallback(() => {
    return messages
      .filter((m) => !m.isLoading && (m.content || m.response?.extracted_text))
      .map((m) => {
        if (m.role === 'assistant') {
          let content = m.content || '';
          if (m.response?.extracted_text) {
            // Keep up to 10k characters to avoid blowing up context window
            const textToInclude = m.response.extracted_text.length > 10000
              ? m.response.extracted_text.slice(0, 10000) + '\n... [truncated]'
              : m.response.extracted_text;
            content = `[Extracted Text/Content:\n${textToInclude}\n]\n\n${content}`;
          }
          return { role: m.role, content };
        }
        return { role: m.role, content: m.content };
      })
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

    const loadingId = crypto.randomUUID()
    const loadingMessage: ChatMessage = {
      id: loadingId,
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
    setStreamingContent('')

    try {
      let finalResponse: AgentResponse | null = null
      const history = getConversationHistory()

      await analyzeStream(
        input,
        currentFiles.map((f) => f.file_id),
        (event) => {
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
          if (event.event === 'error') {
            console.error('Stream error:', event.message)
          }
        },
        history,
      )

      if (finalResponse) {
        setLastResponse(finalResponse)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingId
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
          m.id === loadingId
            ? {
                ...m,
                isLoading: false,
                content: `⚠️ Error: ${e instanceof Error ? e.message : 'Something went wrong'}`,
              }
            : m,
        ),
      )
    } finally {
      setIsLoading(false)
      setLiveSteps([])
    }
  }, [input, files, getConversationHistory])

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

  // Find the last assistant message that had extracted text or tool trace to keep panels persistently populated
  const lastActiveMsg = [...messages]
    .reverse()
    .find(
      (m) =>
        m.role === 'assistant' &&
        m.response &&
        (m.response.extracted_text ||
          m.response.tool_trace.length > 0 ||
          (m.response.execution_plan && m.response.execution_plan.steps.length > 0))
    );

  const lastActiveResponse = lastActiveMsg?.response || lastResponse;

  // Find the user message associated with this response to show active filenames in the header
  const lastActiveMsgIndex = lastActiveMsg
    ? messages.findIndex((m) => m.id === lastActiveMsg.id)
    : -1;
  const associatedUserMsg =
    lastActiveMsgIndex > 0 ? messages[lastActiveMsgIndex - 1] : null;
  const activeFiles = associatedUserMsg?.files || [];

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Header */}
      <header className="shrink-0 border-b border-border/50 px-4 py-3 flex items-center justify-between glass-card rounded-none" style={{borderRadius: 0}}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center btn-gradient shadow-lg">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight flex items-center gap-1.5">
              <span className="gradient-text">Universal Multi-Modal Agent</span>
            </h1>
            <p className="text-xs text-muted-foreground">
              Text · Images · PDFs · Audio · YouTube
              {sessionId && (
                <span className="ml-2 opacity-60">· Session {sessionId.slice(0, 8)}</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="icon"
            onClick={clearChat}
            title="Clear chat"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            disabled={isEmpty}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDarkMode(!darkMode)}
            title="Toggle theme"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {isEmpty ? (
              <WelcomeScreen />
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Live steps bar (shown while loading) */}
          {isLoading && liveSteps.length > 0 && (
            <div className="px-4 pb-2">
              <div className="glass-card px-3 py-2 flex items-center gap-2 flex-wrap">
                <Zap className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="text-xs text-muted-foreground">Running:</span>
                {liveSteps.map((s) => (
                  <span key={s.step_number} className={`status-badge ${s.status}`}>
                    {s.tool_name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Input area */}
          <div className="shrink-0 border-t border-border/50 p-4 space-y-3">
            <FileUpload files={files} onFilesChange={setFiles} disabled={isLoading} />
            <div className="flex gap-2 items-end glow-focus rounded-xl">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything — or upload files and let the agent decide..."
                className="min-h-[52px] max-h-[160px] resize-none rounded-xl border-border/60 bg-card/50 focus:bg-card/80 transition-colors text-sm"
                disabled={isLoading}
                rows={1}
              />
              <Button
                onClick={handleSend}
                disabled={isLoading || (!input.trim() && files.length === 0)}
                size="icon"
                className="shrink-0 h-[52px] w-12 rounded-xl btn-gradient disabled:opacity-40 disabled:transform-none"
              >
                {isLoading ? (
                  <div className="typing-dots flex gap-0.5">
                    <span /><span /><span />
                  </div>
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-[10px] text-muted-foreground text-center">
              Press <kbd className="px-1 py-0.5 rounded bg-muted text-xs font-mono">Enter</kbd> to send · <kbd className="px-1 py-0.5 rounded bg-muted text-xs font-mono">Shift+Enter</kbd> for newline
            </p>
          </div>
        </div>

        {/* Side panel */}
        <div className="hidden lg:flex w-80 xl:w-96 border-l border-border/50 flex-col gap-3 p-4 overflow-y-auto shrink-0 bg-card/20">
          <ToolExecutionPanel response={lastActiveResponse} liveSteps={liveSteps} />
          <ExtractedTextPanel response={lastActiveResponse} activeFiles={activeFiles} />
          <ReasoningPanel response={lastResponse} />
        </div>
      </div>
    </div>
  )
}

function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-8 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center btn-gradient shadow-2xl mb-5">
        <Bot className="h-8 w-8 text-white" />
      </div>
      <h2 className="text-2xl font-bold mb-2 gradient-text">Start a conversation</h2>
      <p className="text-muted-foreground text-sm max-w-sm mb-8">
        Upload images, PDFs, or audio files and ask questions. The agent automatically plans and executes the right tools for your task.
      </p>
      <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
        {CAPABILITY_CARDS.map((card) => (
          <div
            key={card.title}
            className="glass-card p-3 text-left hover:border-primary/40 transition-all duration-200 cursor-default group"
          >
            <div className="text-xl mb-1.5">{card.icon}</div>
            <div className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">{card.title}</div>
            <div className="text-[11px] text-muted-foreground mt-0.5 leading-snug">{card.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
