# 2) repositories starter
# Place in: db/repositories.py

import time
import uuid
from typing import Any, Dict, List, Optional

from supabase import Client


def _sanitize_ticket(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize ticket row shape for API compatibility."""
    return {
        "id": row.get("id"),
        "ticket_no": row.get("ticket_no"),
        "title": row.get("title"),
        "query": row.get("query"),
        "category": row.get("category", "Others"),
        "subcategory": row.get("subcategory"),
        "ai_draft": row.get("ai_draft", ""),
        "admin_draft": row.get("admin_draft", row.get("ai_draft", "")),
        "status": row.get("status", "Pending"),
        "group_id": row.get("group_id"),
        "users": row.get("users", []),
        "history": row.get("history", []),
        "final_answer": row.get("final_answer"),
        "thread_id": row.get("thread_id"),
        "notified": row.get("notified", True),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


class TicketRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "tickets"

    def list_tickets(self) -> List[Dict[str, Any]]:
        resp = self.client.table(self.table).select("*").order("created_at", desc=True).execute()
        return [_sanitize_ticket(r) for r in (resp.data or [])]

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self.client.table(self.table)
            .select("*")
            .eq("id", ticket_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return _sanitize_ticket(rows[0]) if rows else None

    def create_ticket(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data.setdefault("status", "Pending")
        data.setdefault("users", [])
        data.setdefault("history", [])
        data.setdefault("notified", True)
        data.setdefault("admin_draft", data.get("ai_draft", ""))

        resp = self.client.table(self.table).insert(data).execute()
        row = (resp.data or [data])[0]
        return _sanitize_ticket(row)

    def upsert_ticket(self, payload: Dict[str, Any]) -> None:
        # Requires "id" in payload
        self.client.table(self.table).upsert(payload, on_conflict="id").execute()

    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        resp = (
            self.client.table(self.table)
            .update(updates)
            .eq("id", ticket_id)
            .execute()
        )
        rows = resp.data or []
        return _sanitize_ticket(rows[0]) if rows else None

    def delete_ticket(self, ticket_id: str) -> None:
        self.client.table(self.table).delete().eq("id", ticket_id).execute()

    def ack_notification(self, ticket_id: str) -> bool:
        updated = self.update_ticket(ticket_id, {"notified": True})
        return updated is not None

    def append_history_message(self, ticket_id: str, role: str, message: str) -> Optional[Dict[str, Any]]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None

        history = ticket.get("history") or []
        history.append(
            {
                "role": role,
                "message": message,
                "time": time.strftime("%H:%M"),
            }
        )
        return self.update_ticket(ticket_id, {"history": history})


class FAQRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "faq_entries"

    def list_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self.client.table(self.table).select("*").order("created_at", desc=True)
        if limit is not None:
            query = query.limit(limit)
        resp = query.execute()
        return resp.data or []

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self.client.table(self.table)
            .select("*")
            .eq("id", entry_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None

    def create_entry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data.setdefault("id", str(uuid.uuid4())[:8])
        data.setdefault("issue", "")
        data.setdefault("tags", "")
        resp = self.client.table(self.table).insert(data).execute()
        return (resp.data or [data])[0]

    def upsert_entry(self, payload: Dict[str, Any]) -> None:
        self.client.table(self.table).upsert(payload, on_conflict="id").execute()

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        resp = (
            self.client.table(self.table)
            .update(updates)
            .eq("id", entry_id)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None

    def delete_entry(self, entry_id: str) -> None:
        self.client.table(self.table).delete().eq("id", entry_id).execute()