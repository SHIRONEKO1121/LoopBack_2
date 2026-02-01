# LoopBack AI - Enterprise IT Support Assistant

![IBM Watsonx](https://img.shields.io/badge/IBM-Watsonx_Orchestrate-0062FF?logo=ibm)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)

> An intelligent IT support system powered by IBM Watsonx Orchestrate that combines AI-driven knowledge retrieval, automated ticket creation, and self-learning capabilities.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Agent Setup](#agent-setup)
- [Database Setup](#database-setup)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**LoopBack AI** is an enterprise IT support assistant that leverages IBM Watsonx Orchestrate to provide:

- **Intelligent Knowledge Search**: Searches through knowledge base documents (VPN guides, printer troubleshooting, laptop policies, etc.)
- **Automated Ticket Creation**: Creates support tickets when AI cannot resolve issues with high confidence
- **Self-Learning System**: Admins can update knowledge base via CSV, enabling continuous improvement
- **Multiple Interfaces**: React Portal UI, Streamlit Dashboard, and IBM Agent UI

### Key Technologies

- **AI Agent**: IBM Watsonx Orchestrate with custom agentic workflows
- **Backend**: FastAPI (Python) with async support
- **Frontend**: React 18 with Vite
- **Alternative UI**: Streamlit for admin/ticket management
- **Database**: JSON file-based storage (easily replaceable with SQL/NoSQL)
- **Tunneling**: ngrok for exposing local APIs to IBM Cloud

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                     │
├─────────────┬─────────────────┬────────────────────────────┤
│ React Portal│ Streamlit UI    │ IBM Orchestrate UI         │
│ (Port 5173) │ (Port 8501)     │ (Cloud-based)              │
└─────────────┴─────────────────┴────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend (Port 8000)                     │
├─────────────────────────────────────────────────────────────┤
│ • /tickets (GET, POST, DELETE)                              │
│ • /search_knowledge                                         │
│ • /create_ticket                                            │
│ • /ask (AI Agent Proxy)                                     │
└─────────────────────────────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│ Knowledge Base   │    │ Tickets Database     │
│ (Text/CSV files) │    │ (tickets_db.json)    │
└──────────────────┘    └──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│          IBM Watsonx Orchestrate Agent                       │
├─────────────────────────────────────────────────────────────┤
│ • Agentic Workflow with LLM decision-making                 │
│ • Custom Skills: search_knowledge, create_ticket            │
│ • Confidence scoring & branching logic                      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🤖 AI Agent Capabilities
- Natural language understanding for IT queries
- Context-aware knowledge base search
- Confidence-based decision making (threshold: 85%)
- Automatic ticket creation for unresolved issues
- User feedback collection and learning

### 🗂️ Knowledge Base
- VPN setup guides
- Printer troubleshooting
- Laptop request policies
- Hardware specifications
- Software security guidelines
- Searchable workplace IT support database (CSV)

### 🎫 Ticket Management
- Create tickets with AI-generated drafts
- View all pending tickets
- Delete resolved tickets
- Status tracking (Pending/Resolved)
- Admin broadcast solutions

### 🎨 User Interfaces
1. **React Portal** - Modern dark-themed UI with glassmorphism
2. **Streamlit Dashboard** - Quick admin view for ticket management
3. **IBM Orchestrate UI** - Native agent interaction interface

---

## 📋 Prerequisites

### Required Software
- **Python 3.10+**
- **Node.js 16+** and npm
- **Git**

### Required Accounts & Keys
- **IBM Cloud Account** (free tier works)
- **IBM Watsonx Orchestrate** instance
- **ngrok Account** (free tier works)

### Environment Variables Needed
- IBM API Key
- Orchestration ID
- Instance ID
- Agent ID
- Agent Environment ID

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/SHIRONEKO1121/LoopBack.git
cd LoopBack
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn requests python-multipart

# Or create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Streamlit Setup (Optional)

```bash
pip install streamlit pandas
```

### 5. ngrok Setup

```bash
# Install ngrok (macOS example)
brew install ngrok

# Or download from https://ngrok.com/download

# Authenticate ngrok
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

---

## ⚙️ Configuration

### 1. Update Backend Credentials

Edit `server.py` lines 28-33:

```python
# --- Credentials ---
API_KEY = "YOUR_IBM_API_KEY"
ORCHESTRATION_ID = "YOUR_ORCHESTRATION_ID"
INSTANCE_ID = "YOUR_INSTANCE_ID"
AGENT_ID = "YOUR_AGENT_ID"
HOST_URL = f"https://api.us-south.watson-orchestrate.cloud.ibm.com/instances/{INSTANCE_ID}"
```

**How to get these values:**
1. Log into [IBM Watsonx Orchestrate](https://watson-orchestrate.cloud.ibm.com)
2. Navigate to your Agent → Settings
3. Copy the Agent ID and Environment ID
4. Get API Key from IBM Cloud IAM
5. Get Orchestration ID from the instance URL

### 2. Configure Agent Skills

The agent uses two custom OpenAPI skills that need your ngrok URL:

#### a. Get your ngrok URL
```bash
ngrok http 8000
# Copy the forwarding URL (e.g., https://xxxx-xx-xx-xxx.ngrok-free.app)
```

#### b. Update `loopback_openapi.json`
Replace all instances of the ngrok URL with your own:
```json
{
  "servers": [
    {
      "url": "https://YOUR_NGROK_URL"
    }
  ]
}
```

#### c. Import Skills to IBM Orchestrate
1. Go to IBM Orchestrate → Skills → Add Skill
2. Choose "OpenAPI"
3. Upload `loopback_openapi.json`
4. Approve the imported skills:
   - `search_knowledge`
   - `create_ticket`

---

## 🏃 Running the Application

### Option A: All-in-One Setup (Recommended for Demo)

#### Terminal 1: Backend API
```bash
python server.py
# Server runs on http://0.0.0.0:8000
```

#### Terminal 2: ngrok Tunnel
```bash
ngrok http 8000
# Copy the HTTPS forwarding URL
# Update loopback_openapi.json if this is a new session
```

#### Terminal 3: React Frontend
```bash
cd frontend
npm run dev
# UI available at http://localhost:5173
```

#### Terminal 4: Streamlit Dashboard (Optional)
```bash
streamlit run app.py
# Dashboard at http://localhost:8501
```

### Option B: Production Setup

Use a process manager like `pm2` or `systemd` to run services persistently.

---

## 🤖 Agent Setup

### 1. Create Agent in IBM Orchestrate

1. Navigate to **Agents** → **Create Agent**
2. Name: `LoopBack AI`
3. Description: `Enterprise IT Support Assistant`

### 2. Design Workflow

The agent workflow includes:

```mermaid
graph TD
    A[User Query] --> B[AI Analyzes Intent]
    B --> C{Search Knowledge Base}
    C --> D[Generate Answer with Confidence Score]
    D --> E{Confidence > 85%?}
    E -->|Yes| F[Return Answer to User]
    E -->|No| G[Create Support Ticket]
    F --> H[Ask for Feedback]
    H --> I{Feedback: Yes/No?}
    I -->|Yes| J[Mark as Resolved]
    I -->|No| G
    G --> K[Ticket Created with AI Draft]
```

### 3. Configure Skills

**Skill 1: search_knowledge**
- Endpoint: `GET /search_knowledge?query={query}`
- Returns: List of matching knowledge base entries

**Skill 2: create_ticket**
- Endpoint: `POST /create_ticket`
- Body: `{"query": "...", "ai_draft": "...", "status": "Pending"}`
- Returns: Ticket ID

### 4. Set Up Workflow Nodes

1. **Input Node**: Capture user query
2. **AI Node**: Use Generative AI to analyze query and search results
3. **Branch Node**: Check if confidence > 85
4. **High Confidence Path**: Display answer, collect feedback
5. **Low Confidence Path**: Create ticket
6. **End Node**: Session complete

### 5. Publish Agent

1. Test in IBM UI preview
2. Click **Publish**
3. Select environment
4. Copy Agent ID and Environment ID for frontend integration

---

## 🗄️ Database Setup

### Current: JSON File-Based Storage

The system uses `tickets_db.json` for simplicity:

```json
[
  {
    "id": "TKT-1001",
    "query": "How to set up VPN?",
    "ai_draft": "Follow these steps...",
    "status": "Pending",
    "final_answer": null
  }
]
```

### Migrating to PostgreSQL/MySQL

1. Install database adapter:
```bash
pip install sqlalchemy psycopg2-binary  # PostgreSQL
# or
pip install sqlalchemy pymysql  # MySQL
```

2. Replace `load_db()` and `save_db()` in `server.py`:
```python
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost/loopback_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True)
    query = Column(Text)
    ai_draft = Column(Text)
    status = Column(String)
    final_answer = Column(Text, nullable=True)
```

3. Update CRUD operations to use SQLAlchemy sessions

### Knowledge Base Setup

1. **Add new knowledge**:
   - Create `.txt` files in `knowledge_base/` directory
   - Or add rows to `Workplace_IT_Support_Database.csv`

2. **Format**:
   - TXT files: Plain text with clear headings
   - CSV files: Must have headers (Issue, Solution, Category, etc.)

3. **Auto-reload**:
   - Knowledge base is searched dynamically on each query
   - No restart required after adding files

---

## 📡 API Documentation

### Tickets API

#### GET /tickets
Returns all tickets
```bash
curl http://localhost:8000/tickets
```

#### POST /tickets
Create a new ticket
```bash
curl -X POST http://localhost:8000/tickets \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "Printer not working",
    "ai_draft": "Try restarting the printer...",
    "status": "Pending"
  }'
