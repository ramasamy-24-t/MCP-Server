"""Azure Cosmos + AI Search + embeddings clients for MCP tools."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from azure.cosmos import CosmosClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from openai import AzureOpenAI

_HERE = Path(__file__).resolve().parent
# Local: repo/.env or mcp-server/.env; Railway/App Service: platform env vars
load_dotenv(_HERE.parent / ".env", override=False)
load_dotenv(_HERE / ".env", override=False)


def _req(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing env var: {name}")
    return val


@lru_cache(maxsize=1)
def cosmos() -> CosmosClient:
    return CosmosClient(_req("AZURE_COSMOS_ENDPOINT"), credential=_req("AZURE_COSMOS_KEY"))


def container(name_env: str, default: str):
    db = cosmos().get_database_client(os.getenv("AZURE_COSMOS_DATABASE", "ai_os"))
    return db.get_container_client(os.getenv(name_env, default))


@lru_cache(maxsize=1)
def search_client() -> SearchClient:
    return SearchClient(
        endpoint=_req("AZURE_SEARCH_ENDPOINT").rstrip("/"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "knowledge-index"),
        credential=AzureKeyCredential(_req("AZURE_SEARCH_ADMIN_KEY")),
    )


@lru_cache(maxsize=1)
def openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=_req("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=_req("AZURE_OPENAI_ENDPOINT").rstrip("/"),
    )


def embed_query(text: str, dimensions: int | None = 3072) -> list[float]:
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    kwargs: dict[str, Any] = {"model": deployment, "input": text}
    if dimensions:
        kwargs["dimensions"] = dimensions
    resp = openai_client().embeddings.create(**kwargs)
    return resp.data[0].embedding


def query_items(container_name_env: str, default: str, query: str, params: list[dict] | None = None) -> list[dict]:
    c = container(container_name_env, default)
    items = list(
        c.query_items(
            query=query,
            parameters=params or [],
            enable_cross_partition_query=True,
        )
    )
    return items
