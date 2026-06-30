"""LangGraph node implementations."""

import json
import logging
import time
from typing import Any

from app.config.settings import get_settings
from app.graph.state import AgentState
from app.models.domain import (
    ExecutionPlan,
    IntentResult,
    IntentType,
    PlanStep,
    ToolStatus,
    ToolTraceEntry,
)
from app.prompts.templates import (
    CLARIFICATION_PROMPT,
    INTENT_DETECTION_PROMPT,
    PLANNING_PROMPT,
    RESPONSE_GENERATION_PROMPT,
)
from app.services.llm_service import LLMService
from app.tools.base import ToolRegistry
from app.utils.helpers import extract_youtube_urls

logger = logging.getLogger(__name__)


async def input_parser_node(state: AgentState) -> dict[str, Any]:
    """Parse and validate inputs."""
    processed = state.get("processed_input")
    if not processed:
        return {"error": "No processed input available"}

    extracted: list[str] = []
    if processed.text:
        extracted.append(processed.text)

    # Re-extract historical text blocks if present to support follow-ups
    history = state.get("conversation_history") or []
    for msg in history:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if "[Extracted Text/Content:\n" in content:
                try:
                    start_marker = "[Extracted Text/Content:\n"
                    end_marker = "\n]"
                    start_idx = content.find(start_marker) + len(start_marker)
                    end_idx = content.find(end_marker, start_idx)
                    if start_idx != -1 and end_idx != -1:
                        historical_extracted = content[start_idx:end_idx].strip()
                        if historical_extracted and historical_extracted not in extracted:
                            extracted.append(historical_extracted)
                except Exception as e:
                    logger.warning("Failed parsing historical extracted text: %s", e)

    return {
        "extracted_texts": extracted,
        "reasoning_steps": ["Input parsed and normalized"],
        "start_time_ms": time.time() * 1000,
    }


def _format_conversation_history(history_list: list[dict[str, str]]) -> str:
    """Format history list into a clean string, replacing bulky extracted text blocks with summary tags."""
    history_str = ""
    for msg in history_list:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if "[Extracted Text/Content:\n" in content:
            content_clean = content
            try:
                start_marker = "[Extracted Text/Content:\n"
                end_marker = "\n]"
                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker, start_idx + len(start_marker))
                if start_idx != -1 and end_idx != -1:
                    content_clean = (
                        content[:start_idx]
                        + "[Extracted Document Content]"
                        + content[end_idx + len(end_marker):]
                    )
            except Exception:
                pass
            history_str += f"{role.capitalize()}: {content_clean.strip()}\n"
        else:
            history_str += f"{role.capitalize()}: {content.strip()}\n"
    return history_str


async def intent_detector_node(state: AgentState) -> dict[str, Any]:
    """Detect user intent with confidence scoring."""
    processed = state["processed_input"]
    settings = get_settings()
    llm = LLMService(settings)

    # Rule-based intent hints
    intent = _rule_based_intent(processed)

    # Format history for classifier
    history_str = _format_conversation_history(state.get("conversation_history") or [])

    if llm.is_configured:
        try:
            prompt = INTENT_DETECTION_PROMPT.format(
                history=history_str or "None",
                text=processed.text or "",
                file_types=", ".join(processed.file_types) or "none",
                youtube_urls=", ".join(processed.youtube_urls) or "none",
            )
            result = await llm.invoke_json(
                "You classify user intent. Output valid JSON only.",
                prompt,
            )
            intent = IntentResult(
                intent=IntentType(result.get("intent", intent.intent.value)),
                confidence=float(result.get("confidence", intent.confidence)),
                reasoning=result.get("reasoning", ""),
                requires_clarification=result.get("requires_clarification", False),
                clarification_question=result.get("clarification_question"),
            )
        except Exception as e:
            logger.warning("LLM intent detection failed, using rules: %s", e)

    needs_clarification = (
        intent.confidence < settings.intent_confidence_threshold
        or intent.requires_clarification
    )

    if needs_clarification and not intent.clarification_question:
        intent.clarification_question = _generate_clarification(processed, intent)

    return {
        "intent_result": intent,
        "needs_clarification": needs_clarification,
        "clarification_question": intent.clarification_question,
        "reasoning_steps": state.get("reasoning_steps", [])
        + [f"Intent detected: {intent.intent.value} (confidence: {intent.confidence:.2f})"],
    }


