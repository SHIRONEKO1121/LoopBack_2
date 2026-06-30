import os
import json
import time
import datetime
import uuid
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from langsmith import wrappers
from difflib import SequenceMatcher
from db.repositories import FAQRepository, TicketRepository
from db.supabase_client import get_supabase_client, is_supabase_enabled

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING')

if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in environment variables. Gemini API calls will fail.")

gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# Wrap the Gemini client to enable LangSmith tracing
if LANGSMITH_TRACING:
    LANGSMITH_ENDPOINT = os.getenv('LANGSMITH_ENDPOINT')
    LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
    LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT')
    client = wrappers.wrap_gemini(
            gemini_client,
            tracing_extra={
                "tags": ["gemini", "python"],
                "metadata": {
                    "integration": "google-genai",
                },
            },
        )
else:
    client = gemini_client

app = FastAPI(title="LoopBack AI IT Hub API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---
BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "knowledge_base"

# --- Repositories ---
ticket_repo = None
faq_repo = None

if is_supabase_enabled():
    supabase_client = get_supabase_client()
    ticket_repo = TicketRepository(supabase_client)
    faq_repo = FAQRepository(supabase_client)

# --- Data Models ---
class Ticket(BaseModel):
    id: Optional[str] = None
    title: str  # NEW: Summary title
    query: str  # The extracted user dialogue
    category: str # Network, Hardware, Software, Account, Facility, Others
    subcategory: Optional[str] = None # Max 2 words
    ai_draft: str # Suggested draft (First person, Admin perspective)
    status: str = "Pending"
    group_id: Optional[str] = None
    history: List[dict] = []
    final_answer: Optional[str] = None
    thread_id: Optional[int] = None
    notified: bool = True # Track if the user has been notified of the latest status change

class CreateTicketRequest(BaseModel):
    query: str
    history: List[dict] = [] # NEW: Full chat history
    users: List[str] = ["User_Unknown"]
    force_create: bool = False
    thread_id: Optional[int] = None

class BroadcastRequest(BaseModel):
    ticket_id: str
    final_answer: str

class BroadcastAllRequest(BaseModel):
    category: Optional[str] = None
    ticket_ids: Optional[List[str]] = None
    final_answer: str

class AskRequest(BaseModel):
    question: str

class TicketMetadata(BaseModel):
    title: str = Field(description="Issue Summary")
    category: str = Field(description="Network|Hardware|Software|Account|Others")
    subcategory: str = Field(description="Subcategory (Max 2 words)")

class Response(BaseModel):
    confidence: str = Field(description="high|medium|low")
    summary: str = Field(description="Concise 1-sentence summary of the issue (e.g. 'User needs a smaller keyboard due to injury')")
    ticket_metadata: TicketMetadata
    solution_draft: str = Field(description="Admin draft solution or Chat response")
    escalation_required: bool = Field(default=False, description="True if escalation is required")
    is_it_related: bool = Field(default=True, description="True if query is IT Support related (hardware, software, network, account, etc.). False for chit-chat, weather, general knowledge.")

class MessageAppendRequest(BaseModel):
    role: str
    message: str


# --- Helper Functions ---
def get_kb_context_summary(query: str = ""):
    """Returns top relevant KB items from Supabase based on query keywords."""
    if not faq_repo:
        print("DEBUG: ⚠️ FAQ repository not initialized")
        return ""
    
    summary = []
    # robust tokenization: strip punctuation and lowercase
    import re
    query_words = set(re.findall(r'\w+', query.lower())) if query else set()
    print(f"DEBUG: 🔍 FAQ Search Query: '{query}' Tokens: {query_words}")

    scored_rows = []
    try:
        for row in faq_repo.list_entries(limit=50):
            search_text = (
                f"{row.get('category','')} "
                f"{row.get('issue','')} "
                f"{row.get('question','')} "
                f"{row.get('tags','')}"
            ).lower()

            match_count = sum(1 for w in query_words if w in search_text)

            if match_count > 0:
                content = (
                    f"Issue: {row.get('issue', '')}\n"
                    f"Question: {row.get('question', '')}\n"
                    f"Resolution: {row.get('resolution', '')}\n"
                )
                scored_rows.append((match_count, content))

        scored_rows.sort(key=lambda x: x[0], reverse=True)
        print(f"DEBUG: 🔢 Found {len(scored_rows)} FAQ matches.")
        for i, (score, content) in enumerate(scored_rows[:3]):
            print(f"DEBUG:   Match #{i+1} (Score: {score}): {content.splitlines()[0]}")
        summary = [item[1] for item in scored_rows[:3]]

    except Exception as e:
        print(f"DEBUG: ❌ FAQ Search Error: {e}")
        
    return "\n---\n".join(summary)

def is_quality_solution(text: str) -> bool:
    """Checks if text is a real solution."""
    if not text or len(text) < 15: return False
    lower = text.lower()
    bridges = ["connecting you", "transferring", "admin to assist", "support team", "logged a ticket", "escalated"]
    if any(b in lower for b in bridges) and len(text) < 60: return False
    
    # Exclude transactional/request handling responses
    transactional_phrases = [
        "received your request", "initiate the", "monitor the", "let you know", 
        "approval", "access granted", "deployed", "shipping", "ordered", 
        "will now", "have been added"
    ]
    if any(t in lower for t in transactional_phrases): 
        print(f"DEBUG: 🚫 Skipped KB update (Transactional response detected)")
        return False

    indicators = ["check", "try", "navigate", "click", "install", "reset", "restart", "verify", "password", "steps:", "how to"]
    return any(i in lower for i in indicators) or len(text) > 40

# --- Gemini Logic ---
def analyze_with_gemini(query: str, mode: str = "ticket") -> Dict[str, Any]:
    """Analyzes query using Gemini with optimized context."""
    if not GOOGLE_API_KEY:
        return {"confidence": "low", "reasoning": "No API Key", "ticket_metadata": {"title": "Error"}, "solution_draft": "System Error: No API Key.", "summary": "Error"}

    try:
        kb_context = get_kb_context_summary(query)
        
        if mode == "chat":
            prompt = f"""You are a Tier 1 IT Support AI.
Context:
{kb_context}

User: {query}

Task: Respond directly. If issue requires admin/hardware/account fix or user asks for ticket, or if the message is a test message, set "escalation_required": true. Else false.
If the message is a test message,, set escalation_required to false, and tell the user that the system is running well.
Return JSON:
{{
  "solution_draft": "Response...",
  "escalation_required": true|false,
  "confidence": "high|medium|low",
  "is_it_related": true|false,
  "summary": "Standardized, professional issue title (e.g. 'VPN Access Failure' or 'Laptop Screen Replacement Request'). Avoid 'User reports' or 'Customer needs'. Just state the issue.",
  "ticket_metadata": {{
    "title": "Title",
    "category": "Category",
    "subcategory": "Subcategory"
  }}
}}"""
        else:
            prompt = f"""You are an IT Support AI.
Context:
{kb_context}

User: "{query}"

Task: Analyze, generate metadata, and write Admin solution draft (1st person).
Return JSON:
{{
  "confidence": "high|medium|low",
  "summary": "Standardized, professional issue title (e.g. 'VPN Access Failure'). Avoid 'User reports'. Just state the issue.",
  "ticket_metadata": {{
    "title": "Issue Summary",
    "category": "Network|Hardware|Software|Account|Others",
    "subcategory": "Subcategory (Max 2 words)"
  }},
  "solution_draft": "Admin draft...",
  "escalation_required": true,
  "is_it_related": true
}}"""
            
        # Use the wrapped client to call the new API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Response.model_json_schema(),
            },
        )

        # Extract textual content
        content_text = ""
        try:
            if hasattr(response, "text") and response.text:
                content_text = response.text
            else:
                content_text = str(response)
        except Exception:
            content_text = str(response)

        try:
            # Clean possible markdown
            content_text = content_text.strip()
            if content_text.startswith("```json"):
                content_text = content_text.split("\n", 1)[1].rsplit("\n", 1)[0]
            elif content_text.startswith("```"):
                content_text = content_text.split("\n", 1)[1].rsplit("\n", 1)[0]
                
            return json.loads(content_text)
        except Exception:
            print("Gemini Error: Failed to parse response as JSON. Returning raw content.")
            return {"confidence": "low", "solution_draft": content_text, "ticket_metadata": {}, "summary": query}

    except Exception as e:
        error_str = str(e)
        print(f"Gemini Error: {error_str}")
        
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            msg = "⚠️ AI Service Busy: quota exhausted. Please try again in a few minutes."
        else:
            msg = f"System Error: {error_str}"
            
        return {
            "confidence": "low", 
            "solution_draft": msg, 
            "ticket_metadata": {"title": "Error", "category": "Others", "subcategory": "System Error"}, 
            "summary": "System Error"
        }

