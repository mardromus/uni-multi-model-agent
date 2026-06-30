# Universal Multi-Modal Agent

An autonomous AI agent that accepts **text, images, PDFs, and audio** — individually or simultaneously — understands intent, plans the minimum viable tool chain, executes it autonomously, and returns synthesized text-only responses.

> **Live Demo**: Deploy using the instructions below.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🖼️ Image OCR | Extract text from images with confidence scores (EasyOCR) |
| 📄 PDF Parsing | Full-text extraction with scanned-page OCR fallback (PyMuPDF) |
| 🎙️ Audio Transcription | Speech-to-text with Whisper (async, non-blocking) |
| ▶️ YouTube Transcripts | Auto-detect YouTube URLs anywhere — even inside PDF content |
| 📝 Summarization | 1-line + 3 bullets + 5-sentence summaries |
| 💬 Sentiment Analysis | Label + confidence + justification |
| 💻 Code Analysis | Language detection + bug warnings + time complexity |
| 🧠 Cross-Input Reasoning | Combine audio + PDF + text for unified insights |
| ❓ Clarification Gate | Asks a single targeted question when intent is ambiguous |
| 💰 Cost Estimator | Token count + USD cost estimate per request |
| ⚡ SSE Streaming | Real-time tool execution events streamed to the frontend |

---

## Architecture

See [docs/architecture.md](./docs/architecture.md) for full Mermaid diagrams.

```
User Input (Text + Files)
        │
        ▼
┌─────────────────┐
│ Input Processor │  ← Extract YouTube URLs, resolve file paths
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intent Detector │  ← LLM + rule-based confidence scoring
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Clarify    Plan
(ask Q)     │
    │        ▼
    │  ┌──────────────┐
    │  │ Tool Executor│  ← Sequential + dynamic plan extension
    │  │              │     (discovers YouTube URLs in PDF output)
    │  └──────┬───────┘
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│ Output Formatter│  ← Synthesize answer + cost estimate
└────────┬────────┘
         │
         ▼
   React Frontend
   (SSE streaming)
```

### Tool Registry