def _rule_based_intent(processed) -> IntentResult:
    """Fallback rule-based intent detection."""
    text = (processed.text or "").lower()
    file_types = processed.file_types

    if processed.youtube_urls or "youtube" in text or "youtu.be" in text:
        return IntentResult(
            intent=IntentType.YOUTUBE_SUMMARY,
            confidence=0.85,
            reasoning="YouTube URL detected",
        )
    if "sentiment" in text or "how do you feel" in text:
        return IntentResult(
            intent=IntentType.SENTIMENT, confidence=0.9, reasoning="Sentiment keyword"
        )
    if any(kw in text for kw in ["summarize", "summary", "summarise", "tldr", "tl;dr", "key points"]):
        return IntentResult(
            intent=IntentType.SUMMARY, confidence=0.85, reasoning="Summary keyword"
        )
    if any(kw in text for kw in ["code", "function", "bug", "debug", "explain this", "what does this code"]):
        return IntentResult(
            intent=IntentType.CODE_EXPLANATION, confidence=0.8, reasoning="Code keyword"
        )
    if "compare" in text or "same topic" in text or "discuss the same" in text:
        return IntentResult(
            intent=IntentType.CROSS_INPUT_REASONING,
            confidence=0.8,
            reasoning="Comparison keyword",
        )
    if any(kw in text for kw in ["action item", "todo", "tasks", "action items", "next steps"]):
        return IntentResult(
            intent=IntentType.ACTION_ITEM_EXTRACTION,
            confidence=0.85,
            reasoning="Action items keyword",
        )
    if "transcribe" in text or "transcript" in text or "audio" in text:
        return IntentResult(
            intent=IntentType.TRANSCRIPTION, confidence=0.85, reasoning="Transcription keyword"
        )
    if "audio" in file_types or "transcribe" in text:
        return IntentResult(
            intent=IntentType.TRANSCRIPTION, confidence=0.85, reasoning="Audio input"
        )
    if "image" in file_types or "ocr" in text or "extract text" in text or ("explain" in text and "image" in file_types):
        return IntentResult(intent=IntentType.OCR, confidence=0.85, reasoning="Image/OCR input")
    if "pdf" in file_types:
        if any(kw in text for kw in ["summarize", "summary", "summarise"]):
            return IntentResult(
                intent=IntentType.SUMMARY, confidence=0.75, reasoning="PDF with summary intent"
            )
        if any(kw in text for kw in ["action item", "todo", "tasks"]):
            return IntentResult(
                intent=IntentType.ACTION_ITEM_EXTRACTION,
                confidence=0.85,
                reasoning="PDF with action items",
            )
        if text:
            # PDF + a question → cross-input reasoning
            return IntentResult(
                intent=IntentType.CROSS_INPUT_REASONING,
                confidence=0.7,
                reasoning="PDF with user query",
            )
        return IntentResult(
            intent=IntentType.SUMMARY,
            confidence=0.50,
            reasoning="PDF without clear intent - may need clarification",
            requires_clarification=True,
            clarification_question="What should I do with this PDF — extract text, summarize, analyze sentiment, or answer a specific question?",
        )
    if not text and not file_types:
        return IntentResult(
            intent=IntentType.GENERAL_QUESTION,
            confidence=0.3,
            reasoning="Empty input",
            requires_clarification=True,
            clarification_question="How can I help you? Please provide text, an image, PDF, or audio file.",
        )

    # Multiple files → cross input reasoning
    if len(file_types) > 1:
        return IntentResult(
            intent=IntentType.CROSS_INPUT_REASONING,
            confidence=0.75,
            reasoning="Multiple files detected",
        )

    return IntentResult(
        intent=IntentType.GENERAL_QUESTION,
        confidence=0.7,
        reasoning="Default general question",
    )


def _generate_clarification(processed, intent: IntentResult) -> str:
    if "pdf" in processed.file_types:
        return "What should I do with this PDF — extract text, summarize, find action items, or answer a specific question?"
    if len(processed.file_types) > 1:
        return "Would you like a summary, comparison, or cross-input analysis of these files?"
    if not processed.text and not processed.file_types:
        return "How can I help you today?"
    return "Would you like me to summarize, analyze sentiment, or answer a question about this content?"


async def clarification_node(state: AgentState) -> dict[str, Any]:
    """Return clarification question without executing tools."""
    question = state.get("clarification_question") or "Could you please clarify your request?"
    return {
        "final_answer": question,
        "needs_clarification": True,
        "reasoning_steps": state.get("reasoning_steps", []) + ["Clarification required"],
    }


