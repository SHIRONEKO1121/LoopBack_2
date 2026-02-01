import streamlit as st
import pandas as pd
import requests
import time
import time

st.set_page_config(page_title="LoopBack Enterprise Portal", layout="wide", page_icon="🔄")

# Role Selection
role = st.sidebar.selectbox("Switch View", ["Employee Portal", "Admin Dashboard"])

if role == "Admin Dashboard":
    st.title("🔄 LoopBack Admin Dashboard")
    st.markdown("### Unresolved Tickets & AI Draft Review (HITL Queue)")
    
    # FastAPI Endpoint
    API_URL = "http://localhost:8000"

    def get_tickets():
        try:
            response = requests.get(f"{API_URL}/tickets")
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Failed to fetch tickets: {response.status_code} - {response.text}")
                return []
        except requests.exceptions.ConnectionError:
            st.error("Unable to connect to the backend service. Ensure the FastAPI server is running.")
            return []
        except Exception as e:
            st.error(f"An error occurred while fetching tickets: {e}")
            return []

    # Fetch real data from server
    if 'tickets' not in st.session_state:
        st.session_state.tickets = get_tickets()

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending Tickets", len([t for t in st.session_state.tickets if t.get("status") == "Pending"]), "+2")
    c2.metric("Resolved Today", 24)
    c3.metric("Self-Healing Rate", "88%")

    st.divider()

    # Ticket list
    for i, t in enumerate(st.session_state.tickets):
        if t.get("status") == "Pending":
            with st.expander(f"【{t.get('priority', 'Unknown')}】{t.get('id', 'N/A')} - {t.get('query', 'No query')} ({t.get('user_count', 0)} users affected)"):
                st.write(f"**User Problem:** {t.get('query', 'No query')}")
                st.info(f"**AI Shadow Draft:**\n\n{t.get('draft', 'No draft available')}")
                
                final_answer = st.text_area("Final Resolution", value=t.get('draft', ''), key=f"ans_{i}")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                if col1.button("✅ Approve & Broadcast", key=f"app_{t['id']}"):
                    with st.spinner("Broadcasting..."):
                        new_answer = st.session_state[f"ans_{i}"]
                        res = requests.post(f"{API_URL}/broadcast", json={"ticket_id": t['id'], "final_answer": new_answer})
                        if res.status_code == 200:
                            st.success(f"Broadcasted to {len(t.get('users', []))} users!")
                            st.rerun()
                        else:
                            st.error(f"Failed to broadcast: {res.status_code} - {res.text}")
                
                if col2.button("❌ Reject", key=f"rej_{t['id']}"):
                    with st.spinner("Logging rejection..."):
                        # Assuming a reject endpoint or logic exists on server
                        st.warning("Action logged.")
                st.button("🔍 Find Similar Cases", key=f"sim_{i}")

else:
    st.title("👨‍💻 LoopBack Self-Service Portal")
    st.markdown("### Smart IT Assistant (24/7 Support)")
    
    # RAG Chat Simulation
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What technical issue are you facing? (e.g., VPN issues, printer jam)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Simulated RAG Logic
            if "VPN" in prompt.upper():
                full_response = "I found a deep-dive guide for VPN issues. Please check your certificate settings. Confidence: 92% (High)"
            elif "PRINTER" in prompt.upper():
                full_response = "Connecting to the printer... Could you confirm if you are on the 3rd or 4th floor?"
            else:
                full_response = "This issue seems complex. I have escalated this to an IT Administrator. You can track the status here in real-time."
            
            for chunk in full_response.split():
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.05)
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    st.sidebar.markdown("---")
    st.sidebar.subheader("My Ticket Status")
    st.sidebar.info("🎫 TKT-1001: Under Review (AI Draft Generated)")