| Tool | Trigger | Library |
|------|---------|---------|
| `ocr` | Image files | EasyOCR |
| `pdf_parser` | PDF files | PyMuPDF + OCR fallback |
| `audio_transcription` | Audio files | OpenAI Whisper (thread pool) |
| `youtube` | YouTube URLs (text or extracted content) | youtube-transcript-api |
| `summarizer` | Summary/action-item intent | Cerebras LLM |
| `sentiment` | Sentiment intent | Cerebras LLM |
| `code_analyzer` | Code intent | Cerebras LLM |
| `cross_input_reasoner` | Multiple files or comparison intent | Cerebras LLM |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [`uv`](https://github.com/astral-sh/uv) package manager
- FFmpeg (`brew install ffmpeg` / `apt install ffmpeg`)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd uni-multi-model-agent
```

### 2. Backend

```bash
cd backend

# Copy and fill in your API keys
cp .env.example .env  # or edit .env directly

# Install dependencies
uv pip install -e ".[dev]"

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CEREBRAS_API_KEY` | **Required** — Cerebras API key for LLM reasoning | — |
| `CEREBRAS_BASE_URL` | Cerebras API base URL | `https://api.cerebras.ai/v1` |
| `MODEL_NAME` | LLM model name | `gemma-4-31b` |
| `OPENAI_API_KEY` | Optional — OpenAI key (alternative LLM backend) | — |
| `OPENAI_BASE_URL` | OpenAI API base URL | `https://api.openai.com/v1` |
| `WHISPER_MODEL` | Whisper model size (`tiny`/`base`/`small`/`medium`) | `base` |
| `INTENT_CONFIDENCE_THRESHOLD` | Below this → ask clarification | `0.65` |
| `MAX_RETRIES` | Tool retry count on failure | `3` |
| `TOOL_TIMEOUT_SECONDS` | Max seconds per tool | `120` |
| `MAX_UPLOAD_SIZE_MB` | File upload limit | `50` |
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["http://localhost:5173"]` |
| `DEBUG` | Enable debug logging | `false` |

---

## Docker Deployment

### Docker Compose (local)

```bash
# Set your API key
export CEREBRAS_API_KEY=your-key-here

# Build and start
docker compose up --build

# Services:
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Render.com

1. Fork this repository.
2. Create a new Render service → connect your repo.
3. Render will use `render.yaml` automatically.
4. Set `CEREBRAS_API_KEY` in Render's environment variables dashboard.

> **Important**: The `render.yaml` deploys two services:
> - `universal-multimodal-agent-api` (backend FastAPI)
> - `universal-multimodal-agent-ui` (frontend nginx)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check + available tools |
| `GET` | `/api/v1/tools` | List all tools with schemas |
| `POST` | `/api/v1/upload` | Upload a file → returns `file_id` |
| `POST` | `/api/v1/chat` | Chat with history support |
| `POST` | `/api/v1/analyze` | Analyze with optional SSE streaming |
| `GET` | `/api/v1/trace/{id}` | Retrieve execution trace |

### Example: Chat Request

```json
POST /api/v1/chat
{
  "message": "What are the action items from this meeting?",
  "file_ids": ["abc-123-uploaded-pdf-id"],
  "conversation_history": [],
  "session_id": "optional-session-id"
}
```

### Example: Streaming Analyze

```json
POST /api/v1/analyze
{
  "message": "Summarize the YouTube video in this PDF",
  "file_ids": ["pdf-file-id"],
  "stream": true,
  "conversation_history": []
}
```

SSE events emitted: `start`, `input_processed`, `plan_step`, `tool_trace`, `complete`, `error`

---

## Test Cases

### Test Case 1 — Audio Transcription + Summary
```
Input: Upload audio file (.mp3/.wav) + "Transcribe and summarize this"
Expected: Agent runs audio_transcription → summarizer
Output: 1-line summary + 3 bullets + 5-sentence summary + duration
```

### Test Case 2 — PDF + Action Items Query
```
Input: Upload meeting notes PDF + "What are the action items?"
Expected: Agent runs pdf_parser → summarizer (action item mode)
Output: Extracted and filtered action items
```

### Test Case 3 — Image with Code
```
Input: Upload screenshot of code + "Explain this"
Expected: Agent runs ocr → code_analyzer
Output: Language detected + explanation + bugs + time complexity
```

### Test Case 4 — Cross-Input: PDF with YouTube URL (**Key Feature**)
```
Input: Upload PDF containing a YouTube URL + "Hit the YT URL and summarize it"
Expected: Agent runs pdf_parser → [discovers YT URL] → youtube → summarizer
  (No user prompting between steps)
Output: 1-line + 3-bullets + 5-sentence summary of the YouTube video
```

### Test Case 5 — Multi-File Unified Query
```
Input: Upload audio + PDF + "Do these discuss the same topic?"
Expected: Agent runs audio_transcription + pdf_parser → cross_input_reasoner
Output: Comparative analysis of both sources
```

---

## Testing

```bash
cd backend
pytest app/tests/ -v --tb=short
```

Tests cover all 5 assignment test cases via:
- Planning logic (tool chain verification)
- Intent detection (rule-based + edge cases)
- Tool error handling (missing files, invalid URLs)
- API endpoints (health, tools list)
- Cross-input reasoning (data flow)

---

## Project Structure

```
├── backend/
│   └── app/
│       ├── api/          # FastAPI routes & dependencies
│       ├── agents/       # AgentOrchestrator
│       ├── graph/        # LangGraph workflow, nodes, state
│       ├── tools/        # 8 independent tool classes
│       ├── services/     # LLM, file, trace, input services
│       ├── models/       # Pydantic domain models
│       ├── schemas/      # API request/response schemas
│       ├── prompts/      # LLM prompt templates
│       ├── config/       # Settings (pydantic-settings)
│       ├── utils/        # Helpers (YouTube URL regex, etc.)
│       └── tests/        # Pytest test suite
├── frontend/
│   └── src/
│       ├── components/   # React UI components
│       ├── lib/          # API client
│       └── types/        # TypeScript types
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/
│   └── architecture.md   # Architecture diagrams
├── docker-compose.yml
└── render.yaml           # Render.com deployment config
```

---

## Design Decisions

1. **LLM never extracts content** — OCR, PDF parsing, audio transcription, and YouTube fetching use dedicated deterministic tools. LLM only reasons and synthesizes.

2. **Dynamic plan extension** — After PDF/image extraction, the executor automatically scans output for YouTube URLs and inserts new steps into the live plan without user prompting (enabling Test Case 4).

3. **Async-safe Whisper** — `model.transcribe()` runs in a thread pool via `asyncio.run_in_executor` to avoid blocking the event loop.

4. **Clarification gate** — Below 0.65 confidence or when `requires_clarification=True`, the agent pauses and asks one targeted question before executing any tools.

5. **Cost estimator** — Every response includes `token_estimate` and `cost_estimate_usd` using tiktoken counts and configurable per-token pricing.

---

## License

MIT