# --- Endpoints ---
@app.get("/tickets")
async def get_tickets():
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    return ticket_repo.list_tickets()

@app.post("/tickets/{ticket_id}/ack_notification")
async def ack_notification(ticket_id: str):
    """Called by the bot to confirm it has notified the user."""
    if ticket_repo and ticket_repo.ack_notification(ticket_id):
        return {"status": "acked"}
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    raise HTTPException(status_code=404, detail="Ticket not found")

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = [] # List of {"role": "user"|"model", "content": "..."}

@app.post("/chat/analyze")
async def analyze_chat(req: ChatRequest):
    """
    Analyzes chat context and returns an AI response + confidence.
    Does NOT create a ticket yet.
    """
    print(f"DEBUG: 💬 Chat Request: {req.message}")
    
    # Construct context from history
    history_context = ""
    for msg in req.history[-5:]: # Last 5 messages for context
        role = "User" if msg.get("role") == "user" else "AI"
        history_context += f"{role}: {msg.get('content')}\n"
    
    full_prompt = f"{history_context}\nUser: {req.message}"
    
    ai_result = analyze_with_gemini(full_prompt, mode="chat")
    
    # Check for keywords to force escalation logic if needed
    escalate = ai_result.get("escalation_required", False)
    if not escalate:
        if "ticket" in req.message.lower() or "admin" in req.message.lower() or "escalate" in req.message.lower():
             escalate = True
    
    return {
        "response": ai_result.get("solution_draft"),
        "escalation_required": escalate,
        "confidence": ai_result.get("confidence"),
        "is_it_related": ai_result.get("is_it_related", True),
        "metadata": ai_result.get("ticket_metadata"),
        "summary": ai_result.get("summary", req.message) # Return summary
    }

