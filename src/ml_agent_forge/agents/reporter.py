"""Reporter agent: writes final markdown business report from code_context and user_input."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.ml_agent_forge.state import GraphState


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-3-5-sonnet-latest", api_key=api_key, temperature=0)


def reporter_node(state: GraphState) -> dict:
    """Read code_context and user_input; produce a comprehensive markdown report and set final_report."""
    user_input = state.get("user_input") or {}
    code_context = state.get("code_context") or []

    # Summarize code context for the LLM (avoid huge base64 in prompt)
    context_summary = []
    for i, ctx in enumerate(code_context):
        part = {
            "index": i + 1,
            "code": ctx.get("code"),
            "stdout": ctx.get("stdout"),
            "stderr": ctx.get("stderr"),
            "error": ctx.get("error"),
            "artifacts_count": len(ctx.get("artifacts") or []),
        }
        context_summary.append(part)

    prompt = f"""
You are a business analyst. Write a comprehensive markdown report that answers the user's business question.

Business context: {user_input.get("business_context", "")}
Concrete task: {user_input.get("task", "")}

Execution summary (code runs and outputs):
{context_summary}

Instructions:
- Structure the report with clear sections (Executive Summary, Findings, Methodology, Conclusions, Recommendations).
- Reference generated charts/artifacts where relevant (e.g. "See figure in artifacts" or describe what was plotted).
- Base conclusions on the stdout and results above. If any run had errors, note them and interpret what succeeded.
- Use markdown (headers, lists, bold) for readability.
Output only the report body, no preamble."""

    llm = _get_llm()
    messages = [
        SystemMessage(content="You output only the markdown report, no extra commentary."),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)
    final_report = response.content if hasattr(response, "content") else str(response)

    return {
        "final_report": final_report,
        "messages": (state.get("messages") or []) + [HumanMessage(content="Reporter produced the final report.")],
    }
