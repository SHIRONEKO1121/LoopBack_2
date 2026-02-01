import React, { useState, useEffect } from 'react';
import { MessageSquare, ShieldCheck, Bell, Search, User, CheckCircle, Clock, Zap, CheckCircle2, Trash2, Send } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import './App.css';

const API_URL = "http://localhost:8000";

function App() {
  const [role, setRole] = useState('employee'); // 'employee' or 'admin'
  const [tickets, setTickets] = useState([]);
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: "Hello! I'm your Enterprise IT Assistant. How can I help you today?" }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let interval;
    if (role === 'admin') {
      fetchTickets();
      // Auto-refresh every 5 seconds for real-time feel
      interval = setInterval(fetchTickets, 5000);
    }
    return () => clearInterval(interval);
  }, [role]);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API_URL}/tickets`);
      console.log("Fetched tickets:", response.data);
      setTickets(response.data);
    } catch (error) {
      console.error("Fetch error:", error);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMsg = { role: 'user', content: inputValue };
    const currentInput = inputValue; // Capture value before clearing
    setChatMessages(prev => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      // Call the backend proxy which talks to watsonx
      const response = await axios.post(`${API_URL}/ask`, { message: currentInput });

      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: response.data.response }
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: "I'm having trouble connecting to the brain. Please try again later." }
      ]);
    } finally {
      setIsLoading(false);
      fetchTickets(); // Refresh tickets in case the AI created one
    }
  };

  const approveResolution = async (ticketId) => {
    const finalAnswer = document.getElementById(`draft-${ticketId}`).value;
    try {
      await axios.post(`${API_URL}/broadcast`, { ticket_id: ticketId, final_answer: finalAnswer });
      fetchTickets();
    } catch (err) {
      alert("Broadcast failed - Backend offline?");
    }
  };

  const deleteTicket = async (ticketId) => {
    if (!window.confirm("Are you sure you want to ignore and delete this ticket?")) return;
    try {
      await axios.delete(`${API_URL}/tickets/${ticketId}`);
      fetchTickets();
    } catch (err) {
      alert("Failed to delete ticket.");
    }
  };

  return (
    <div className="layout">
      <nav className="sidebar glass">
        <div className="brand">
          <div className="logo glow"><Zap size={20} fill="currentColor" /></div>
          <span>LoopBack AI</span>
        </div>

        <div className="nav-items">
          <button className={role === 'employee' ? 'active' : ''} onClick={() => setRole('employee')}>
            <User size={18} /> Employee
          </button>
          <button className={role === 'admin' ? 'active' : ''} onClick={() => setRole('admin')}>
            <ShieldCheck size={18} /> Admin
          </button>
        </div>

        <div className="sidebar-footer">
          <span>Status: Online</span>
        </div>
      </nav>

      <main className="main-content">
        <header>
          <div className="search-bar glass">
            <Search size={18} />
            <input type="text" placeholder="Search knowledge base..." />
          </div>
          <div className="header-actions">
            <Bell size={20} />
            <div className="avatar"></div>
          </div>
        </header>

        <section className="dashboard-view">
          {role === 'employee' ? (
            <div className="employee-grid">
              <div className="welcome-banner glow">
                <h1>Welcome, <span className="gradient-text">Employee</span></h1>
                <p>LoopBack AI is monitoring system health. 99.9% uptime today.</p>
              </div>

              <div className="chat-container glass">
                <div className="chat-header">
                  <h3><MessageSquare size={18} /> Smart Assistant</h3>
                  <div className="status-dot"></div>
                </div>
                <div className="messages">
                  <AnimatePresence>
                    {chatMessages.map((msg, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`message ${msg.role}`}
                      >
                        {msg.content}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {isLoading && <div className="loading-indicator">Thinking...</div>}
                </div>
                <form className="input-area" onSubmit={handleSendMessage}>
                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Type your issue here..."
                  />
                  <button type="submit" className="btn-primary"><Zap size={16} /> Send</button>
                </form>
              </div>

              <div className="stat-cards">
                <div className="card glass">
                  <Clock size={24} color="#00d2ff" />
                  <h4>Avg. Response</h4>
                  <p>1.2 mins</p>
                </div>
                <div className="card glass">
                  <CheckCircle size={24} color="#00e676" />
                  <h4>Self-Healed</h4>
                  <p>88%</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="admin-grid">
              <div className="admin-header">
                <h2>Human-in-the-Loop <span className="badge">Queue</span></h2>
                <button className="btn-ghost" onClick={fetchTickets}>Refresh</button>
              </div>

              <div className="ticket-list">
                {Object.values(
                  tickets
                    .filter(t => t.status === 'Pending')
                    .reduce((groups, ticket) => {
                      const gid = ticket.group_id || ticket.id;
                      if (!groups[gid]) groups[gid] = [];
                      groups[gid].push(ticket);
                      return groups;
                    }, {})
                ).map((group) => {
                  const mainTicket = group[0]; // Use first ticket as representative
                  const count = group.length;
                  return (
                    <motion.div
                      layout
                      key={mainTicket.id}
                      className="ticket-card glass"
                    >
                      <div className="ticket-info">
                        <span className="priority-tag">
                          {count > 1 ? `Group (${count} Users)` : 'Escalated'}
                        </span>
                        <h3>{count > 1 ? "Recurring Issue" : mainTicket.id}</h3>
                        <p className="query">"{mainTicket.query}"</p>
                        {count > 1 && (
                          <p className="sub-text" style={{ fontSize: '0.8em', opacity: 0.7 }}>
                            + {count - 1} other similar reports
                          </p>
                        )}
                      </div>
                      <div className="draft-editor">
                        <textarea id={`draft-${mainTicket.id}`} defaultValue={mainTicket.ai_draft} />
                        <div className="ticket-actions">
                          <button
                            onClick={() => approveResolution(mainTicket.id)}
                            className="btn-approve"
                          >
                            <Send size={16} /> Broadcast Fix
                          </button>
                          <button
                            onClick={() => deleteTicket(mainTicket.id)}
                            className="btn-reject"
                          >
                            <Trash2 size={16} /> Reject
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
                {tickets.filter(t => t.status === 'Pending').length === 0 && (
                  <div className="empty-state">All tickets resolved.</div>
                )}
              </div>
            </div>
          )}
        </section>
      </main>
    </div >
  );
}

export default App;