@app.post("/tickets")
async def create_ticket(req: CreateTicketRequest):
    print(f"DEBUG: 📩 New Ticket Request: {req.query} (Force: {req.force_create})")
    
    # AI Analysis for categorization (if not provided/if needed)
    # If the frontend passes a 'summary' as 'req.query', we use it.
    # We still run analyze_with_gemini to get metadata categorization based on that summary/query.
    
    # NEW: Construct full prompt from history for better context
    analysis_input = req.query
    if req.history:
        history_str = "\n".join([f"{m.get('role', 'User')}: {m.get('content', m.get('message', ''))}" for m in req.history])
        analysis_input = f"{history_str}\n\nUser Request: {req.query}"

    ai_result = analyze_with_gemini(analysis_input, mode="ticket")
    conf = ai_result.get("confidence", "low")
    meta = ai_result.get("ticket_metadata", {})
    draft = ai_result.get("solution_draft", "")
    
    # 2. High/Medium Confidence Intercept (No Ticket Created yet)
    if not req.force_create and (conf == "high" or conf == "medium"):
        print(f"DEBUG: 🤖 Intercepted with {conf} confidence. Suggesting solution.")
        return {
            "status": "suggested",
            "confidence": conf,
            "solution": draft,
            "ticket_id": None # No ticket created
        }

    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    # 3. Create Ticket (Low Confidence OR User Forced)

    # Prepare history
    ticket_history = []
    if req.history:
        for msg in req.history:
            ticket_history.append({
                "role": msg.get("role"),
                "message": msg.get("content", msg.get("message")),
                "time": time.strftime("%H:%M") # Timestamp for now
            })
    else:
        # Fallback to single entry
        ticket_history.append({
            "role": "user", 
            "message": req.query, 
            "time": time.strftime("%H:%M")
        })

    # If query is short (e.g. "ticket"), use AI summary
    final_query = req.query
    if len(req.query.split()) < 4 and ai_result.get("summary"):
        final_query = ai_result.get("summary")
    
    new_ticket = {
        "title": meta.get("title", final_query),
        "query": final_query, 
        "category": meta.get("category", "Others"),
        "subcategory": meta.get("subcategory", "General"),
        "ai_draft": draft,
        "admin_draft": draft,
        "status": "Pending",
        "group_id": None,
        "users": req.users,
        "history": ticket_history,
        "thread_id": req.thread_id,
        "notified": True # Created by bot, so user knows.
    }

    created_ticket = ticket_repo.create_ticket(new_ticket)
    ticket_id = created_ticket.get("id")
    if ticket_id and created_ticket.get("group_id") in [None, ""]:
        ticket_repo.update_ticket(ticket_id, {"group_id": ticket_id})
    return {
        "status": "created", 
        "ticket_id": ticket_id, 
        "confidence": conf,
        "solution": draft if conf == "high" else None
    }

