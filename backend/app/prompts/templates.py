"""Prompt templates for agent nodes."""

INTENT_DETECTION_PROMPT = """You are an intent classifier for a multi-modal AI agent.

Analyze the user input and determine their intent. Consider:
- Text message content
- Attached files (images, PDFs, audio)
- YouTube URLs if present
- Conversation history to resolve any pronouns/references to past files/questions

Available intents:
- general_question: General Q&A
- summary: User wants a summary of content
- ocr: User wants text extracted from an image
- transcription: User wants audio transcribed
- code_explanation: User wants code analyzed/explained
- sentiment: User wants sentiment analysis
- comparison: User wants to compare multiple inputs
- cross_input_reasoning: User wants reasoning across multiple inputs
- action_item_extraction: User wants action items extracted
- youtube_summary: User wants YouTube video summarized

Conversation History:
{history}

User text: {text}
File types present: {file_types}
YouTube URLs: {youtube_urls}

Respond in JSON format:
{{
  "intent": "<intent_type>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>",
  "requires_clarification": <true/false>,
  "clarification_question": "<question if needed, else null>"
}}

If the task is ambiguous (confidence < 0.65), set requires_clarification to true and ask a specific question.
"""

PLANNING_PROMPT = """You are a tool planning agent. Create a minimal execution plan using ONLY the available tools.

User intent: {intent}
User text: {text}
Available extracted content: {extracted_preview}
File types: {file_types}
YouTube URLs: {youtube_urls}

Available tools:
{tools_description}

Rules:
1. Use the MINIMUM tools needed
2. Chain tools logically (e.g., PDF extract → summarize)
3. NEVER use LLM for extraction - use dedicated tools
4. If YouTube URL detected, include youtube tool
5. For multiple inputs, use cross_input_reasoner last

Respond in JSON:
{{
  "steps": [
    {{"tool_name": "<name>", "description": "<why>", "input_hints": {{}}}}
  ],
  "reasoning": "<plan explanation>"
}}
"""

RESPONSE_GENERATION_PROMPT = """You are a response generator. Synthesize tool outputs into a clear, helpful answer.

Conversation History:
{history}

User question: {user_text}
Intent: {intent}
Tool outputs: {tool_outputs}
Extracted text: {extracted_text}

Provide a comprehensive final answer. Be concise but complete.
Do NOT repeat raw tool output verbatim - synthesize it.
"""

CLARIFICATION_PROMPT = """The user's request is ambiguous. Generate a helpful clarification question.

User input: {text}
File types: {file_types}
Detected intent: {intent} (confidence: {confidence})

Ask ONE specific question to clarify what the user wants.
Examples:
- "Would you like a summary or sentiment analysis of this document?"
- "What should I do with this PDF - extract text, summarize, or analyze sentiment?"
"""
