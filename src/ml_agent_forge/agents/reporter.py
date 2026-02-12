"""Reporter agent: writes final markdown business report from code_context and user_input."""

import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from structlog import get_logger

from src.ml_agent_forge.state import GraphState
from src.ml_agent_forge.utils.logger import truncate_for_log


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=api_key, temperature=0)


def reporter_node(state: GraphState) -> dict:
    """Read code_context and user_input; produce a comprehensive markdown report and set final_report."""
    user_input = state.get("user_input") or {}
    code_context = state.get("code_context") or []
    task = user_input.get("task", "")
    get_logger().info(
        "Agent started",
        agent="Reporter",
        task=task[:200] + "..." if len(task) > 200 else task,
        code_context_entries=len(code_context),
    )

    # Summarize code context for the LLM (avoid huge base64 in prompt)
    context_summary = []
    all_artifact_names = []
    for i, ctx in enumerate(code_context):
        run_artifacts = ctx.get("artifacts") or []
        art_names = [Path(a.get("path", "")).name for a in run_artifacts if a.get("path")]
        all_artifact_names.extend(art_names)
        
        part = {
            "index": i + 1,
            "code": ctx.get("code"),
            "stdout": ctx.get("stdout"),
            "stderr": ctx.get("stderr"),
            "error": ctx.get("error"),
            "artifacts_count": len(run_artifacts),
            "artifact_names": art_names,
        }
        context_summary.append(part)

    prompt = f"""
You are a business analyst. Write a comprehensive markdown report that answers the user's business question.

Business context: {user_input.get("business_context", "")}
Concrete task: {user_input.get("task", "")}

Execution summary (code runs and outputs):
{context_summary}

Available artifacts (images/charts) to embed:
{all_artifact_names}

Instructions:
- Structure the report with clear sections (Executive Summary, Findings, Methodology, Conclusions, Recommendations).
- **EMBED IMAGES**: Use standard markdown syntax `![Description](artifact_name.png)` to embed the available charts.
- Base conclusions on the stdout and results above. If any run had errors, note them and interpret what succeeded.
- Use markdown (headers, lists, bold) for readability.
Output only the report body, no preamble."""

    llm = _get_llm()
    messages = [
        SystemMessage(content="You output only the markdown report, no extra commentary."),
        HumanMessage(content=prompt),
    ]
    get_logger().debug(
        "LLM invoke (Reporter)",
        agent="Reporter",
        prompt_truncated=truncate_for_log(prompt, 800),
    )
    response = llm.invoke(messages)
    final_report = response.content if hasattr(response, "content") else str(response)
    get_logger().info(
        "LLM response (Reporter)",
        agent="Reporter",
        report_truncated=truncate_for_log(final_report, 500),
    )

    return {
        "final_report": final_report,
        "messages": (state.get("messages") or []) + [HumanMessage(content="Reporter produced the final report.")],
    }
