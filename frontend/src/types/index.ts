export interface PlanStep {
  step_number: number
  tool_name: string
  description: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error?: string | null
  duration_ms?: number
}

export interface ToolTraceEntry {
  tool_name: string
  status: string
  input_summary?: string
  output_summary?: string
  duration_ms?: number
  error?: string | null
}

export interface ExecutionPlan {
  plan_id: string
  steps: PlanStep[]
}

export interface AgentResponse {
  response_id: string
  extracted_text: string
  final_answer: string
  reasoning_steps: string[]
  tool_trace: ToolTraceEntry[]
  execution_plan?: ExecutionPlan | null
  execution_time_ms: number
  clarification_question?: string | null
  token_estimate?: number
  cost_estimate_usd?: number
  needs_clarification?: boolean
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  files?: UploadedFile[]
  response?: AgentResponse
  isLoading?: boolean
}

export interface UploadedFile {
  file_id: string
  filename: string
  content_type: string
  size_bytes: number
}

export interface ToolInfo {
  name: string
  description: string
}
