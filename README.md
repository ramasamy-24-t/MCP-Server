# Autonomous AI OS — MCP Server (least privilege)

Custom MCP tool boundary for Cosmos + Azure AI Search.  
**Human-in-the-loop (HIL) UI is yours** — `escalation_create` only stores the package.

## What you get

| Tool | Who can call it |
|---|---|
| `order_lookup`, `account_lookup`, `device_lookup` | `ORDERS_AGENT` |
| `customer_memory_read`, `customer_interactions_read` | `CUSTOMER_RAG_AGENT` (+ some others) |
| `transaction_lookup` | `PAYMENT_CAPABILITY` only (not Sales) |
| `policy_lookup`, `vector_search` | Policy / Knowledge agents |
| `resolved_case_search` | Knowledge / Tech support |
| `escalation_create` | `HUMAN_ESCALATION` / Orchestrator |
| `list_my_tools` | Every known agent |

Every tool requires **`agent_id`**. Unknown or unauthorized → `permission_denied`.

## Run locally (stdio MCP)

From repo root (uses root `.env`):

```bash
cd mcp-server
pip install -r requirements.txt
python smoke_test.py
python server.py
```

Or with MCP CLI:

```bash
mcp run server.py
```

### Cursor MCP config example

```json
{
  "mcpServers": {
    "aios-mcp": {
      "command": "python",
      "args": ["D:/Projects/sales & service/mcp-server/server.py"],
      "env": {}
    }
  }
}
```

(Ensure `.env` is loadable from repo root — `azure_clients.py` already loads it.)

## Deploy to Azure (Foundry registration)

See **[DEPLOY_AZURE.md](./DEPLOY_AZURE.md)** for App Service + Foundry steps.

Short version:
1. Create Linux App Service (Python 3.11) in an allowed region  
2. Put `.env` values into App Settings + `MCP_TRANSPORT=streamable-http`  
3. Startup: `python -m uvicorn server:mcp_http_app --host 0.0.0.0 --port 8000`  
4. Deploy `mcp-server/` code  
5. Foundry → Tools → MCP → paste remote URL  

Official guides:
- https://learn.microsoft.com/en-us/azure/foundry/mcp/build-your-own-mcp-server  
- https://learn.microsoft.com/en-us/azure/azure-functions/scenario-custom-remote-mcp-server  

## n8n usage

Orchestrator / agent nodes must pass `agent_id` on every tool call, e.g.:

- Orders agent → `agent_id=ORDERS_AGENT` + `order_lookup`  
- Sales agent → cannot call `transaction_lookup` (denied)

## HIL

`escalation_create` writes to Cosmos `escalations` with `humanCan: approve|reject|...`.  
You build the human console / n8n approval flow separately.

## Security note

Keys live in repo `.env` (gitignored). Prefer Key Vault + managed identity before production.
