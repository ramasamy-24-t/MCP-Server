# Deploy aios-mcp on Railway (recommended for demos)

Azure keeps **data** (Cosmos, AI Search, OpenAI). Railway only hosts the **MCP HTTP process**.
Agents / Foundry still call your public MCP URL — architecture unchanged.

## Why Railway now

Azure App Service kept fighting ASGI (gunicorn vs uvicorn) and missing packages.
Railway: paste env vars → deploy folder → public URL in minutes.

## 1. Create project

1. https://railway.app → **New Project** → **Deploy from GitHub**  
   (or **Empty Project** → **Add service** → **Empty service**)
2. Root directory / watch path: **`mcp-server`**  
   (must contain `server.py`, `requirements.txt`, `Procfile`)

## 2. Environment variables

Service → **Variables** → paste from your local `.env` (same names):

```text
MCP_TRANSPORT=streamable-http
AZURE_COSMOS_ENDPOINT=
AZURE_COSMOS_KEY=
AZURE_COSMOS_DATABASE=ai_os
AZURE_COSMOS_CONTAINER_CUSTOMERS=customers
AZURE_COSMOS_CONTAINER_INTERACTIONS=interactions
AZURE_COSMOS_CONTAINER_ORDERS=orders
AZURE_COSMOS_CONTAINER_ACCOUNTS=accounts
AZURE_COSMOS_CONTAINER_DEVICES=devices
AZURE_COSMOS_CONTAINER_PAYMENTS=payments
AZURE_COSMOS_CONTAINER_PRODUCTS=products
AZURE_COSMOS_CONTAINER_POLICIES=policies
AZURE_COSMOS_CONTAINER_RESOLVED_CASES=resolved_cases
AZURE_COSMOS_CONTAINER_WORKFLOWS=workflows
AZURE_COSMOS_CONTAINER_AUDIT_EVENTS=audit_events
AZURE_COSMOS_CONTAINER_ESCALATIONS=escalations
AZURE_COSMOS_CONTAINER_SALES_LEADS=sales_leads
AZURE_COSMOS_CONTAINER_OUTCOME_METRICS=outcome_metrics
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_ADMIN_KEY=
AZURE_SEARCH_INDEX_NAME=knowledge-index
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

### Sales agent invoke (Orchestrator → n8n)

Optional; defaults to `agentos97` webhooks if unset:

```text
N8N_SALES_OUTREACH_URL=https://agentos97.app.n8n.cloud/webhook/sales-lead-intake
N8N_SALES_QUOTING_URL=https://agentos97.app.n8n.cloud/webhook/quoting-agent
N8N_SALES_ONBOARDING_URL=https://agentos97.app.n8n.cloud/webhook/onboarding-agent
N8N_SALES_INVOKE_TIMEOUT_SEC=120
```

Only `ORCHESTRATOR` may call `sales_outreach_invoke`, `sales_quoting_invoke`, `sales_onboarding_invoke`.

Railway sets `PORT` automatically — do not hardcode it.

## 3. Deploy

- GitHub: push → Railway auto-builds  
- Or CLI: `railway up` from `mcp-server/`

## 4. Public URL

Service → **Settings** → **Networking** → **Generate Domain**

Test:

```text
https://<your-app>.up.railway.app/mcp
```

Deploy logs should show uvicorn listening (not gunicorn).

## 5. Foundry / agents

Remote MCP endpoint = that Railway `/mcp` URL.  
Least-privilege matrix, Cosmos, Search — unchanged.

## Local smoke (optional)

```bash
cd mcp-server
set MCP_TRANSPORT=streamable-http
py server.py
```
