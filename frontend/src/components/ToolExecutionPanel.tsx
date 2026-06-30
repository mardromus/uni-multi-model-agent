import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Clock, Loader2, Zap, DollarSign } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { AgentResponse, PlanStep } from '@/types'

interface ToolExecutionPanelProps {
  response?: AgentResponse | null
  liveSteps?: PlanStep[]
}

const TOOL_COLORS: Record<string, string> = {
  ocr: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  pdf_parser: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
  audio_transcription: 'text-pink-400 bg-pink-400/10 border-pink-400/20',
  youtube: 'text-red-400 bg-red-400/10 border-red-400/20',
  summarizer: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  sentiment: 'text-violet-400 bg-violet-400/10 border-violet-400/20',
  code_analyzer: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
  cross_input_reasoner: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
}

const TOOL_EMOJIS: Record<string, string> = {
  ocr: '🔍',
  pdf_parser: '📄',
  audio_transcription: '🎙️',
  youtube: '▶️',
  summarizer: '📝',
  sentiment: '💬',
  code_analyzer: '💻',
  cross_input_reasoner: '🧠',
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
    case 'failed':
      return <XCircle className="h-3.5 w-3.5 text-red-400" />
    case 'running':
      return <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
    default:
      return <Clock className="h-3.5 w-3.5 text-muted-foreground/50" />
  }
}

function formatMs(ms: number | undefined) {
  if (!ms || ms === 0) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function ToolExecutionPanel({ response, liveSteps }: ToolExecutionPanelProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const steps = liveSteps && liveSteps.length > 0
    ? liveSteps
    : response?.execution_plan?.steps || []

  const toggle = (n: number) => setExpanded((p) => ({ ...p, [n]: !p[n] }))

  return (
    <div className="glass-card p-4 space-y-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">Tool Execution</span>
        </div>
        {response?.execution_time_ms != null && response.execution_time_ms > 0 && (
          <span className="text-xs text-muted-foreground">
            {(response.execution_time_ms / 1000).toFixed(2)}s total
          </span>
        )}
      </div>

      {steps.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-4 opacity-60">
          No tools executed yet — results will appear here
        </p>
      ) : (
        <div className="space-y-2">
          {steps.map((step, idx) => {
            const colorClass = TOOL_COLORS[step.tool_name] || 'text-muted-foreground bg-muted/20 border-border/20'
            const emoji = TOOL_EMOJIS[step.tool_name] || '🔧'
            const isExpanded = expanded[step.step_number]
            const duration = formatMs(step.duration_ms)

            return (
              <div
                key={`${step.step_number}-${step.tool_name}`}
                className={cn('tool-step overflow-hidden', step.status)}
              >
                {/* Step header */}
                <button
                  className="w-full flex items-center gap-2 p-2.5 text-left hover:bg-white/5 transition-colors"
                  onClick={() => toggle(step.step_number)}
                >
                  {/* Step number */}
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-muted/50 flex items-center justify-center text-[10px] font-bold text-muted-foreground">
                    {idx + 1}
                  </span>

                  {/* Status icon */}
                  <StatusIcon status={step.status} />

                  {/* Tool badge */}
                  <span className={cn(
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border shrink-0',
                    colorClass
                  )}>
                    {emoji} {step.tool_name}
                  </span>

                  {/* Description */}
                  <span className="text-xs text-muted-foreground truncate flex-1 text-left">
                    {step.description}
                  </span>

                  {/* Duration */}
                  {duration && (
                    <span className="text-[10px] text-muted-foreground/60 shrink-0">{duration}</span>
                  )}

                  {/* Expand toggle */}
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                  )}
                </button>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="px-3 pb-3 space-y-2 border-t border-border/30 pt-2">
                    {step.error && (
                      <p className="text-xs text-red-400 bg-red-400/10 rounded p-2">
                        ⚠️ {step.error}
                      </p>
                    )}
                    {step.output_data && Object.keys(step.output_data).length > 0 && (
                      <div>
                        <p className="text-[10px] text-muted-foreground mb-1 font-medium uppercase tracking-wide">Output</p>
                        <pre className="bg-secondary/30 rounded-lg p-2 text-[10px] overflow-auto max-h-32 font-mono text-foreground/80">
                          {JSON.stringify(step.output_data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Cost estimator */}
      {response?.token_estimate != null && response.token_estimate > 0 && (
        <div className="border-t border-border/30 pt-3 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <DollarSign className="h-3 w-3" />
              Cost Estimate
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              ~{response.token_estimate.toLocaleString()} tokens
            </span>
            {response.cost_estimate_usd != null && response.cost_estimate_usd > 0 && (
              <span className="cost-chip">
                ~${response.cost_estimate_usd.toFixed(5)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
