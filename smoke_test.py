"""Smoke-test least-privilege MCP tool functions (no stdio MCP client required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import server  # noqa: E402


def show(label: str, raw: str):
    data = json.loads(raw)
    status = "OK" if data.get("ok") else "DENY/ERR"
    print(f"[{status}] {label}")
    print(json.dumps(data, indent=2)[:800])
    print("-" * 40)


def main():
    show("orders list tools", server.list_my_tools("ORDERS_AGENT"))
    show("orders order_lookup", server.order_lookup("ORDERS_AGENT", customer_id="CUST-10291"))
    show("sales DENY transaction", server.transaction_lookup("SALES_AGENT", customer_id="CUST-10291"))
    show("payment txn", server.transaction_lookup("PAYMENT_CAPABILITY", order_id="ORD-DUP-1001"))
    show("policy active", server.policy_lookup("POLICY_RAG_AGENT", policy_id="PAYMENT-DUPLICATE-V2"))
    show("vector search", server.vector_search("KNOWLEDGE_AGENT", query="SoundBox rental MDR", top_k=2))
    show(
        "escalation create",
        server.escalation_create(
            "HUMAN_ESCALATION",
            customer_id="CUST-10291",
            issue="Possible duplicate payment",
            recommended_action="Human verify TXN-001/TXN-002 and approve refund of TXN-002",
            workflow_id="WF-DUP-1001",
            order_id="ORD-DUP-1001",
            policy_id="PAYMENT-DUPLICATE-V2",
            policy_version="v2.0",
            evidence_json='{"txns":["TXN-001","TXN-002"]}',
            agent_conclusion="Both txns success; needs HIL",
            priority="P1",
        ),
    )


if __name__ == "__main__":
    main()