def kb_entry_exists(new_query: str) -> bool:
    """Checks if a similar query already exists in the FAQ repository."""
    if not faq_repo:
        return False

    try:
        for row in faq_repo.list_entries(limit=200):
            for text in [row.get('question', ''), row.get('issue', '')]:
                if not text:
                    continue
                ratio = SequenceMatcher(None, new_query.lower(), text.lower()).ratio()
                if ratio > 0.85:
                    print(f"DEBUG: 🚫 FAQ Duplicate prevented: '{new_query}' similar to '{text}' ({ratio:.2f})")
                    return True
    except Exception as e:
        print(f"DEBUG: ❌ FAQ duplicate check error: {e}")
    return False

def standardize_resolution(text: str) -> str:
    """Uses Gemini to rewrite a response into a standardized KB resolution."""
    if not text or not GOOGLE_API_KEY: return text
    
    try:
        prompt = f"""Rewrite the following support response into a standardized, technical resolution for a Knowledge Base. 
        Rules:
        1. Remove pleasantries (Hi, Thanks, Sorry, 'I will...').
        2. Use imperative or objective tone (e.g., 'Connect to VPN...' or 'Ticket #123 created for hardware replacement').
        3. Keep it concise.
        4. OUTPUT PLAIN TEXT ONLY. Do NOT use markdown formatting (no bold **, no italics *, no code blocks).
        5. Do NOT include prefixes like "KB Resolution:" or "Resolution:". Start directly with the action.
        
        Input: "{text}"
        """
        
        # Use the wrapped client if available, else gemini_client
        c = client if 'client' in globals() else gemini_client
        response = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        if hasattr(response, "text"):
            return response.text.strip()
        else:
            return str(response).strip()
    except Exception as e:
        print(f"Standardization Error: {e}")
        return text

@app.post("/tickets/{ticket_id}/messages")
async def append_ticket_message(ticket_id: str, req: MessageAppendRequest):
    """
    Appends a message to the ticket's history.
    """
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    updated_ticket = ticket_repo.append_history_message(ticket_id, req.role, req.message)
    if not updated_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "updated", "history_length": len(updated_ticket.get("history", []))}

