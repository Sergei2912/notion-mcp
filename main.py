# -*- coding: utf-8 -*-
"""
Notion MCP Server – финальная версия
• GET  /sse  – keep-alive (“ready” каждые 60 с)
• POST /mcp  – JSON-команды {"action": "...", "parameters": {...}}
  Доступ защищён Bearer-токеном MCP_TOKEN из .env
"""

import os
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

from notion_client import create_page, create_task, update_page

load_dotenv()

app = FastAPI(title="Notion MCP", version="0.2.0")

# ---------- безопасность ----------
bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> None:
    """Проверка Bearer-токена."""
    token = os.getenv("MCP_TOKEN")
    if not token:
        raise RuntimeError("MCP_TOKEN отсутствует в .env")
    if not credentials or credentials.credentials != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


# ---------- модель команды ----------
class MCPCommand(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


# ---------- SSE ----------
@app.get("/sse")
async def sse(req):
    async def stream():
        while not await req.is_disconnected():
            yield {"event": "message", "data": "ready"}
            await asyncio.sleep(60)

    return EventSourceResponse(stream())


# ---------- MCP ----------
@app.post("/mcp", dependencies=[Depends(verify_token)])
async def mcp(cmd: MCPCommand):
    action = cmd.action
    p = cmd.parameters

    if action == "create_page":
        return {"status": "ok", "data": await create_page(p.get("title", "Untitled"))}

    if action == "create_task":
        return {"status": "ok", "data": await create_task(p)}

    if action == "update_page":
        return {"status": "ok", "data": await update_page(p)}

    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
