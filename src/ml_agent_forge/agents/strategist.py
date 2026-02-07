"""Strategist (ML Expert) agent: creates a step-by-step execution plan from context and data_profile."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.ml_agent_forge.state import GraphState


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-3-5-sonnet-latest", api_key=api_key, temperature=0)


def strategist_node(state: GraphState) -> dict:
    """Read user_input and data_profile; produce a step-by-step plan and set plan in state."""
    user_input = state.get("user_input") or {}
    data_profile = state.get("data_profile") or ""

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
    response = llm.invoke(messages)
    plan = response.content if hasattr(response, "content") else str(response)

    return {
        "plan": plan,
        "messages": (state.get("messages") or []) + [HumanMessage(content="Strategist produced the execution plan.")],
    }
