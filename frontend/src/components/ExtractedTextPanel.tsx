import { useState } from 'react'
import { Copy, Check, FileSearch, ChevronDown, ChevronUp } from 'lucide-react'
import type { AgentResponse, UploadedFile } from '@/types'

interface ExtractedTextPanelProps {
  response?: AgentResponse | null
  activeFiles?: UploadedFile[]
}

export function ExtractedTextPanel({ response, activeFiles }: ExtractedTextPanelProps) {
  const [copied, setCopied] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const text = response?.extracted_text

  const filesLabel = activeFiles && activeFiles.length > 0
    ? ` (${activeFiles.map(f => f.filename).join(', ')})`
    : ''

  if (!text) {
    return (
      <div className="glass-card p-4 animate-fade-in">
        <div className="flex items-center gap-2 mb-2">
          <FileSearch className="h-4 w-4 text-muted-foreground/50" />
          <span className="text-sm font-semibold text-muted-foreground/70">Extracted Text</span>
        </div>
        <p className="text-xs text-muted-foreground/50 text-center py-3">
          Extracted content will appear here
        </p>
      </div>
    )
  }

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="glass-card p-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <FileSearch className="h-4 w-4 text-primary shrink-0" />
          <span className="text-sm font-semibold truncate max-w-[140px] xl:max-w-[200px]" title={`Extracted Text${filesLabel}`}>
            Extracted Text{filesLabel}
          </span>
          <span className="text-[10px] text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded-full shrink-0">
            {text.length.toLocaleString()} chars
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={copy}
            className="p-1.5 rounded-lg hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
            title="Copy text"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
          >
            {collapsed ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="relative">
          <pre className="text-[11px] leading-relaxed text-foreground/80 bg-secondary/20 rounded-lg p-3 overflow-auto max-h-48 font-mono whitespace-pre-wrap break-words border border-border/30">
            {text}
          </pre>
          {copied && (
            <div className="absolute top-2 right-2 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[10px] px-2 py-1 rounded-full">
              Copied!
            </div>
          )}
        </div>
      )}
    </div>
  )
}