async def planning_node(state: AgentState) -> dict[str, Any]:
    """Create minimal tool execution plan."""
    processed = state["processed_input"]
    intent = state["intent_result"]
    registry = state.get("_tool_registry")  # injected at runtime

    if registry is None:
        from app.tools.base import get_tool_registry

        registry = get_tool_registry()

    steps = _build_plan(processed, intent, registry, state.get("extracted_texts", []))
    plan = ExecutionPlan(steps=steps)

    return {
        "execution_plan": plan,
        "plan_steps": steps,
        "reasoning_steps": state.get("reasoning_steps", [])
        + [f"Plan created with {len(steps)} steps"],
    }


def _build_plan(
    processed,
    intent: IntentResult,
    registry: ToolRegistry,
    extracted_texts: list[str] | None = None,
) -> list[PlanStep]:
    """Build execution plan based on intent and inputs."""
    steps: list[PlanStep] = []
    step_num = 1
    text = processed.text or ""
    has_audio = "audio" in processed.file_types
    has_image = "image" in processed.file_types
    has_pdf = "pdf" in processed.file_types
    multi_file = len(processed.file_paths) > 1

    # Check if there is historical extracted content (excluding current user query)
    user_text = processed.text or ""
    has_historical_extracted = False
    if extracted_texts:
        actual_texts = [t for t in extracted_texts if t != user_text]
        if actual_texts:
            has_historical_extracted = True

    has_extracted = (
        has_pdf
        or has_image
        or has_audio
        or processed.youtube_urls
        or has_historical_extracted
    )

    # --- File extraction steps ---
    for i, (path, ftype) in enumerate(zip(processed.file_paths, processed.file_types)):
        if ftype == "image":
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="ocr",
                    description=f"Extract text from image {i + 1}",
                    input_data={"file_path": path},
                )
            )
            step_num += 1
        elif ftype == "pdf":
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="pdf_parser",
                    description=f"Parse PDF document {i + 1}",
                    input_data={"file_path": path},
                )
            )
            step_num += 1
        elif ftype == "audio":
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="audio_transcription",
                    description=f"Transcribe audio file {i + 1}",
                    input_data={"file_path": path},
                )
            )
            step_num += 1

    # --- YouTube steps (from user text) ---
    for url in processed.youtube_urls:
        steps.append(
            PlanStep(
                step_number=step_num,
                tool_name="youtube",
                description=f"Fetch YouTube transcript for {url}",
                input_data={"url": url},
            )
        )
        step_num += 1

    # --- NOTE: YouTube URLs hidden inside PDF content will be discovered
    # dynamically in tool_executor_node after PDF is parsed ---

    # --- Intent-based downstream steps ---

    if intent.intent == IntentType.CODE_EXPLANATION:
        # For image with code: OCR already in steps; code_analyzer uses extracted text
        code = _extract_code_block(text) or text if not has_extracted else "{{extracted_text}}"
        steps.append(
            PlanStep(
                step_number=step_num,
                tool_name="code_analyzer",
                description="Analyze code (language, bugs, complexity)",
                input_data={"code": code},
            )
        )
        step_num += 1

    elif intent.intent == IntentType.SENTIMENT:
        target_text = "{{extracted_text}}" if has_extracted else text
        steps.append(
            PlanStep(
                step_number=step_num,
                tool_name="sentiment",
                description="Analyze sentiment of content",
                input_data={"text": target_text},
            )
        )
        step_num += 1

    elif intent.intent in (IntentType.SUMMARY, IntentType.ACTION_ITEM_EXTRACTION):
        target_text = "{{extracted_text}}" if has_extracted else text
        context = text if intent.intent == IntentType.ACTION_ITEM_EXTRACTION else ""
        steps.append(
            PlanStep(
                step_number=step_num,
                tool_name="summarizer",
                description=(
                    "Extract action items from content"
                    if intent.intent == IntentType.ACTION_ITEM_EXTRACTION
                    else "Generate structured summary"
                ),
                input_data={"text": target_text, "context": context},
            )
        )
        step_num += 1

    elif intent.intent == IntentType.YOUTUBE_SUMMARY:
        # YouTube steps already added above; chain summarizer
        if processed.youtube_urls:  # Direct YouTube URL in text
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="summarizer",
                    description="Summarize YouTube transcript",
                    input_data={"text": "{{extracted_text}}", "context": text},
                )
            )
            step_num += 1

    elif intent.intent == IntentType.TRANSCRIPTION:
        # Audio transcription already added; if user implies summary, add it
        if has_audio and any(kw in text.lower() for kw in ["summarize", "summary", "key points", "brief"]):
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="summarizer",
                    description="Summarize audio transcript",
                    input_data={"text": "{{extracted_text}}", "context": text},
                )
            )
            step_num += 1

    # Auto-chain summarizer after audio when intent is not pure transcription
    if has_audio and intent.intent not in (IntentType.TRANSCRIPTION, IntentType.SENTIMENT, IntentType.CODE_EXPLANATION):
        # Check if summarizer wasn't already added
        if not any(s.tool_name == "summarizer" for s in steps):
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="summarizer",
                    description="Summarize audio transcript",
                    input_data={"text": "{{extracted_text}}", "context": text},
                )
            )
            step_num += 1

    # Cross-input reasoning for multiple files or explicit comparison intents
    if (
        multi_file
        or intent.intent in (IntentType.COMPARISON, IntentType.CROSS_INPUT_REASONING)
        or (has_pdf and text and intent.intent == IntentType.CROSS_INPUT_REASONING)
    ):
        if not any(s.tool_name == "cross_input_reasoner" for s in steps):
            steps.append(
                PlanStep(
                    step_number=step_num,
                    tool_name="cross_input_reasoner",
                    description="Combine all inputs into unified answer",
                    input_data={
                        "user_question": text,
                        "tool_outputs": "{{tool_outputs}}",
                        "extracted_texts": "{{extracted_texts}}",
                    },
                )
            )
            step_num += 1

    # Fallback: general question with no files and no tool steps
    if not steps:
        if text:
            steps.append(
                PlanStep(
                    step_number=1,
                    tool_name="cross_input_reasoner",
                    description="Answer general question",
                    input_data={
                        "user_question": text,
                        "tool_outputs": [],
                        "extracted_texts": [text],
                    },
                )
            )
        else:
            steps.append(
                PlanStep(
                    step_number=1,
                    tool_name="cross_input_reasoner",
                    description="Process combined inputs",
                    input_data={
                        "user_question": "",
                        "tool_outputs": "{{tool_outputs}}",
                        "extracted_texts": "{{extracted_texts}}",
                    },
                )
            )

    return steps


