import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { cn, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentResponse, PlanStep } from '@/types'

interface ToolExecutionPanelProps {
  response?: AgentResponse | null
  liveSteps?: PlanStep[]
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-destructive" />
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />
  }
}

export function ToolExecutionPanel({ response, liveSteps }: ToolExecutionPanelProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const steps = liveSteps || response?.execution_plan?.steps || []
  const traces = response?.tool_trace || []

  if (steps.length === 0 && traces.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tool Execution</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No tools executed yet.</p>
        </CardContent>
      </Card>
    )
  }

  const toggle = (n: number) => setExpanded((p) => ({ ...p, [n]: !p[n] }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          Tool Execution
          {response?.execution_time_ms != null && (
            <span className="text-xs font-normal text-muted-foreground">
              {formatDuration(response.execution_time_ms)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {steps.map((step) => (
          <div key={step.step_number} className="border rounded-md">
            <button
              className="w-full flex items-center gap-2 p-3 text-left hover:bg-muted/50"
              onClick={() => toggle(step.step_number)}
            >
              {expanded[step.step_number] ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <StatusIcon status={step.status} />
              <span className="text-sm font-medium">
                Step {step.step_number}: {step.tool_name}
              </span>
              {step.duration_ms != null && step.duration_ms > 0 && (
                <span className="text-xs text-muted-foreground ml-auto">
                  {formatDuration(step.duration_ms)}
                </span>
              )}
            </button>
            {expanded[step.step_number] && (
              <div className="px-3 pb-3 space-y-2 text-sm">
                <p className="text-muted-foreground">{step.description}</p>
                {step.error && <p className="text-destructive">{step.error}</p>}
                {step.output_data && Object.keys(step.output_data).length > 0 && (
                  <pre className="bg-muted p-2 rounded text-xs overflow-auto max-h-40">
                    {JSON.stringify(step.output_data, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        ))}

        {response?.token_estimate != null && response.token_estimate > 0 && (
          <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t">
            <span>Tokens: ~{response.token_estimate.toLocaleString()}</span>
            {response.cost_estimate_usd != null && (
              <span>Cost: ${response.cost_estimate_usd.toFixed(4)}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
