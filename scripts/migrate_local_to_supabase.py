import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.supabase_client import get_supabase_client
from db.repositories import FAQRepository, TicketRepository


TICKETS_JSON = ROOT / "tickets_db.json"
FAQ_CSV = ROOT / "knowledge_base" / "Workplace_IT_Support_Database.csv"


def _read_tickets_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("tickets_db.json must be a list")
    return data


def _read_faq_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _normalize_ticket(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": t.get("id"),
        "title": t.get("title") or t.get("query") or "Untitled Ticket",
        "query": t.get("query") or "",
        "category": t.get("category") or "Others",
        "subcategory": t.get("subcategory"),
        "ai_draft": t.get("ai_draft") or "",
        "admin_draft": t.get("admin_draft") or t.get("ai_draft") or "",
        "status": t.get("status") or "Pending",
        "group_id": t.get("group_id") or t.get("id"),
        "users": t.get("users") or [],
        "history": t.get("history") or [],
        "final_answer": t.get("final_answer"),
        "thread_id": t.get("thread_id"),
        "notified": t.get("notified", True),
    }


def _normalize_faq(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("ID") or row.get("id"),
        "category": row.get("Category") or row.get("category") or "",
        "issue": row.get("Issue") or row.get("issue") or "",
        "question": row.get("Question") or row.get("question") or "",
        "resolution": row.get("Resolution") or row.get("resolution") or "",
        "tags": row.get("Tags") or row.get("tags") or "",
        # question_embedding intentionally not set here (populate in embedding job)
    }


def _chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def migrate(dry_run: bool = False, chunk_size: int = 200) -> None:
    load_dotenv()

    tickets_raw = _read_tickets_json(TICKETS_JSON)
    faq_raw = _read_faq_csv(FAQ_CSV)

    tickets = [_normalize_ticket(t) for t in tickets_raw if t.get("id")]
    faq_entries = [_normalize_faq(r) for r in faq_raw if (r.get("ID") or r.get("id"))]

    print(f"[INFO] Tickets found: {len(tickets_raw)} (valid for upsert: {len(tickets)})")
    print(f"[INFO] FAQ rows found: {len(faq_raw)} (valid for upsert: {len(faq_entries)})")

    if dry_run:
        print("[DRY-RUN] No data written to Supabase.")
        return

    client = get_supabase_client()
    ticket_repo = TicketRepository(client)
    faq_repo = FAQRepository(client)

    # Upsert tickets
    ticket_count = 0
    for batch in _chunked(tickets, chunk_size):
        for row in batch:
            ticket_repo.upsert_ticket(row)
            ticket_count += 1

    # Upsert FAQ
    faq_count = 0
    for batch in _chunked(faq_entries, chunk_size):
        for row in batch:
            faq_repo.upsert_entry(row)
            faq_count += 1

    print(f"[DONE] Upserted tickets: {ticket_count}")
    print(f"[DONE] Upserted faq entries: {faq_count}")

    # Optional quick sanity check
    db_tickets = ticket_repo.list_tickets()
    db_faq = faq_repo.list_entries()
    print(f"[CHECK] Supabase tickets count (current): {len(db_tickets)}")
    print(f"[CHECK] Supabase FAQ count (current): {len(db_faq)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local JSON/CSV data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Validate input only; do not write to DB")
    parser.add_argument("--chunk-size", type=int, default=200, help="Batch size for migration loops")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run, chunk_size=args.chunk_size)