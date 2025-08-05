# -*- coding: utf-8 -*-
"""
Notion MCP Server.

Этот сервер предоставляет интерфейс JSON‑RPC для взаимодействия с
Notion через ChatGPT. Он реализует keep‑alive SSE‑канал и эндпоинт
``/mcp`` для выполнения различных действий: создание/изменение/архивация
страниц, создание задач, чтение базы данных, поиск, добавление и
удаление блоков и другие.

Аутентификация: если переменная окружения ``MCP_TOKEN`` задана,
сервер ожидает Bearer‑токен в заголовке ``Authorization``; если
``MCP_TOKEN`` не определён, аутентификация отключена.
"""

import os
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

from notion_client import (
    create_page,
    create_task,
    update_page,
    query_database,
    retrieve_page,
    archive_page,
    delete_block,
    append_block_children,
    retrieve_block_children,
    retrieve_database,
    search,
)

load_dotenv()

app = FastAPI(title="Notion MCP", version="0.2.0")

# ---------- безопасность ----------
bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> None:
    """Проверка Bearer-токена.

    Если переменная ``MCP_TOKEN`` задана, требуется соответствие
    авторизационного заголовка. Если токен не задан – проверка
    пропускается.
    """
    token = os.getenv("MCP_TOKEN")
    # если токен не установлен — пропускаем проверку
    if not token:
        return
    # если переданный токен не совпадает — 401
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

    if action == "query_database":
        # p может содержать необязательный фильтр
        filter_payload = p.get("filter") if isinstance(p, dict) else None
        return {"status": "ok", "data": await query_database(filter_payload)}

    if action == "retrieve_page":
        page_id = p.get("page_id") if isinstance(p, dict) else None
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id is required for retrieve_page")
        return {"status": "ok", "data": await retrieve_page(page_id)}

    if action == "archive_page":
        page_id = p.get("page_id") if isinstance(p, dict) else None
        archived_flag = p.get("archived", True) if isinstance(p, dict) else True
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id is required for archive_page")
        return {"status": "ok", "data": await archive_page(page_id, bool(archived_flag))}

    if action == "delete_block":
        block_id = p.get("block_id") if isinstance(p, dict) else None
        if not block_id:
            raise HTTPException(status_code=400, detail="block_id is required for delete_block")
        return {"status": "ok", "data": await delete_block(block_id)}

    if action == "append_block_children":
        block_id = p.get("block_id") if isinstance(p, dict) else None
        children = p.get("children") if isinstance(p, dict) else None
        if not block_id or not isinstance(children, list):
            raise HTTPException(status_code=400, detail="block_id and children (list) required for append_block_children")
        return {"status": "ok", "data": await append_block_children(block_id, children)}

    if action == "retrieve_block_children":
        block_id = p.get("block_id") if isinstance(p, dict) else None
        if not block_id:
            raise HTTPException(status_code=400, detail="block_id is required for retrieve_block_children")
        return {"status": "ok", "data": await retrieve_block_children(block_id)}

    if action == "retrieve_database":
        database_id = p.get("database_id") if isinstance(p, dict) else None
        if not database_id:
            raise HTTPException(status_code=400, detail="database_id is required for retrieve_database")
        return {"status": "ok", "data": await retrieve_database(database_id)}

    if action == "search":
        query = p.get("query") if isinstance(p, dict) else None
        if not query:
            raise HTTPException(status_code=400, detail="query is required for search")
        filter_payload = p.get("filter") if isinstance(p, dict) else None
        sort_payload = p.get("sort") if isinstance(p, dict) else None
        return {"status": "ok", "data": await search(query, filter_payload, sort_payload)}

    # неизвестное действие
    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
            
