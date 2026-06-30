import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AgentResponse } from '@/types'

interface ExtractedTextPanelProps {
  response?: AgentResponse | null
}

export function ExtractedTextPanel({ response }: ExtractedTextPanelProps) {
  const text = response?.extracted_text

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Extracted Text</CardTitle>
      </CardHeader>
      <CardContent>
        {text ? (
          <pre className="text-sm whitespace-pre-wrap bg-muted p-3 rounded-md max-h-60 overflow-auto">
            {text}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">No extracted text yet.</p>
        )}
      </CardContent>
    </Card>
  )
}
