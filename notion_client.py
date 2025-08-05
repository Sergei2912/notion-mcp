# -*- coding: utf-8 -*-
"""Асинхронный клиент Notion API для MCP-серверa."""

import os
from typing import Dict, Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


async def _post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=HEADERS, json=payload)
    return r.json()


async def _patch(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.patch(url, headers=HEADERS, json=payload)
    return r.json()


# ---------- действия ----------
async def create_page(title: str) -> Dict[str, Any]:
    payload = {
        "parent": {"page_id": os.getenv("NOTION_PAGE_ID")},
        "properties": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": title},
                }
            ]
        },
    }
    return await _post(f"{BASE}/pages", payload)


async def create_task(p: Dict[str, Any]) -> Dict[str, Any]:
    db = os.getenv("NOTION_DATABASE_ID")
    if not db:
        return {"error": "NOTION_DATABASE_ID not set"}

    title = p.get("title", "Untitled")
    due_date = p.get("due_date")  # формат YYYY-MM-DD

    props: Dict[str, Any] = {
        "Name": {"title": [{"text": {"content": title}}]},
    }
    if due_date:
        props["Due date"] = {"date": {"start": due_date}}

    payload = {"parent": {"database_id": db}, "properties": props}
    return await _post(f"{BASE}/pages", payload)


async def update_page(p: Dict[str, Any]) -> Dict[str, Any]:
    page_id = p["page_id"]
    properties = p["properties"]

    payload = {"properties": properties}
    return await _patch(f"{BASE}/pages/{page_id}", payload)
