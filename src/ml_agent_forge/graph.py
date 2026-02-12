"""LangGraph assembly: Supervisor–Worker multi-agent pipeline for data analysis and ML."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.ml_agent_forge.state import GraphState
from src.ml_agent_forge.agents import (
    supervisor_node,
    detective_node,
    strategist_node,
    developer_node,
    reporter_node,
)


def _route_after_supervisor(state: GraphState) -> str:
    """Conditional edge: from Supervisor to the chosen worker or END."""
    next_agent = (state.get("next_agent") or "").strip()
    if next_agent == "FINISH":
        return END
    if next_agent in ("DataDetective", "Strategist", "Developer", "Reporter"):
        return next_agent
    # Fallback: end to avoid infinite loop
    return END


def build_graph(checkpointer=None):
    """Build the StateGraph and compile it.

    - Entry -> Supervisor.
    - Supervisor -> [DataDetective | Strategist | Developer | Reporter | END] via conditional edge.
    - Each worker -> Supervisor.
    - Reporter is the same worker that returns to Supervisor; Supervisor then sends FINISH -> END.

    Args:
        checkpointer: Optional checkpointer for persistence (e.g. MemorySaver()).

    Returns:
        Compiled graph (invocable).
    """
    builder = StateGraph(GraphState)

    builder.add_node("Supervisor", supervisor_node)
    builder.add_node("DataDetective", detective_node)
    builder.add_node("Strategist", strategist_node)
    builder.add_node("Developer", developer_node)
    builder.add_node("Reporter", reporter_node)

    builder.set_entry_point("Supervisor")
    builder.add_conditional_edges("Supervisor", _route_after_supervisor)

    builder.add_edge("DataDetective", "Supervisor")
    builder.add_edge("Strategist", "Supervisor")
    builder.add_edge("Developer", "Supervisor")
    builder.add_edge("Reporter", "Supervisor")

    return builder.compile(checkpointer=checkpointer)


def get_graph():
    """Return a compiled graph with in-memory checkpointer (for CLI use)."""
    return build_graph(checkpointer=MemorySaver())
