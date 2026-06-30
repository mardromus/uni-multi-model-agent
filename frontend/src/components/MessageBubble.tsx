import ReactMarkdown from 'react-markdown'
import { Bot, User, AlertCircle, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isClarification = message.response?.needs_clarification

  return (
    <div className={cn('flex gap-3 group', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-transform group-hover:scale-105',
          isUser
            ? 'btn-gradient shadow-md'
            : isClarification
              ? 'bg-amber-500/20 border border-amber-500/30'
              : 'bg-secondary border border-border/50',
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : isClarification ? (
          <HelpCircle className="h-4 w-4 text-amber-400" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>

      {/* Content */}
      <div className={cn('flex flex-col gap-1.5 max-w-[80%]', isUser && 'items-end')}>
        {/* Bubble */}
        <div
          className={cn(
            'px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'bubble-user text-white'
              : isClarification
                ? 'rounded-2xl border border-amber-500/30 bg-amber-500/5 text-foreground'
                : 'bubble-assistant text-foreground',
          )}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-2 py-0.5">
              <div className="typing-dots flex gap-1.5 items-center">
                <span />
                <span />
                <span />
              </div>
              <span className="text-xs text-muted-foreground">Agent is thinking...</span>
            </div>
          ) : isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-secondary/60 prose-code:text-primary prose-headings:text-foreground">
              {isClarification && (
                <div className="flex items-center gap-1.5 mb-2 text-amber-400 text-xs font-medium">
                  <AlertCircle className="h-3.5 w-3.5" />
                  <span>Clarification needed</span>
                </div>
              )}
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* File attachments */}
        {message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.files.map((f) => {
              const icon = f.content_type.startsWith('image/')
                ? '🖼️'
                : f.content_type === 'application/pdf'
                  ? '📄'
                  : f.content_type.startsWith('audio/')
                    ? '🎙️'
                    : '📎'
              return (
                <span key={f.file_id} className="file-tag">
                  {icon} {f.filename}
                </span>
              )
            })}
          </div>
        )}

        {/* Cost + time metadata */}
        {message.response && !message.response.needs_clarification && (
          <div className="flex items-center gap-2 flex-wrap">
            {message.response.execution_time_ms > 0 && (
              <span className="text-[10px] text-muted-foreground">
                {(message.response.execution_time_ms / 1000).toFixed(1)}s
              </span>
            )}
            {message.response.cost_estimate_usd != null &&
              message.response.cost_estimate_usd > 0 && (
                <span className="cost-chip">
                  ~${message.response.cost_estimate_usd.toFixed(4)}
                </span>
              )}
          </div>
        )}

        <span className="text-[10px] text-muted-foreground/60">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
