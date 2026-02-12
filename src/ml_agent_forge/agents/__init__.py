"""Multi-agent nodes for the Hierarchical Supervisor–Worker graph."""

from src.ml_agent_forge.agents.supervisor import supervisor_node
from src.ml_agent_forge.agents.detective import detective_node
from src.ml_agent_forge.agents.strategist import strategist_node
from src.ml_agent_forge.agents.developer import developer_node
from src.ml_agent_forge.agents.reporter import reporter_node

__all__ = [
    "supervisor_node",
    "detective_node",
    "strategist_node",
    "developer_node",
    "reporter_node",
]
