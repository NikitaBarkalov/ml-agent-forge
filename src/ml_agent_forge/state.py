"""Shared state definition for the Hierarchical Multi-Agent Graph."""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class GraphState(TypedDict, total=False):
    """State passed through the LangGraph workflow.

    Attributes:
        messages: Conversation history (LLM messages).
        user_input: Dict with business_context, task, file_paths.
        data_profile: Schema, head of CSV, or metadata of input files.
        plan: Step-by-step execution plan (e.g. cleaning, modeling).
        code_context: History of executed code snippets and their results.
        final_report: Markdown report answering the business question.
        next_agent: Router decision: DataDetective, Strategist, Developer, Reporter, FINISH.
    """

    messages: list[BaseMessage]
    user_input: dict[str, Any]
    data_profile: str
    plan: str
    code_context: list[dict[str, Any]]
    final_report: str
    next_agent: str
