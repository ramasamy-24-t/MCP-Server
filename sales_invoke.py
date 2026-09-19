"""HTTP invoke helpers for Sales n8n agents (Outreach / Quoting / Onboarding).

CS Azure clients stay untouched. These calls forward work to existing n8n webhooks.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


DEFAULT_OUTREACH_URL = "https://agentos97.app.n8n.cloud/webhook/sales-lead-intake"
DEFAULT_QUOTING_URL = "https://agentos97.app.n8n.cloud/webhook/quoting-agent"
DEFAULT_ONBOARDING_URL = "https://agentos97.app.n8n.cloud/webhook/onboarding-agent"


def _url(env_name: str, default: str) -> str:
    return (os.getenv(env_name) or default).strip()


def invoke_sales_agent(
    *,
    env_name: str,
    default_url: str,
    message: str,
    context_json: str = "",
    extra: dict[str, Any] | None = None,
    timeout_sec: float | None = None,
) -> dict[str, Any]:
    url = _url(env_name, default_url)
    if not url:
        return {"ok": False, "error": {"code": "config", "message": f"Missing webhook URL ({env_name})"}}

    context: Any = {}
    if context_json and context_json.strip():
        try:
            context = json.loads(context_json)
        except json.JSONDecodeError:
            context = {"raw": context_json}

    body: dict[str, Any] = {
        "message": message or "",
        "chatInput": message or "",
        "context": context,
    }
    if extra:
        body.update({k: v for k, v in extra.items() if v is not None and v != ""})

    timeout = timeout_sec or float(os.getenv("N8N_SALES_INVOKE_TIMEOUT_SEC") or "120")
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers={"Content-Type": "application/json"})
        text = resp.text
        parsed: Any
        try:
            parsed = resp.json()
        except Exception:
            parsed = text
        return {
            "ok": 200 <= resp.status_code < 300,
            "status_code": resp.status_code,
            "webhook_url": url,
            "response": parsed,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": {"code": "invoke_failed", "message": str(e)},
            "webhook_url": url,
        }
