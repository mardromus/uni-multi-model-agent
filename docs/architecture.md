# Architecture Documentation

See the main [README](../README.md) for the full architecture diagram and project overview.

## LangGraph Workflow

The agent uses a LangGraph state machine with the following nodes:

1. **Input Parser** — Normalizes text, files, and YouTube URLs
2. **Intent Detector** — Classifies intent with confidence scoring
3. **Clarification** — Returns follow-up question if confidence < threshold
4. **Planning** — Creates minimal tool execution plan
5. **Tool Executor** — Runs tools sequentially with retry logic
6. **Output Formatter** — Synthesizes final response with trace

## Clarification Logic

When intent confidence falls below `INTENT_CONFIDENCE_THRESHOLD` (default 0.65), the agent returns a clarification question and does not execute tools until the user responds.

Examples:
- PDF uploaded without clear intent → "What should I do with this PDF?"
- Ambiguous request → "Would you like a summary or sentiment analysis?"

## Multi-Tool Chains

The planner automatically chains tools:

```
PDF → Extract Text → Detect YouTube URL → Fetch Transcript → Summarize → Answer
```

No user intervention required between steps.

## Output Format

Every response includes:
- **Extracted Text** — Raw text from OCR/PDF/audio
- **Final Answer** — Synthesized response
- **Reasoning Steps** — Agent reasoning chain
- **Tool Trace** — Execution plan with status icons
- **Execution Time** — Total processing time
- **Token/Cost Estimates** — When LLM is used
