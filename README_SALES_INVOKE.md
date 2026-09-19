# Sales agents via MCP (Orchestrator invoke)

CS tools (Cosmos / Search) are unchanged. Sales teammates keep Gmail/Sheets on n8n.

## Tools (ORCHESTRATOR only)

| MCP tool | n8n webhook (default) |
|---|---|
| `sales_outreach_invoke` | `…/webhook/sales-lead-intake` |
| `sales_quoting_invoke` | `…/webhook/quoting-agent` |
| `sales_onboarding_invoke` | `…/webhook/onboarding-agent` |

Always pass `agent_id=ORCHESTRATOR`.

## Orchestrator routing (paste into agent instructions)

- New lead / outreach / follow-up → `sales_outreach_invoke`
- Interested lead needs quote or negotiation → `sales_quoting_invoke` with full context_json
- Agreement signed → `sales_onboarding_invoke` with signed terms + history
- Never skip stages; never let CS agents call these tools

## Env

See `env.sales.example`. Set the same vars on Railway after deploy.
