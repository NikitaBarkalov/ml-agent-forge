"""Strategist (ML Expert) agent: creates a step-by-step execution plan from context and data_profile."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from structlog import get_logger

from backend.state import GraphState
from backend.utils.logger import truncate_for_log


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=api_key, temperature=0)


def strategist_node(state: GraphState) -> dict:
    """Read user_input and data_profile; produce a step-by-step plan and set plan in state."""
    user_input = state.get("user_input") or {}
    data_profile = state.get("data_profile") or ""
    task = user_input.get("task", "")
    get_logger().info(
        "Agent started",
        agent="Strategist",
        task=task[:200] + "..." if len(task) > 200 else task,
        data_profile_len=len(data_profile),
    )

    llm = _get_llm()
    prompt = f"""
You are an ML/Data Strategy expert. Given the business context, task, and data profile below, output a clear step-by-step execution plan (e.g. 1. Load and clean data, 2. EDA, 3. Feature engineering, 4. Train model X, 5. Evaluate and save artifacts).

Business context: {user_input.get("business_context", "")}
Concrete task: {user_input.get("task", "")}
Data profile:
{data_profile}

Output only the plan as a single text block (numbered steps). No preamble."""

    messages = [
        SystemMessage(content="You output concise, actionable execution plans. Use numbered steps."),
        HumanMessage(content=prompt),
    ]
    get_logger().debug(
        "LLM invoke (Strategist)",
        agent="Strategist",
        prompt_truncated=truncate_for_log(prompt, 800),
    )
    response = llm.invoke(messages)
    plan = response.content if hasattr(response, "content") else str(response)
    get_logger().info(
        "LLM response (Strategist)",
        agent="Strategist",
        plan_truncated=truncate_for_log(plan, 500),
    )

    return {
        "plan": plan,
        "messages": (state.get("messages") or []) + [HumanMessage(content="Strategist produced the execution plan.")],
    }
