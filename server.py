"""
Autonomous AI OS — MCP Server (least privilege).

Every tool requires agent_id. Unauthorized tools are rejected and logged.
HIL (human approval UI) is intentionally out of scope — escalation_create
only builds/stores the escalation package for humans to handle.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from azure_clients import embed_query, query_items, search_client, container
from permissions import (
    TOOL_ACCOUNT_LOOKUP,
    TOOL_CUSTOMER_INTERACTIONS_READ,
    TOOL_CUSTOMER_MEMORY_READ,
    TOOL_DEVICE_LOOKUP,
    TOOL_ESCALATION_CREATE,
    TOOL_LIST_MY_TOOLS,
    TOOL_ORDER_LOOKUP,
    TOOL_POLICY_LOOKUP,
    TOOL_RESOLVED_CASE_SEARCH,
    TOOL_TRANSACTION_LOOKUP,
    TOOL_VECTOR_SEARCH,
    TOOL_WORKFLOW_LOOKUP,
    PermissionDenied,
    require_tool,
    tools_for_agent,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aios-mcp")

# FastMCP defaults to localhost-only Host checks → Railway/Azure get 421 Invalid Host header.
# Set MCP_ALLOWED_HOSTS (comma-separated) to re-enable protection for known public hosts.
_allowed_hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=bool(_allowed_hosts),
    allowed_hosts=_allowed_hosts,
)

mcp = FastMCP(
    "aios-mcp",
    instructions=(
        "Autonomous AI OS MCP boundary. Always pass agent_id on every tool call. "
        "Agents only receive tools allowed by the least-privilege matrix. "
        "Do not invent DB/tool results. Escalation creates a package for humans; "
        "it does not auto-approve high-risk actions."
    ),
    transport_security=_transport_security,
)

# Expose ASGI app for Azure App Service / uvicorn
# Alias `app` so Azure Oryx/gunicorn default `server:app` also works
mcp_http_app = mcp.streamable_http_app()
app = mcp_http_app


def _ok(data: Any) -> str:
    return json.dumps({"ok": True, "data": data}, default=str)


def _err(message: str, code: str = "error") -> str:
    return json.dumps({"ok": False, "error": {"code": code, "message": message}})


def _guard(agent_id: str, tool: str):
    try:
        require_tool(agent_id, tool)
        log.info("ALLOW agent=%s tool=%s", agent_id, tool)
    except PermissionDenied as e:
        log.warning("DENY agent=%s tool=%s reason=%s", agent_id, tool, e)
        raise


@mcp.tool(name=TOOL_LIST_MY_TOOLS, description="List tools this agent_id is allowed to call.")
def list_my_tools(agent_id: str) -> str:
    try:
        _guard(agent_id, TOOL_LIST_MY_TOOLS)
        return _ok({"agent_id": agent_id.upper(), "allowed_tools": tools_for_agent(agent_id)})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")


@mcp.tool(name=TOOL_ORDER_LOOKUP, description="Look up merchant orders by customerId and/or orderId.")
def order_lookup(agent_id: str, customer_id: str = "", order_id: str = "") -> str:
    try:
        _guard(agent_id, TOOL_ORDER_LOOKUP)
        if not customer_id and not order_id:
            return _err("Provide customer_id and/or order_id")
        if order_id and customer_id:
            q = "SELECT * FROM c WHERE c.customerId = @cid AND (c.orderId = @oid OR c.id = @oid)"
            params = [
                {"name": "@cid", "value": customer_id},
                {"name": "@oid", "value": order_id},
            ]
        elif order_id:
            q = "SELECT * FROM c WHERE c.orderId = @oid OR c.id = @oid"
            params = [{"name": "@oid", "value": order_id}]
        else:
            q = "SELECT * FROM c WHERE c.customerId = @cid"
            params = [{"name": "@cid", "value": customer_id}]
        rows = query_items("AZURE_COSMOS_CONTAINER_ORDERS", "orders", q, params)
        return _ok({"count": len(rows), "orders": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(name=TOOL_ACCOUNT_LOOKUP, description="Look up merchant account / MID by customerId or mid.")
def account_lookup(agent_id: str, customer_id: str = "", mid: str = "") -> str:
    try:
        _guard(agent_id, TOOL_ACCOUNT_LOOKUP)
        if not customer_id and not mid:
            return _err("Provide customer_id and/or mid")
        if customer_id and mid:
            q = "SELECT * FROM c WHERE c.customerId = @cid AND c.mid = @mid"
            params = [{"name": "@cid", "value": customer_id}, {"name": "@mid", "value": mid}]
        elif mid:
            q = "SELECT * FROM c WHERE c.mid = @mid"
            params = [{"name": "@mid", "value": mid}]
        else:
            q = "SELECT * FROM c WHERE c.customerId = @cid"
            params = [{"name": "@cid", "value": customer_id}]
        rows = query_items("AZURE_COSMOS_CONTAINER_ACCOUNTS", "accounts", q, params)
        return _ok({"count": len(rows), "accounts": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(name=TOOL_CUSTOMER_MEMORY_READ, description="Read customer/merchant profile memory by customerId.")
def customer_memory_read(agent_id: str, customer_id: str) -> str:
    try:
        _guard(agent_id, TOOL_CUSTOMER_MEMORY_READ)
        if not customer_id:
            return _err("customer_id is required")
        q = "SELECT * FROM c WHERE c.customerId = @cid"
        rows = query_items(
            "AZURE_COSMOS_CONTAINER_CUSTOMERS",
            "customers",
            q,
            [{"name": "@cid", "value": customer_id}],
        )
        return _ok({"count": len(rows), "customers": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_CUSTOMER_INTERACTIONS_READ,
    description="Read prior customer interactions by customerId.",
)
def customer_interactions_read(agent_id: str, customer_id: str, limit: int = 10) -> str:
    try:
        _guard(agent_id, TOOL_CUSTOMER_INTERACTIONS_READ)
        if not customer_id:
            return _err("customer_id is required")
        limit = max(1, min(int(limit or 10), 50))
        q = (
            "SELECT TOP @lim * FROM c WHERE c.customerId = @cid "
            "ORDER BY c.createdAt DESC"
        )
        # Cosmos SQL TOP with parameter can be picky; use literal safe int
        q = f"SELECT TOP {limit} * FROM c WHERE c.customerId = @cid ORDER BY c.createdAt DESC"
        rows = query_items(
            "AZURE_COSMOS_CONTAINER_INTERACTIONS",
            "interactions",
            q,
            [{"name": "@cid", "value": customer_id}],
        )
        return _ok({"count": len(rows), "interactions": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_TRANSACTION_LOOKUP,
    description="Look up payment transactions by customerId, orderId, or txnId.",
)
def transaction_lookup(
    agent_id: str,
    customer_id: str = "",
    order_id: str = "",
    txn_id: str = "",
) -> str:
    try:
        _guard(agent_id, TOOL_TRANSACTION_LOOKUP)
        clauses = []
        params = []
        if customer_id:
            clauses.append("c.customerId = @cid")
            params.append({"name": "@cid", "value": customer_id})
        if order_id:
            clauses.append("c.orderId = @oid")
            params.append({"name": "@oid", "value": order_id})
        if txn_id:
            clauses.append("(c.txnId = @tid OR c.id = @tid)")
            params.append({"name": "@tid", "value": txn_id})
        if not clauses:
            return _err("Provide customer_id, order_id, and/or txn_id")
        q = "SELECT * FROM c WHERE " + " AND ".join(clauses)
        rows = query_items("AZURE_COSMOS_CONTAINER_PAYMENTS", "payments", q, params)
        return _ok({"count": len(rows), "transactions": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_POLICY_LOOKUP,
    description="Look up policy registry records by policyId (Cosmos). Prefer active version.",
)
def policy_lookup(agent_id: str, policy_id: str = "", active_only: bool = True) -> str:
    try:
        _guard(agent_id, TOOL_POLICY_LOOKUP)
        if policy_id:
            q = "SELECT * FROM c WHERE c.policyId = @pid"
            params = [{"name": "@pid", "value": policy_id}]
            if active_only:
                q += " AND c.status = 'active'"
        else:
            q = "SELECT * FROM c WHERE c.status = 'active'" if active_only else "SELECT * FROM c"
            params = []
        rows = query_items("AZURE_COSMOS_CONTAINER_POLICIES", "policies", q, params)
        return _ok({"count": len(rows), "policies": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_VECTOR_SEARCH,
    description="Semantic search over Azure AI Search knowledge index (policies, FAQs, cases).",
)
def vector_search(agent_id: str, query: str, top_k: int = 5) -> str:
    try:
        _guard(agent_id, TOOL_VECTOR_SEARCH)
        if not query:
            return _err("query is required")
        top_k = max(1, min(int(top_k or 5), 20))
        vector = embed_query(query, dimensions=3072)
        results = search_client().search(
            search_text=None,
            vector_queries=[
                {
                    "kind": "vector",
                    "vector": vector,
                    "fields": "content_vector",
                    "k": top_k,
                }
            ],
            top=top_k,
        )
        hits = []
        for doc in results:
            hits.append(
                {
                    "score": doc.get("@search.score"),
                    "id": doc.get("id"),
                    "content": (doc.get("content") or "")[:1200],
                    "metadata": doc.get("metadata"),
                }
            )
        return _ok({"count": len(hits), "hits": hits})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_RESOLVED_CASE_SEARCH,
    description="Find similar resolved cases (examples only; current policy still wins).",
)
def resolved_case_search(agent_id: str, issue_type: str = "", query: str = "", limit: int = 5) -> str:
    try:
        _guard(agent_id, TOOL_RESOLVED_CASE_SEARCH)
        limit = max(1, min(int(limit or 5), 20))
        if issue_type:
            q = f"SELECT TOP {limit} * FROM c WHERE c.issueType = @it"
            rows = query_items(
                "AZURE_COSMOS_CONTAINER_RESOLVED_CASES",
                "resolved_cases",
                q,
                [{"name": "@it", "value": issue_type}],
            )
        elif query:
            # hybrid: vector search filtered conceptually by text; also cosmos scan
            vector_json = json.loads(vector_search(agent_id, query, top_k=limit))
            q = f"SELECT TOP {limit} * FROM c"
            rows = query_items("AZURE_COSMOS_CONTAINER_RESOLVED_CASES", "resolved_cases", q, [])
            return _ok(
                {
                    "note": "Historical cases are examples only. Apply current active policy.",
                    "cosmos_cases": rows,
                    "vector_hits": vector_json.get("data", {}).get("hits", []) if vector_json.get("ok") else [],
                }
            )
        else:
            q = f"SELECT TOP {limit} * FROM c"
            rows = query_items("AZURE_COSMOS_CONTAINER_RESOLVED_CASES", "resolved_cases", q, [])
        return _ok(
            {
                "note": "Historical cases are examples only. Apply current active policy.",
                "count": len(rows),
                "cases": rows,
            }
        )
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(name=TOOL_DEVICE_LOOKUP, description="Look up SoundBox/POS devices by customerId or tid.")
def device_lookup(agent_id: str, customer_id: str = "", tid: str = "") -> str:
    try:
        _guard(agent_id, TOOL_DEVICE_LOOKUP)
        if not customer_id and not tid:
            return _err("Provide customer_id and/or tid")
        if customer_id and tid:
            q = "SELECT * FROM c WHERE c.customerId = @cid AND c.tid = @tid"
            params = [{"name": "@cid", "value": customer_id}, {"name": "@tid", "value": tid}]
        elif tid:
            q = "SELECT * FROM c WHERE c.tid = @tid"
            params = [{"name": "@tid", "value": tid}]
        else:
            q = "SELECT * FROM c WHERE c.customerId = @cid"
            params = [{"name": "@cid", "value": customer_id}]
        rows = query_items("AZURE_COSMOS_CONTAINER_DEVICES", "devices", q, params)
        return _ok({"count": len(rows), "devices": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(name=TOOL_WORKFLOW_LOOKUP, description="Look up workflow state by workflowId or customerId.")
def workflow_lookup(agent_id: str, workflow_id: str = "", customer_id: str = "") -> str:
    try:
        _guard(agent_id, TOOL_WORKFLOW_LOOKUP)
        if not workflow_id and not customer_id:
            return _err("Provide workflow_id and/or customer_id")
        if workflow_id:
            q = "SELECT * FROM c WHERE c.workflowId = @wid OR c.id = @wid"
            params = [{"name": "@wid", "value": workflow_id}]
        else:
            q = "SELECT * FROM c WHERE c.customerId = @cid"
            params = [{"name": "@cid", "value": customer_id}]
        rows = query_items("AZURE_COSMOS_CONTAINER_WORKFLOWS", "workflows", q, params)
        return _ok({"count": len(rows), "workflows": rows})
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


@mcp.tool(
    name=TOOL_ESCALATION_CREATE,
    description=(
        "Create a human escalation package (HIL). Stores package in Cosmos escalations. "
        "Does NOT auto-resolve; humans handle approve/reject/takeover outside this tool."
    ),
)
def escalation_create(
    agent_id: str,
    customer_id: str,
    issue: str,
    recommended_action: str,
    workflow_id: str = "",
    order_id: str = "",
    policy_id: str = "",
    policy_version: str = "",
    evidence_json: str = "{}",
    agent_conclusion: str = "",
    priority: str = "P2",
) -> str:
    try:
        _guard(agent_id, TOOL_ESCALATION_CREATE)
        if not customer_id or not issue or not recommended_action:
            return _err("customer_id, issue, and recommended_action are required")
        try:
            evidence = json.loads(evidence_json) if evidence_json else {}
        except json.JSONDecodeError:
            evidence = {"raw": evidence_json}

        esc_id = f"ESC-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        doc = {
            "id": esc_id.lower(),
            "escalationId": esc_id,
            "customerId": customer_id,
            "workflowId": workflow_id or None,
            "issue": issue,
            "order": order_id or None,
            "evidence": evidence,
            "applicablePolicy": {"policyId": policy_id, "version": policy_version},
            "agentConclusion": agent_conclusion,
            "recommendedAction": recommended_action,
            "status": "open",
            "priority": priority,
            "assignedTo": "human_ops_queue",
            "humanCan": ["approve", "reject", "modify", "take_over", "resolve", "return_to_agent"],
            "createdByAgent": agent_id.upper(),
            "hilNote": "Human-in-the-loop required. MCP does not auto-approve.",
            "createdAt": now,
            "updatedAt": now,
        }
        container("AZURE_COSMOS_CONTAINER_ESCALATIONS", "escalations").upsert_item(doc)
        return _ok(
            {
                "message": "Escalation package created. Human must handle HIL outside MCP.",
                "escalation": doc,
            }
        )
    except PermissionDenied as e:
        return _err(str(e), "permission_denied")
    except Exception as e:
        return _err(str(e))


def main():
    # stdio = local Cursor; streamable-http/sse = remote MCP (Railway / Azure)
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        transport = "stdio"
    log.info("Starting aios-mcp transport=%s", transport)
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        # Bind all interfaces for Azure App Service / containers
        import uvicorn

        app = mcp.streamable_http_app() if transport == "streamable-http" else mcp.sse_app()
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("PORT") or os.getenv("MCP_PORT") or "8000")
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
