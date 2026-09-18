# Deploy aios-mcp to Azure (remote MCP)

> **Demo / tight deadline:** prefer [DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md).  
> Keep Cosmos / AI Search / OpenAI on Azure; host only the MCP HTTP process on Railway.

Your local server uses **stdio**. Azure needs **HTTP**. The app already supports:

```bash
set MCP_TRANSPORT=streamable-http
py server.py
```

Endpoint path is typically under the MCP streamable HTTP app (often `/mcp`).

---

## Recommended path: Azure App Service (Linux)

### 1. Create Web App (Student-allowed region)

Portal → **App Services** → Create:

| Setting | Value |
|---|---|
| Resource group | `Project-1` |
| Name | e.g. `app-aios-mcp-demo` (globally unique) |
| Publish | Code |
| Runtime | **Python 3.11** |
| OS | **Linux** |
| Region | one of your Policy allowed regions |
| Plan | Free F1 if available, else B1 |

### 2. Configure app settings (Configuration → Application settings)

Copy from your `.env` (same names):

- `AZURE_COSMOS_ENDPOINT`
- `AZURE_COSMOS_KEY`
- `AZURE_COSMOS_DATABASE=ai_os`
- all `AZURE_COSMOS_CONTAINER_*` you use
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_ADMIN_KEY`
- `AZURE_SEARCH_INDEX_NAME=knowledge-index`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION=2024-02-01`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large`
- `MCP_TRANSPORT=streamable-http`
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`

### 3. Startup command

**Configuration → General settings → Startup Command** — use this (installs deps if Oryx venv is missing):

```bash
bash startup.sh
```

Fallback (same behavior inline):

```bash
bash -c "cd /home/site/wwwroot && python -m pip install -r requirements.txt && python -m uvicorn server:app --host 0.0.0.0 --port 8000"
```

Do **not** leave Startup Command empty — Azure auto-detects Flask and runs **gunicorn sync**, which breaks this ASGI/Starlette MCP app.

### 4. Deploy code

From `mcp-server` folder (Azure CLI):

```bash
az webapp up --name app-aios-mcp-demo --resource-group Project-1 --runtime "PYTHON:3.11"
```

Or use **Deployment Center** → Local Git / ZIP deploy / VS Code Azure extension.

Deploy **contents of `mcp-server/`** (so `server.py` is at site root), and ensure parent `.env` values are in **App Settings** (do not rely on uploading `.env`).

### 5. Test

```text
https://app-aios-mcp-demo.azurewebsites.net/mcp
```

(Exact path depends on FastMCP mount; check App Service log stream if 404.)

### 6. Register in Azure AI Foundry

1. Foundry project → **Build** → **Tools** → **Add**  
2. **Custom** → **Model Context Protocol**  
3. **Remote MCP Server endpoint** = your App Service MCP URL  
4. Auth = key or Entra (add an API key header later for production)

Docs: https://learn.microsoft.com/en-us/azure/foundry/mcp/build-your-own-mcp-server

---

## Alternative: Azure Functions MCP template

Best when you want the official Foundry Functions webhook shape:

```bash
azd init --template remote-mcp-functions-python -e mcpserver-aios
```

Then port our tools from `server.py` into the Functions MCP handlers.  
Endpoint shape:

```text
https://<function-app>.azurewebsites.net/runtime/webhooks/mcp
```

Guide: https://learn.microsoft.com/en-us/azure/azure-functions/scenario-custom-remote-mcp-server

---

## What stays the same

- Least-privilege matrix (`permissions.py`)
- Cosmos + Search tools
- `agent_id` on every call
- HIL still outside MCP (`escalation_create` only stores the package)

## What changes

| Local | Azure |
|---|---|
| `MCP_TRANSPORT=stdio` (default) | `MCP_TRANSPORT=streamable-http` |
| `.env` file | App Settings |
| `py server.py` | App Service startup / uvicorn |