def _extract_code_block(text: str) -> str | None:
    import re

    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else None


async def tool_executor_node(state: AgentState) -> dict[str, Any]:
    """Execute planned tools sequentially with dynamic YouTube URL discovery."""
    plan_steps = state.get("plan_steps", [])
    registry = state.get("_tool_registry")
    if registry is None:
        from app.tools.base import get_tool_registry

        registry = get_tool_registry()

    settings = get_settings()
    tool_outputs: list[dict] = list(state.get("tool_outputs", []))
    tool_trace: list[ToolTraceEntry] = list(state.get("tool_trace", []))
    extracted_texts: list[str] = list(state.get("extracted_texts", []))
    combined_text_parts: list[str] = []

    # Track YouTube URLs already scheduled to avoid duplicates
    scheduled_yt_urls: set[str] = set(
        step.input_data.get("url", "") for step in plan_steps if step.tool_name == "youtube"
    )

    # We may dynamically append steps during iteration, so use an index loop
    i = 0
    while i < len(plan_steps):
        step = plan_steps[i]
        step.status = ToolStatus.RUNNING
        start = time.time()

        try:
            processed = state.get("processed_input")
            user_text = processed.text if processed else ""
            input_data = _resolve_inputs(
                step.input_data,
                extracted_texts,
                tool_outputs,
                "\n\n".join(extracted_texts),
                user_text,
            )
            result = await _execute_with_retry(
                registry, step.tool_name, input_data, settings.max_retries
            )
            duration = (time.time() - start) * 1000

            step.status = ToolStatus.SUCCESS
            step.output_data = result
            step.duration_ms = duration

            # --- Collect extracted text (fixed: no duplicates in text_keys) ---
            for key in ["text", "transcript"]:
                if key in result and result[key]:
                    extracted_texts.append(result[key])
                    combined_text_parts.append(result[key])

            tool_outputs.append({"tool": step.tool_name, "output": result})
            tool_trace.append(
                ToolTraceEntry(
                    tool_name=step.tool_name,
                    status=ToolStatus.SUCCESS,
                    input_summary=str(step.input_data)[:200],
                    output_summary=_summarize_output(result),
                    duration_ms=duration,
                )
            )

            # --- DYNAMIC YOUTUBE URL DISCOVERY (Test Case 4) ---
            # After PDF/OCR extraction, scan the new text for YouTube URLs
            if step.tool_name in ("pdf_parser", "ocr"):
                new_extracted = result.get("text", "")
                if new_extracted:
                    found_urls = extract_youtube_urls(new_extracted)
                    for url in found_urls:
                        if url not in scheduled_yt_urls:
                            scheduled_yt_urls.add(url)
                            # Insert YouTube step immediately after current step
                            new_yt_step = PlanStep(
                                step_number=len(plan_steps) + 1,
                                tool_name="youtube",
                                description=f"Fetch YouTube transcript from URL found in extracted content: {url}",
                                input_data={"url": url},
                            )
                            plan_steps.insert(i + 1, new_yt_step)
                            logger.info(
                                "Dynamically added YouTube step for URL found in extracted content: %s",
                                url,
                            )
                            # Also insert a summarizer step after the YouTube step if not already planned
                            already_has_summarizer = any(
                                s.tool_name == "summarizer" for s in plan_steps[i + 2:]
                            )
                            if not already_has_summarizer:
                                summarizer_step = PlanStep(
                                    step_number=len(plan_steps) + 1,
                                    tool_name="summarizer",
                                    description="Summarize YouTube transcript",
                                    input_data={
                                        "text": "{{extracted_text}}",
                                        "context": state.get("processed_input", {}).text
                                        if hasattr(state.get("processed_input", {}), "text")
                                        else "",
                                    },
                                )
                                plan_steps.insert(i + 2, summarizer_step)

        except Exception as e:
            duration = (time.time() - start) * 1000
            step.status = ToolStatus.FAILED
            step.error = str(e)
            step.duration_ms = duration
            tool_trace.append(
                ToolTraceEntry(
                    tool_name=step.tool_name,
                    status=ToolStatus.FAILED,
                    input_summary=str(step.input_data)[:200],
                    duration_ms=duration,
                    error=str(e),
                )
            )
            logger.error("Tool %s failed: %s", step.tool_name, e)

        i += 1

    # Renumber steps for display consistency
    for idx, s in enumerate(plan_steps):
        s.step_number = idx + 1

    combined_text = "\n\n".join(combined_text_parts)

    return {
        "plan_steps": plan_steps,
        "tool_outputs": tool_outputs,
        "tool_trace": tool_trace,
        "extracted_texts": extracted_texts,
        "extracted_text": combined_text,
        "reasoning_steps": state.get("reasoning_steps", [])
        + [f"Executed {len(plan_steps)} tools"],
    }


