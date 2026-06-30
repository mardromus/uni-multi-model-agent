import { Brain, ChevronRight } from 'lucide-react'
import type { AgentResponse } from '@/types'

interface ReasoningPanelProps {
  response?: AgentResponse | null
}

export function ReasoningPanel({ response }: ReasoningPanelProps) {
  const steps = response?.reasoning_steps || []

  return (
    <div className="glass-card p-4 animate-fade-in">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold">Agent Reasoning</span>
        {steps.length > 0 && (
          <span className="text-[10px] text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded-full">
            {steps.length} steps
          </span>
        )}
      </div>

      {steps.length === 0 ? (
        <p className="text-xs text-muted-foreground/50 text-center py-3">
          Reasoning trace will appear here
        </p>
      ) : (
        <ol className="space-y-1.5">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-xs group">
              <span className="shrink-0 w-5 h-5 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-[9px] font-bold text-primary mt-0.5">
                {i + 1}
              </span>
              <div className="flex items-start gap-1 flex-1 min-w-0">
                <ChevronRight className="h-3 w-3 text-muted-foreground/40 mt-0.5 shrink-0" />
                <span className="text-foreground/70 leading-snug group-hover:text-foreground/90 transition-colors">
                  {step}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
