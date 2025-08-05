# -*- coding: utf-8 -*-
"""
Notion MCP Server
-----------------
• GET  /sse  — поддержка Server-Sent Events (“ready” каждые 60 с)
• POST /mcp  — приём JSON-команды вида:
      {"action": "...", "parameters": {...}}

Доступ к /mcp защищён Bearer-токеном (MCP_TOKEN в .env).
"""

import os
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

from notion_client import create_page, create_task, update_page

load_dotenv()  # подтягиваем MCP_TOKEN и NOTION_* из .env

app = FastAPI(title="Notion MCP", version="0.2.0")

# ---------- Авторизация ----------
bearer_scheme = HTTPBearer(scheme_name="MCP")


def verify_token(credentials: HTTPAuthorizationCredentials) -> None:
    """Проверяет Bearer-токен из заголовка Authorization."""
    expected = os.getenv("MCP_TOKEN")
    if not expected:
        raise RuntimeError("MCP_TOKEN not set in environment")
    if credentials.scheme.lower() != "bearer" or credentials.credentials != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


# ---------- Модель входной команды ----------
class MCPCommand(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}


# ---------- SSE энд-пойнт ----------
@app.get("/sse")
async def sse(req: Request):
    async def event_stream():
        while not await req.is_disconnected():
            yield {"event": "message", "data": "ready"}
            await asyncio.sleep(60)

    return EventSourceResponse(event_stream())


# ---------- Основной MCP энд-пойнт ----------
@app.post("/mcp")
async def mcp(
    cmd: MCPCommand,
    credentials: HTTPAuthorizationCredentials = bearer_scheme,
):
    # Проверяем токен
    verify_token(credentials)

    action = cmd.action
    params = cmd.parameters

    if action == "create_page":
        data = await create_page(params.get("title", "Untitled"))
        return {"status": "ok", "data": data}

    if action == "create_task":
        data = await create_task(params)
        return {"status": "ok", "data": data}

    if action == "update_page":
        data = await update_page(params)
        return {"status": "ok", "data": data}

    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
