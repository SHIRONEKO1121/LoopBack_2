import os
import json
import csv
import time
import requests
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
ORCHESTRATION_ID = os.getenv('ORCHESTRATION_ID')
INSTANCE_ID = os.getenv('INSTANCE_ID')
AGENT_ID = os.getenv('AGENT_ID')
HOST_URL = os.getenv('HOST_URL')

app = FastAPI(title="LoopBack AI IT Hub API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration & Paths ---
BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "knowledge_base"
DB_FILE = BASE_DIR / "tickets_db.json"

# --- Data Models ---
class Ticket(BaseModel):
    id: Optional[str] = None
    group_id: Optional[str] = None
    query: str
    ai_draft: str
    status: str = "Pending"
    users: List[str] = ["User_Unknown"]

class AskRequest(BaseModel):
    message: str

class BroadcastRequest(BaseModel):
    ticket_id: str
    # group_id: Optional[str] = None
    final_answer: str

# --- Database Mock ---
def load_db():
    if not DB_FILE.exists():
        return []
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- Endpoints ---

@app.get("/tickets")
async def get_tickets():
    return load_db()

@app.post("/tickets")
async def create_ticket(ticket: Ticket):
    print(f"DEBUG: 📩 Ticket creation request received!")
    db = load_db()
    
    # 1. Get Token for AI (re-using the one from ask_ai if possible, or get new)
    try:
        tr = requests.post("https://iam.cloud.ibm.com/identity/token", 
                          data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY})
        token = tr.json().get("access_token")
    except:
        token = None

    # 2. Check for Similarity
    group_id = None
    if token:
         group_id = check_similarity_ai(ticket.query, db, token)
    
    ticket.id = f"TKT-{1020 + len(db) + 1}"
    
    if group_id:
        print(f"DEBUG: 🔗 Linking new ticket {ticket.id} to Group {group_id}")
        ticket.group_id = group_id
    else:
        print(f"DEBUG: 🆕 New Group established for {ticket.id}")
        ticket.group_id = ticket.id

    db.append(ticket.dict())
    save_db(db)
    print(f"DEBUG: ✅ Ticket created: {ticket.id}")
    return {"status": "created", "ticket_id": ticket.id, "group_id": ticket.group_id}

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str):
    print(f"DEBUG: 🗑️ Delete request for ticket: {ticket_id}")
    db = load_db()
    original_count = len(db)
    db = [t for t in db if t.get("id") != ticket_id]
    
    if len(db) < original_count:
        save_db(db)
        print(f"DEBUG: ✅ Ticket {ticket_id} deleted successfully")
        return {"status": "deleted", "ticket_id": ticket_id}
    else:
        print(f"DEBUG: ⚠️ Ticket {ticket_id} not found")
        raise HTTPException(status_code=404, detail="Ticket not found")

@app.post("/broadcast")
async def broadcast_solution(req: BroadcastRequest):
    db = load_db()
    
    # Check if we can find the group_ID first
    target_group = None
    for ticket in db:
        if ticket["id"] == req.ticket_id:
            target_group = ticket.get("group_id", ticket["id"]) # Fallback to own ID if None
            break
            
    if target_group:
        print(f"DEBUG: 📢 Broadcasting solution to Group: {target_group}")
        count = 0
        for ticket in db:
            # Update matching group OR if it's the exact ticket ID (legacy case)
            if ticket.get("group_id") == target_group or ticket["id"] == req.ticket_id:
                ticket["status"] = "Resolved"
                ticket["final_answer"] = req.final_answer
                count += 1
        print(f"DEBUG: ✅ Resolved {count} tickets in group.")
    else:
        print("DEBUG: ⚠️ Ticket ID not found for broadcast.")

    save_db(db)
    return {"status": "broadcast_complete"}

@app.get("/search_knowledge")
async def search_knowledge(query: str):
    print(f"DEBUG: 🔍 Knowledge search triggered: '{query}'")
    results = []
    query_words = [w.lower() for w in query.replace('?', '').split() if len(w) >= 3]
    
    # Search Files
    for file_path in KB_DIR.glob("*"):
        if file_path.suffix.lower() == ".csv":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        text = " ".join([str(v) for v in row.values() if v]).lower()
                        if query.lower() in text or any(word in text for word in query_words):
                            results.append({"source": file_path.name, "content": row})
            except: pass
        elif file_path.suffix.lower() == ".txt":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if query.lower() in content.lower() or any(word in content.lower() for word in query_words):
                        results.append({"source": file_path.name, "content": content[:500]})
            except: pass
            
    print(f"DEBUG: ✅ Found {len(results)} search results")
    return {"results": results[:5]}

    print(f"DEBUG: ✅ Found {len(results)} search results")
    return {"results": results[:5]}

