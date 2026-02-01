# IBM Cloud API Key Configuration Guide

## Quick Setup (3 Steps)

### 1. Get Your API Key

**Option A: From IBM Cloud Console**
1. Go to https://cloud.ibm.com
2. Click your profile icon (top right) → **Manage** → **Access (IAM)**
3. Click **API keys** (left sidebar)
4. Copy existing key OR click **Create +** to make a new one
5. **Save the key** - you won't see it again!

**Option B: Check Your Existing Code**
Your `server.py` loads credentials from environment variables. Check if you have them saved elsewhere (email, notes, Watsonx dashboard).

### 2. Create `.env` File

In your project root (`/Users/shironeko/.gemini/antigravity/scratch/ibm-hackathon-2026/`), create a `.env` file:

```bash
# Required for ALL features
IBM_API_KEY=your-api-key-here

# Required for Agent integration (already working)
IBM_ORCHESTRATION_ID=your-orchestration-id-here
IBM_AGENT_ID=your-agent-id-here
IBM_HOST_URL=https://us-south.ml.cloud.ibm.com
```

### 3. Restart Server

```bash
# Kill old server
killall -9 python

# Start with new environment  
python server.py
```

## What Each Key Does

| Variable | Purpose | Impact if Missing |
|----------|---------|-------------------|
| `IBM_API_KEY` | Authentication for Watsonx API | ❌ No AI ticket grouping, no ask_ai |
| `IBM_ORCHESTRATION_ID` | Your Orchestrate workspace | ❌ Chat won't work |
| `IBM_AGENT_ID` | Specific agent to use | ❌ Chat won't work |

## Testing Your Setup

After adding the API key, test it:

```bash
# Test IAM token
python3 << 'EOF'
import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("IBM_API_KEY")

response = requests.post(
    "https://iam.cloud.ibm.com/identity/token",
    data={
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
)
print(f"✅ Token works!" if response.status_code == 200 else f"❌ Error: {response.status_code}")
EOF
```

## Expected Server Logs (When Working)

```
DEBUG: 🔑 Getting IAM token for AI grouping...
DEBUG: ✅ Got IAM token successfully
DEBUG: 🤖 Asking Watsonx.ai to group tickets...
DEBUG: 🤖 AI Decision: TKT-1043
DEBUG: 🔗 Linking new ticket TKT-1045 to Group TKT-1043
```

## Where to Find IDs

- **API Key**: IBM Cloud → IAM → API Keys
- **Orchestration ID**: IBM Watsonx Orchestrate → Settings → Your workspace ID
- **Agent ID**: Orchestrate → Agents → Click your agent → Copy ID from URL

## Need Help?

Once you add the API key, create two similar tickets through the frontend and check `/tmp/server_log.txt` for the grouping logs.
