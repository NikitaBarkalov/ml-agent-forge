"""Supervisor (Router) agent: decides which worker runs next using structured output."""

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
# try:
#     from langchain_core.pydantic_v1 import BaseModel, Field
# except ImportError:
from pydantic import BaseModel, Field

from src.ml_agent_forge.state import GraphState


class SupervisorDecision(BaseModel):
    """Structured output for the supervisor's routing decision."""

    next_agent: Literal["DataDetective", "Strategist", "Developer", "Reporter", "FINISH"] = Field(
        description="The next agent to invoke, or FINISH to end the workflow."
    )
    reason: str = Field(description="Brief reason for this routing decision.")


def _get_llm():
    """Build ChatAnthropic LLM with model and API key from env."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(
        model="claude-3-5-sonnet-latest",
        api_key=api_key,
        temperature=0,
    )


def supervisor_node(state: GraphState) -> dict:
    """Route to the next worker based on current state.

    Routing logic:
    - If data_profile is empty -> DataDetective.
    - If plan is empty -> Strategist.
    - If plan exists but no code results -> Developer.
    - If analysis is done -> Reporter.
    - After Reporter or when done -> FINISH.
    """
    llm = _get_llm()
    structured_llm = llm.with_structured_output(SupervisorDecision)

    user_input = state.get("user_input") or {}
    data_profile = (state.get("data_profile") or "").strip()
    plan = (state.get("plan") or "").strip()
    code_context = state.get("code_context") or []
    final_report = (state.get("final_report") or "").strip()

    prompt = f"""
You are the Supervisor of a multi-agent data analysis and ML pipeline.

Current state:
- user_input: {user_input}
- data_profile (length {len(data_profile)} chars): {"(empty)" if not data_profile else "present"}
- plan (length {len(plan)} chars): {"(empty)" if not plan else "present"}
- code_context: {len(code_context)} entries (executed code + results)
- final_report (length {len(final_report)} chars): {"(empty)" if not final_report else "present"}

Routing rules (choose exactly one):
1. If data_profile is empty or missing -> choose DataDetective to analyze input files.
2. Else if plan is empty or missing -> choose Strategist to create an execution plan.
3. Else if plan exists but code_context is empty (no executed code yet) -> choose Developer to generate and run code.
4. Else if we have code results but no final_report -> choose Reporter to write the business report.
5. Else if final_report is already written -> choose FINISH to end.

Respond with next_agent and a short reason."""

    messages = [
        SystemMessage(content="You output only valid JSON-like structured decisions. Be deterministic."),
        HumanMessage(content=prompt),
    ]
    decision = structured_llm.invoke(messages)

    return {
        "next_agent": decision.next_agent,
        "messages": (state.get("messages") or []) + [HumanMessage(content=prompt)],
    }