def check_similarity_ai(new_query: str, existing_tickets: List[dict], token: str) -> Optional[str]:
    """
    Uses Watsonx.ai to check if new_query matches any existing ticket.
    Returns the group_id (ticket ID of the match) or None.
    """
    if not existing_tickets:
        return None
        
    # Prepare a summary list for the prompt to save tokens
    # We only check 'Pending' tickets to group active issues
    active_tickets = [t for t in existing_tickets if t.get("status") == "Pending"]
    if not active_tickets:
        return None

    # Construct the prompt
    candidates_text = "\n".join([f"- ID: {t['id']}, Issue: {t['query']}" for t in active_tickets[:20]]) # Limit to 20 recent
    
    prompt = f"""You are an IT Support Triage AI.
Check if the New Issue matches any of the Existing Issues. 
They match if they are about the EXACT SAME technical problem (e.g., "wifi broken" vs "cannot connect to internet").
If they match, return ONLY the ID of the existing issue.
If they do not match, return "None".

Existing Issues:
{candidates_text}

New Issue: {new_query}

Match ID:"""

    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Using Granite or similar model available in standard Watsonx
    body = {
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 10,
            "min_new_tokens": 1,
            "stop_sequences": ["\n"],
            "repetition_penalty": 1.0
        },
        "model_id": "ibm/granite-13b-chat-v2",
        "project_id": "e92c7a79-2dc4-4966-b458-48e6728c556e" # Using similar ID structure as instance for now, usually project_id is different
    }

    try:
        print("DEBUG: 🤖 Asking Watsonx.ai to group tickets...")
        response = requests.post(url, headers=headers, json=body)
        if response.status_code != 200:
            print(f"DEBUG: ⚠️ AI Grouping failed: {response.text}")
            return None
            
        result_text = response.json()['results'][0]['generated_text'].strip()
        print(f"DEBUG: 🤖 AI Decision: {result_text}")
        
        # Check if result is a valid ID from our list
        for t in active_tickets:
            if t['id'] in result_text:
                return t.get("group_id", t['id'])
                
        return None

    except Exception as e:
        print(f"DEBUG: ❌ AI Grouping error: {e}")
        return None

def extract_ai_response(data: dict) -> Optional[str]:
    """
    Extract AI response from Watsonx API response.
    Scans multiple possible JSON paths where the text might be.
    """
    candidates = []
    
    # ⭐ Path 0: step_history (MOST IMPORTANT - contains actual workflow responses)
    try:
        result = data.get("result")
        if result and isinstance(result, dict):
            data_obj = result.get("data")
            if data_obj and isinstance(data_obj, dict):
                message = data_obj.get("message")
                if message and isinstance(message, dict):
                    step_history = message.get("step_history", [])
                    for step in step_history:
                        if step.get("role") == "assistant":
                            step_details = step.get("step_details", [])
                            for detail in step_details:
                                # Check for tool_response type (contains the actual AI answer)
                                if detail.get("type") == "tool_response":
                                    # Try to get the response content
                                    tool_resp = detail.get("response", {})
                                    
                                    # Check various response formats
                                    if isinstance(tool_resp, dict):
                                        # Format 1: Direct text field
                                        if "text" in tool_resp:
                                            candidates.append(("step_history.tool_response.text", tool_resp["text"]))
                                        # Format 2: Message content
                                        if "message" in tool_resp:
                                            msg_content = tool_resp["message"]
                                            if isinstance(msg_content, str):
                                                candidates.append(("step_history.tool_response.message", msg_content))
                                            elif isinstance(msg_content, dict) and "text" in msg_content:
                                                candidates.append(("step_history.tool_response.message.text", msg_content["text"]))
                                        # Format 3: Content array
                                        if "content" in tool_resp:
                                            content = tool_resp["content"]
                                            if isinstance(content, str):
                                                candidates.append(("step_history.tool_response.content", content))
                                            elif isinstance(content, list):
                                                for item in content:
                                                    if isinstance(item, dict) and item.get("type") == "text":
                                                        candidates.append(("step_history.tool_response.content[]", item.get("text")))
                                    elif isinstance(tool_resp, str):
                                        candidates.append(("step_history.tool_response", tool_resp))
    except Exception as e:
        print(f"DEBUG: ⚠️ Error parsing step_history: {e}")
    
    # Path 1: messages array (most reliable for conversational responses)
    messages = data.get("messages", [])
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content")
            if content:
                candidates.append(("messages", content))
    
    # Path 2: result.data.message.content (structured output)
    try:
        content_blocks = data.get("result", {}).get("data", {}).get("message", {}).get("content", [])
        if isinstance(content_blocks, list):
            for block in content_blocks:
                if block.get("response_type") == "text":
                    text = block.get("text")
                    if text:
                        candidates.append(("result.data.message.content", text))
    except: pass
    
    # Path 3: output.text (legacy API format)
    output = data.get("output")
    if output and isinstance(output, dict):
        output_text = output.get("text")
        if output_text:
            candidates.append(("output.text", output_text))
    
    # Path 4: result.output (alternative format)
    result = data.get("result")
    if result and isinstance(result, dict):
        result_output = result.get("output")
        if result_output and isinstance(result_output, str):
            candidates.append(("result.output", result_output))
    
    return candidates