def _resolve_inputs(
    input_data: dict,
    extracted_texts: list[str],
    tool_outputs: list,
    text: str = "",
    user_text: str = "",
) -> dict:
    """Resolve template placeholders in tool inputs."""
    resolved = {}

    # Filter out user text query from actual extracted content to prevent self-summarization
    actual_texts = [t for t in extracted_texts if t != user_text]
    if actual_texts:
        combined = "\n\n".join(actual_texts)
    else:
        combined = text or "\n\n".join(extracted_texts)

    for key, value in input_data.items():
        if value == "{{extracted_text}}":
            resolved[key] = combined
        elif value == "{{tool_outputs}}":
            resolved[key] = [o["output"] for o in tool_outputs]
        elif value == "{{extracted_texts}}":
            resolved[key] = actual_texts if actual_texts else extracted_texts
        else:
            resolved[key] = value
    return resolved


async def _execute_with_retry(registry, tool_name: str, input_data: dict, max_retries: int) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            return await registry.execute(tool_name, **input_data)
        except Exception as e:
            last_error = e
            logger.warning("Tool %s attempt %d failed: %s", tool_name, attempt + 1, e)
    raise RuntimeError(f"Tool {tool_name} failed after {max_retries} retries: {last_error}")


def _summarize_output(result: dict) -> str:
    for key in ["text", "transcript", "unified_answer", "one_line", "explanation"]:
        if key in result and result[key]:
            val = str(result[key])
            return val[:200] + ("..." if len(val) > 200 else "")
    return json.dumps(result)[:200]


