"""Multi-agent nodes for the Hierarchical Supervisor–Worker graph."""

from backend.agents.supervisor import supervisor_node
from backend.agents.detective import detective_node
from backend.agents.strategist import strategist_node
from backend.agents.developer import developer_node
from backend.agents.reporter import reporter_node

__all__ = [
    "supervisor_node",
    "detective_node",
    "strategist_node",
    "developer_node",
    "reporter_node",
]