```

#### DELETE /tickets/{ticket_id}
Delete a ticket
```bash
curl -X DELETE http://localhost:8000/tickets/TKT-1001
```

### Knowledge Base API

#### GET /search_knowledge
Search knowledge base
```bash
curl "http://localhost:8000/search_knowledge?query=VPN"
```

### Agent API

#### POST /ask
Send query to AI agent
```bash
curl -X POST http://localhost:8000/ask \\
  -H "Content-Type: application/json" \\
  -d '{"message": "How to set up VPN?"}'
```

---

## 🚢 Deployment

### Deploy to Vercel (Frontend)

```bash
cd frontend
npm run build
vercel --prod
```

### Deploy Backend to IBM Cloud Code Engine

```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Login
ibmcloud login

# Create Code Engine project
ibmcloud ce project create --name loopback-backend

# Deploy
ibmcloud ce app create --name loopback-api \\
  --image YOUR_DOCKER_IMAGE \\
  --env API_KEY=xxx --env AGENT_ID=xxx
```

### Alternative: Deploy to Heroku

```bash
# Create Procfile
echo "web: uvicorn server:app --host 0.0.0.0 --port $PORT" > Procfile

# Deploy
heroku create loopback-ai
git push heroku main
```

---

## 💡 Usage Examples

### Example 1: VPN Setup Query

**User**: "How to set up a VPN?"

**Agent Response**:
```
VPN Setup Guide (High Confidence – 92%)

