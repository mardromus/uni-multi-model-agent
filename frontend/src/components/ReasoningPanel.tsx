import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentResponse } from '@/types'

interface ReasoningPanelProps {
  response?: AgentResponse | null
}

export function ReasoningPanel({ response }: ReasoningPanelProps) {
  const steps = response?.reasoning_steps || []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Reasoning Steps</CardTitle>
      </CardHeader>
      <CardContent>
        {steps.length > 0 ? (
          <ol className="space-y-2">
            {steps.map((step, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <span className="text-muted-foreground font-mono shrink-0">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">No reasoning steps yet.</p>
        )}
      </CardContent>
    </Card>
  )
}
