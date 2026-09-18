"""
Least-privilege tool allowlists for Autonomous AI OS MCP.
Every tool call must pass agent_id; MCP rejects unauthorized tools.
"""
from __future__ import annotations

from typing import Final

# Canonical agent IDs (orchestrator must pass one of these)
ORDERS_AGENT = "ORDERS_AGENT"
CUSTOMER_RAG_AGENT = "CUSTOMER_RAG_AGENT"
POLICY_RAG_AGENT = "POLICY_RAG_AGENT"
TECHNICAL_SUPPORT_AGENT = "TECHNICAL_SUPPORT_AGENT"
SALES_AGENT = "SALES_AGENT"
KNOWLEDGE_AGENT = "KNOWLEDGE_AGENT"
PAYMENT_CAPABILITY = "PAYMENT_CAPABILITY"
HUMAN_ESCALATION = "HUMAN_ESCALATION"
ORCHESTRATOR = "ORCHESTRATOR"
MONITORING_AGENT = "MONITORING_AGENT"

# Tool names exposed by this MCP server
TOOL_ORDER_LOOKUP = "order_lookup"
TOOL_ACCOUNT_LOOKUP = "account_lookup"
TOOL_CUSTOMER_MEMORY_READ = "customer_memory_read"
TOOL_CUSTOMER_INTERACTIONS_READ = "customer_interactions_read"
TOOL_TRANSACTION_LOOKUP = "transaction_lookup"
TOOL_POLICY_LOOKUP = "policy_lookup"
TOOL_VECTOR_SEARCH = "vector_search"
TOOL_RESOLVED_CASE_SEARCH = "resolved_case_search"
TOOL_DEVICE_LOOKUP = "device_lookup"
TOOL_WORKFLOW_LOOKUP = "workflow_lookup"
TOOL_ESCALATION_CREATE = "escalation_create"
TOOL_LIST_MY_TOOLS = "list_my_tools"

AGENT_PERMISSIONS: Final[dict[str, set[str]]] = {
    ORDERS_AGENT: {
        TOOL_ORDER_LOOKUP,
        TOOL_ACCOUNT_LOOKUP,
        TOOL_DEVICE_LOOKUP,
        TOOL_LIST_MY_TOOLS,
    },
    CUSTOMER_RAG_AGENT: {
        TOOL_CUSTOMER_MEMORY_READ,
        TOOL_CUSTOMER_INTERACTIONS_READ,
        TOOL_LIST_MY_TOOLS,
    },
    POLICY_RAG_AGENT: {
        TOOL_POLICY_LOOKUP,
        TOOL_VECTOR_SEARCH,
        TOOL_LIST_MY_TOOLS,
    },
    KNOWLEDGE_AGENT: {
        TOOL_VECTOR_SEARCH,
        TOOL_RESOLVED_CASE_SEARCH,
        TOOL_POLICY_LOOKUP,
        TOOL_LIST_MY_TOOLS,
    },
    TECHNICAL_SUPPORT_AGENT: {
        TOOL_CUSTOMER_MEMORY_READ,
        TOOL_DEVICE_LOOKUP,
        TOOL_VECTOR_SEARCH,
        TOOL_RESOLVED_CASE_SEARCH,
        TOOL_LIST_MY_TOOLS,
    },
    SALES_AGENT: {
        # Sales must NOT get payment/order DB tools by default
        TOOL_CUSTOMER_MEMORY_READ,
        TOOL_VECTOR_SEARCH,
        TOOL_LIST_MY_TOOLS,
    },
    PAYMENT_CAPABILITY: {
        TOOL_TRANSACTION_LOOKUP,
        TOOL_ORDER_LOOKUP,
        TOOL_LIST_MY_TOOLS,
    },
    HUMAN_ESCALATION: {
        TOOL_ESCALATION_CREATE,
        TOOL_WORKFLOW_LOOKUP,
        TOOL_CUSTOMER_MEMORY_READ,
        TOOL_LIST_MY_TOOLS,
    },
    ORCHESTRATOR: {
        # Coordinator may inspect state; still no unrestricted write/payment refunds
        TOOL_WORKFLOW_LOOKUP,
        TOOL_LIST_MY_TOOLS,
        TOOL_ESCALATION_CREATE,
    },
    MONITORING_AGENT: {
        TOOL_WORKFLOW_LOOKUP,
        TOOL_LIST_MY_TOOLS,
    },
}


class PermissionDenied(PermissionError):
    pass


def require_tool(agent_id: str, tool_name: str) -> None:
    agent = (agent_id or "").strip().upper()
    if not agent:
        raise PermissionDenied("agent_id is required for least-privilege MCP access")
    allowed = AGENT_PERMISSIONS.get(agent)
    if allowed is None:
        raise PermissionDenied(f"Unknown agent_id: {agent_id}")
    if tool_name not in allowed:
        raise PermissionDenied(
            f"Agent {agent} is not allowed to call tool '{tool_name}'. "
            f"Allowed: {sorted(allowed)}"
        )


def tools_for_agent(agent_id: str) -> list[str]:
    agent = (agent_id or "").strip().upper()
    return sorted(AGENT_PERMISSIONS.get(agent, set()))