Below are the steps to configure the corporate VPN (Cisco AnyConnect) 
on a Windows, macOS, or Linux machine.

[Detailed steps...]

Did this solve your problem? (Yes/No)
```

### Example 2: Low Confidence → Ticket Creation

**User**: "My laptop screen is flickering randomly"

**Agent Response**:
```
I found some related information, but I'm not entirely confident. 
I've created a support ticket for you.

Ticket ID: TKT-1025
Status: Pending
AI Draft: "Check display drivers and cable connections..."

An IT specialist will review this shortly.
```

### Example 3: Admin Updating Knowledge Base

1. Open `knowledge_base/Workplace_IT_Support_Database.csv`
2. Add row:
   ```csv
   Screen flickering,Update GPU drivers,Hardware,High
   ```
3. Save file
4. Next query about screen flickering will have higher confidence!

---

## 🐛 Troubleshooting

### Issue: Agent returns "401 Unauthorized"
**Solution**: Verify your IBM API Key is current and has Watsonx Orchestrate permissions.

```bash
# Test API key
curl -X POST "https://iam.cloud.ibm.com/identity/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey=YOUR_KEY"
```

### Issue: Skills not found in agent
**Solution**: 
1. Ensure ngrok is running
2. Test endpoint manually:
   ```bash
   curl "https://YOUR_NGROK_URL/search_knowledge?query=test"
   ```
3. Re-import OpenAPI spec in IBM Orchestrate

### Issue: Frontend can't connect to backend
**Solution**: Check CORS settings in `server.py` and ensure backend is running.

### Issue: Knowledge base not searchable
**Solution**: Verify files are in `knowledge_base/` directory and are readable.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Team

Created for **IBM Watsonx Hackathon 2026**

- **Developer**: SHIRONEKO
- **GitHub**: [@SHIRONEKO1121](https://github.com/SHIRONEKO1121)

---

## 🙏 Acknowledgments

- IBM Watsonx Orchestrate team for the powerful AI platform
- FastAPI for the excellent async web framework
- React team for the modern UI library

---

## 📞 Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/SHIRONEKO1121/LoopBack/issues)
- Check IBM Watsonx [Documentation](https://www.ibm.com/docs/en/watsonx-orchestrate)
