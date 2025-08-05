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

# ----------- новые функции -----------

async def query_database(filter_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Запрос записей в базе данных Notion.

    Возвращает список страниц из базы данных, определённой переменной
    окружения ``NOTION_DATABASE_ID``. Фильтр можно передать через
    ``filter_payload`` – он будет включён в тело запроса, как
    описано в документации Notion API.

    Пример фильтра:

        {"property": "Due date", "date": {"equals": "2025-08-05"}}

    Если ``NOTION_DATABASE_ID`` не задан в окружении, возвращает
    словарь с ключом ``error``.
    """
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        return {"error": "NOTION_DATABASE_ID not set"}
    payload: Dict[str, Any] = {}
    if filter_payload:
        payload["filter"] = filter_payload
    return await _post(f"{BASE}/databases/{database_id}/query", payload)


async def retrieve_page(page_id: str) -> Dict[str, Any]:
    """Получить данные страницы Notion по её идентификатору.

    Использует эндпоинт GET /v1/pages/{page_id}. Возвращает JSON с
    подробной информацией о странице и её свойствах.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/pages/{page_id}", headers=HEADERS)
    return r.json()


async def archive_page(page_id: str, archived: bool = True) -> Dict[str, Any]:
    """Архивировать или восстановить страницу.

    В Notion удаление страницы осуществляется установкой поля
    ``archived`` (или ``in_trash``) в значение ``true``. Чтобы
    восстановить страницу, передайте ``archived=False``【208229300779467†L105-L123】.

    :param page_id: идентификатор страницы
    :param archived: ``True`` чтобы поместить в корзину, ``False`` чтобы
        восстановить
    :return: объект страницы после обновления
    """
    payload = {"archived": archived}
    return await _patch(f"{BASE}/pages/{page_id}", payload)


async def delete_block(block_id: str) -> Dict[str, Any]:
    """Удалить (архивировать) блок по ID.

    Этот эндпоинт помечает блок, включая страницы, как архивированный.
    Согласно документации Notion API, DELETE /blocks/{block_id} устанавливает
    ``archived`` на ``true``【348894490916182†L99-L105】.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.delete(f"{BASE}/blocks/{block_id}", headers=HEADERS)
    return r.json()


async def append_block_children(block_id: str, children: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Добавить дочерние блоки в конец блока.

    Использует PATCH /blocks/{block_id}/children. Список
    ``children`` должен быть массивом блоков в формате Notion API.
    Максимум 100 блоков за раз.
    """
    payload = {"children": children}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.patch(
            f"{BASE}/blocks/{block_id}/children", headers=HEADERS, json=payload
        )
    return r.json()


async def retrieve_block_children(block_id: str) -> Dict[str, Any]:
    """Получить дочерние блоки указанного блока.

    Выполняет GET /blocks/{block_id}/children и возвращает список
    содержимого страницы или другого блока.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/blocks/{block_id}/children", headers=HEADERS)
    return r.json()


async def retrieve_database(database_id: str) -> Dict[str, Any]:
    """Получить свойства базы данных.

    Эндпоинт GET /databases/{database_id} возвращает описание базы
    данных и её свойства.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/databases/{database_id}", headers=HEADERS)
    return r.json()


async def search(query: str, filter: Dict[str, Any] | None = None, sort: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Поиск по рабочему пространству Notion.

    Отправляет POST /search с текстовым запросом. Можно указать
    фильтр и сортировку. Подробнее см. документацию Notion API.
    """
    payload: Dict[str, Any] = {"query": query}
    if filter:
        payload["filter"] = filter
    if sort:
        payload["sort"] = sort
    return await _post(f"{BASE}/search", payload)