async def output_formatter_node(state: AgentState) -> dict[str, Any]:
    """Format final response."""
    from app.models.domain import AgentResponse
    from app.utils.helpers import estimate_cost, estimate_tokens

    settings = get_settings()
    processed = state["processed_input"]
    intent = state.get("intent_result")
    start_time = state.get("start_time_ms", time.time() * 1000)
    execution_time = time.time() * 1000 - start_time

    if state.get("needs_clarification"):
        response = AgentResponse(
            final_answer=state.get("clarification_question", ""),
            needs_clarification=True,
            clarification_question=state.get("clarification_question"),
            reasoning_steps=state.get("reasoning_steps", []),
            execution_time_ms=execution_time,
        )
        return {"agent_response": response, "final_answer": response.final_answer}

    # Generate final answer
    final_answer = await _generate_final_answer(state, settings)
    extracted_text = state.get("extracted_text", "") or "\n\n".join(
        state.get("extracted_texts", [])
    )

    all_text = extracted_text + final_answer
    input_tokens = estimate_tokens(all_text)
    output_tokens = estimate_tokens(final_answer)
    cost = estimate_cost(
        input_tokens, output_tokens, settings.input_token_price, settings.output_token_price
    )

    plan = state.get("execution_plan")
    if plan and state.get("plan_steps"):
        plan.steps = state["plan_steps"]

    response = AgentResponse(
        extracted_text=extracted_text,
        final_answer=final_answer,
        reasoning_steps=state.get("reasoning_steps", []),
        tool_trace=state.get("tool_trace", []),
        execution_plan=plan,
        execution_time_ms=round(execution_time, 2),
        token_estimate=input_tokens + output_tokens,
        cost_estimate_usd=round(cost, 6),
    )

    return {
        "agent_response": response,
        "final_answer": final_answer,
        "extracted_text": extracted_text,
    }


async def _generate_final_answer(state: AgentState, settings) -> str:
    """Synthesize final answer from tool outputs."""
    tool_outputs = state.get("tool_outputs", [])
    extracted_texts = state.get("extracted_texts", [])
    processed = state["processed_input"]
    intent = state.get("intent_result")

    # Check cross_input_reasoner output first
    for output in tool_outputs:
        if "unified_answer" in output.get("output", {}):
            ans = output["output"]["unified_answer"]
            if ans and ans.strip():
                return ans

    llm = LLMService(settings)
    # Format history for response generation
    history_str = _format_conversation_history(state.get("conversation_history") or [])

    if llm.is_configured:
        try:
            prompt = RESPONSE_GENERATION_PROMPT.format(
                history=history_str or "None",
                user_text=processed.text or "",
                intent=intent.intent.value if intent else "general",
                tool_outputs=json.dumps(
                    [o["output"] for o in tool_outputs], indent=2, default=str
                )[:8000],
                extracted_text="\n".join(extracted_texts)[:4000],
            )
            return await llm.invoke("You generate helpful final answers.", prompt)
        except Exception as e:
            logger.warning("Response generation failed: %s", e)

    # Fallback formatting
    parts = []
    for output in tool_outputs:
        out = output["output"]
        if "one_line" in out:
            parts.append(f"**Summary:** {out['one_line']}")
            if out.get("three_bullets"):
                parts.append("**Key Points:**")
                for b in out["three_bullets"]:
                    parts.append(f"- {b}")
            if out.get("five_sentences"):
                parts.append(f"\n{out['five_sentences']}")
        elif "label" in out and "justification" in out:
            parts.append(f"**Sentiment:** {out['label']} (confidence: {out['confidence']:.0%})")
            parts.append(f"*{out.get('justification', '')}*")
        elif "explanation" in out:
            parts.append(f"**Language:** {out.get('language', 'unknown')}")
            parts.append(out["explanation"])
            if out.get("bugs"):
                parts.append("**Potential Bugs:**")
                for b in out["bugs"]:
                    parts.append(f"- {b}")
            if out.get("time_complexity"):
                parts.append(f"**Time Complexity:** {out['time_complexity']}")
        elif "transcript" in out and out["transcript"]:
            parts.append(f"**Transcript:** {out['transcript'][:2000]}")
        elif "text" in out and out["text"]:
            parts.append(out["text"][:2000])

    return "\n\n".join(parts) if parts else "I processed your request but couldn't generate a detailed answer."