@app.post("/broadcast")
async def broadcast_solution(req: BroadcastRequest):
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    ticket = ticket_repo.get_ticket(req.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updated_ticket = ticket_repo.update_ticket(
        req.ticket_id,
        {
            "status": "Resolved",
            "final_answer": req.final_answer,
            "notified": False,
        },
    )
    ticket_repo.append_history_message(req.ticket_id, "model", f"**Resolution:** {req.final_answer}")

    if ticket and req.final_answer and is_quality_solution(req.final_answer) and faq_repo:
        target_ticket_query = ticket.get("query", "")
        target_category = ticket.get("category", "Support")
        target_subcategory = ticket.get("subcategory", "")

        if kb_entry_exists(target_ticket_query):
            print(f"DEBUG: ⏭️ Skipping KB update (Duplicate detected)")
        else:
            try:
                std_resolution = standardize_resolution(req.final_answer)
                faq_repo.create_entry(
                    {
                        "category": target_category,
                        "issue": "",
                        "question": target_ticket_query,
                        "resolution": std_resolution,
                        "tags": f"{target_category};{target_subcategory or ''};Resolved",
                    }
                )
                print(f"DEBUG: 📚 Added solution to Knowledge Base")
            except Exception as e:
                print(f"DEBUG: ❌ Failed to update Knowledge Base: {e}")

    return {"status": "success", "resolved": 1 if updated_ticket else 0}

@app.post("/broadcast_all")
async def broadcast_all(req: BroadcastAllRequest):
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    tickets = ticket_repo.list_tickets()
    count = 0
    for t in tickets:
        if t["status"] == "Pending":
            update = False
            if req.ticket_ids and t["id"] in req.ticket_ids:
                update = True
            elif req.category and t.get("category") == req.category:
                update = True

            if update:
                ticket_repo.update_ticket(
                    t["id"],
                    {
                        "status": "Resolved",
                        "final_answer": req.final_answer,
                        "notified": False,
                    },
                )
                ticket_repo.append_history_message(
                    t["id"],
                    "model",
                    f"**Resolution Broadcast:** {req.final_answer}",
                )
                count += 1

    if count > 0 and is_quality_solution(req.final_answer) and faq_repo:
        start_cat = req.category or "Batch"
        batch_query = f"Batch Resolved: {count} tickets"

        if kb_entry_exists(batch_query):
            print(f"DEBUG: ⏭️ Skipping Batch KB update (Duplicate detected)")
        else:
            try:
                std_batch_res = standardize_resolution(req.final_answer)
                faq_repo.create_entry(
                    {
                        "category": start_cat,
                        "issue": "",
                        "question": batch_query,
                        "resolution": std_batch_res,
                        "tags": f"{start_cat};BatchResolved",
                    }
                )
            except Exception:
                pass

    return {"status": "success", "resolved": count}

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str):
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    ticket_repo.delete_ticket(ticket_id)
    return {"status": "deleted"}

@app.post("/tickets/{ticket_id}/ask")
async def ask_user(ticket_id: str, req: AskRequest):
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    updated_ticket = ticket_repo.update_ticket(
        ticket_id,
        {
            "status": "Awaiting Info",
            "notified": False,
        },
    )
    if not updated_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket_repo.append_history_message(ticket_id, "admin", req.question)
    return {"status": "sent"}

@app.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket_user(ticket_id: str):
    """
    Endpoint for users to mark their own ticket as resolved
    (e.g., if the AI suggestion worked).
    """
    if not ticket_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    updated_ticket = ticket_repo.update_ticket(
        ticket_id,
        {
            "status": "Self-Resolved",
            "final_answer": "User marked as resolved based on AI suggestion.",
        },
    )
    if not updated_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket_repo.append_history_message(
        ticket_id,
        "user",
        "This solution worked for me. Closing ticket.",
    )
    return {"status": "resolved"}

# --- Knowledge Base CRUD ---

class KBEntry(BaseModel):
    id: Optional[str] = None
    category: str
    issue: Optional[str] = "" # Optional/Deprecated
    question: str
    resolution: str
    tags: Optional[str] = None

@app.get("/knowledge-base")
async def get_kb_entries(limit: int = 5):
    """Returns all KB entries."""
    if not faq_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    return faq_repo.list_entries(limit=limit)

@app.post("/knowledge-base")
async def create_kb_entry(entry: KBEntry):
    """Creates a new KB entry."""
    if not faq_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    created_entry = faq_repo.create_entry(
        {
            "category": entry.category,
            "issue": entry.issue or "",
            "question": entry.question,
            "resolution": standardize_resolution(entry.resolution),
            "tags": entry.tags or "",
        }
    )
    return {"status": "created", "entry": created_entry}

@app.put("/knowledge-base/{entry_id}")
async def update_kb_entry(entry_id: str, entry: KBEntry):
    """Updates an existing KB entry."""
    if not faq_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    updated_entry = faq_repo.update_entry(
        entry_id,
        {
            "category": entry.category,
            "issue": entry.issue or "",
            "question": entry.question,
            "resolution": standardize_resolution(entry.resolution),
            "tags": entry.tags or "",
        },
    )
    if updated_entry:
        return {"status": "updated", "entry": updated_entry}
    raise HTTPException(status_code=404, detail="Entry not found")

@app.delete("/knowledge-base/{entry_id}")
async def delete_kb_entry(entry_id: str):
    """Deletes a KB entry."""
    if not faq_repo:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    faq_repo.delete_entry(entry_id)
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