@app.post("/ask")
async def ask_ai(req: AskRequest):
    """
    OPTIMIZED VERSION: Handles async Agent tool calls properly
    """
    print(f"\n{'='*60}")
    print(f"DEBUG: 💬 New question: {req.message}")
    print(f"{'='*60}\n")
    
    try:
        # 1. Get IAM Token
        print("DEBUG: 🔑 Getting IAM token...")
        tr = requests.post("https://iam.cloud.ibm.com/identity/token", 
                          data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY})
        tr.raise_for_status()
        token = tr.json()["access_token"]
        print("DEBUG: ✅ Token acquired")

        # 2. Start Agent Run
        msg_url = f"{HOST_URL}/v1/orchestrate/runs"
        headers = {
            "Authorization": f"Bearer {token}", 
            "X-IBM-Orchestrate-ID": ORCHESTRATION_ID, 
            "Content-Type": "application/json"
        }
        
        print("DEBUG: 🚀 Starting Agent run...")
        res = requests.post(msg_url, headers=headers, json={
            "message": {"role": "user", "content": req.message}, 
            "agent_id": AGENT_ID
        })
        res.raise_for_status()
        run_id = res.json().get("run_id")
        print(f"DEBUG: ✅ Run started: {run_id}")
        
        # 3. Intelligent Polling with Async Run Support
        poll_url = f"{msg_url}/{run_id}"
        IGNORABLE_PHRASES = ["A new flow has started", "flow has started", "tool is processing"]
        MAX_ATTEMPTS = 60  # 2 minutes max
        POLL_INTERVAL = 2  # seconds
        
        current_run_id = run_id
        async_depth = 0  # Track how many async jumps we've made
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            time.sleep(POLL_INTERVAL)
            
            current_url = f"{msg_url}/{current_run_id}"
            poll_resp = requests.get(current_url, headers=headers)
            poll_resp.raise_for_status()
            data = poll_resp.json()
            
            status = data.get("status", "unknown")
            result = data.get("result") or {}
            result_type = result.get("type") if isinstance(result, dict) else None
            
            print(f"DEBUG: 📊 Attempt {attempt}/{MAX_ATTEMPTS} - run_id={current_run_id[:8]}..., status={status}, type={result_type}")
            
            # 🔍 DEBUG: Print details periodically
            if attempt <= 3 or (attempt % 10 == 0):
                print(f"DEBUG: 📄 Raw JSON snapshot (first 3000 chars):")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
            
            # ⭐ CRITICAL: Check if this is an async_initiated response
            if result_type == "async_initiated" and status == "completed":
                target_run_id = data.get("result", {}).get("data", {}).get("target_run_id")
                if target_run_id and target_run_id != current_run_id:
                    print(f"DEBUG: � Async workflow detected! Switching from {current_run_id[:8]}... to target {target_run_id[:8]}...")
                    current_run_id = target_run_id
                    async_depth += 1
                    
                    if async_depth > 3:
                        print(f"DEBUG: ⚠️ Too many async jumps ({async_depth}), stopping")
                        break
                    
                    # Reset attempt counter for the new run
                    continue
            
            # Extract all possible responses
            candidates = extract_ai_response(data)
            
            if candidates:
                print(f"DEBUG: 🔍 Found {len(candidates)} response candidate(s):")
                for path, text in candidates:
                    preview = text[:80] + "..." if len(text) > 80 else text
                    print(f"  - From '{path}': {preview}")
                
                # Filter out placeholder messages
                real_responses = [
                    (path, text) for path, text in candidates 
                    if not any(phrase.lower() in text.lower() for phrase in IGNORABLE_PHRASES)
                ]
                
                if real_responses:
                    path, final_text = real_responses[-1]  # Take the last real response
                    print(f"DEBUG: ✅ Real AI response found via '{path}'!")
                    print(f"DEBUG: 📝 Preview: {final_text[:150]}...")
                    return {"response": final_text}
            
            # Handle terminal states
            if status == "completed" and result_type != "async_initiated":
                print(f"DEBUG: ⚠️ Run completed but no real response found")
                break
            elif status in ["failed", "cancelled"]:
                print(f"DEBUG: ❌ Run {status}")
                return {"response": f"The AI agent encountered an issue (Status: {status}). Please try again."}
        
        # Timeout or no response
        print(f"DEBUG: ⏰ Timeout after {MAX_ATTEMPTS} attempts")
        return {"response": "The request is taking longer than expected. Please try asking in the IBM UI or try again later."}
        
    except requests.exceptions.HTTPError as he:
        print(f"ERROR: ❌ HTTP Error: {he}")
        print(f"ERROR: Response: {he.response.text if hasattr(he, 'response') else 'N/A'}")
        return {"response": f"Connection error: {str(he)}"}
    except Exception as e:
        print(f"ERROR: ❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"response": "System error. Please check server logs."}

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting LoopBack AI IT Hub API...")
    print(f"📍 Knowledge Base: {KB_DIR}")
    print(f"📍 Tickets DB: {DB_FILE}")
    print(f"🤖 Watsonx Agent: {AGENT_ID}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
