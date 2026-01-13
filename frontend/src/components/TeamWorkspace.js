import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import './TeamWorkspace.css';

function TeamWorkspace({ user }) {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupDetails, setGroupDetails] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberName, setNewMemberName] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [gmailStatus, setGmailStatus] = useState({ connected: false, email: null });
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Check Gmail status
  const checkGmailStatus = useCallback(async () => {
    try {
      const response = await axios.get('/auth/gmail/status');
      setGmailStatus({
        connected: response.data.connected,
        email: response.data.email
      });
    } catch (err) {
      console.error('Failed to check Gmail status:', err);
    }
  }, []);

  // Connect Gmail
  const connectGmail = async () => {
    try {
      const response = await axios.get('/auth/gmail/url');
      if (response.data.auth_url) {
        // Open in new window
        window.open(response.data.auth_url, '_blank', 'width=600,height=700');
      }
    } catch (err) {
      console.error('Failed to get Gmail auth URL:', err);
      alert('Failed to connect Gmail');
    }
  };

  // Fetch groups
  const fetchGroups = useCallback(async () => {
    try {
      const response = await axios.get('/chat/groups');
      setGroups(response.data.groups || []);
    } catch (err) {
      console.error('Failed to fetch groups:', err);
    }
  }, []);

  // Fetch group details (including members)
  const fetchGroupDetails = useCallback(async () => {
    if (!selectedGroup) return;
    
    try {
      const response = await axios.get(`/chat/groups/${selectedGroup.id}`);
      setGroupDetails(response.data);
    } catch (err) {
      console.error('Failed to fetch group details:', err);
    }
  }, [selectedGroup]);

  // Fetch messages for selected group
  const fetchMessages = useCallback(async () => {
    if (!selectedGroup) return;
    
    try {
      const response = await axios.get(`/chat/groups/${selectedGroup.id}/messages`);
      setMessages(response.data.messages || []);
    } catch (err) {
      console.error('Failed to fetch messages:', err);
    }
  }, [selectedGroup]);

  // Initial load
  useEffect(() => {
    fetchGroups();
    checkGmailStatus();
  }, [fetchGroups, checkGmailStatus]);

  // Auto-refresh groups every 10 seconds (to see new groups from other users)
  useEffect(() => {
    const interval = setInterval(fetchGroups, 10000);
    return () => clearInterval(interval);
  }, [fetchGroups]);

  // Fetch messages and details when group changes
  useEffect(() => {
    if (selectedGroup) {
      fetchMessages();
      fetchGroupDetails();
    }
  }, [selectedGroup, fetchMessages, fetchGroupDetails]);

  // Auto-refresh messages every 3 seconds
  useEffect(() => {
    if (!selectedGroup) return;
    
    const interval = setInterval(fetchMessages, 3000);
    return () => clearInterval(interval);
  }, [selectedGroup, fetchMessages]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create new group
  const createGroup = async () => {
    if (!newGroupName.trim()) return;
    
    setLoading(true);
    try {
      const response = await axios.post('/chat/groups', {
        name: newGroupName,
        description: ''
      });
      
      if (response.data.success) {
        setNewGroupName('');
        setShowNewGroup(false);
        fetchGroups();
        setSelectedGroup({ id: response.data.group_id, name: newGroupName });
      }
    } catch (err) {
      console.error('Failed to create group:', err);
    } finally {
      setLoading(false);
    }
  };

  // Delete group
  const deleteGroup = async (groupId) => {
    try {
      await axios.delete(`/chat/groups/${groupId}`);
      // Clear selection if deleted group was selected
      if (selectedGroup?.id === groupId) {
        setSelectedGroup(null);
        setGroupDetails(null);
        setMessages([]);
      }
      fetchGroups();
    } catch (err) {
      console.error('Failed to delete group:', err);
      alert('Failed to delete group: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Add member to group
  const addMember = async () => {
    if (!newMemberEmail.trim() || !selectedGroup) return;
    
    setAddingMember(true);
    try {
      await axios.post(`/chat/groups/${selectedGroup.id}/members`, {
        email: newMemberEmail,
        name: newMemberName || null
      });
      
      setNewMemberEmail('');
      setNewMemberName('');
      fetchGroupDetails();
      fetchGroups();
    } catch (err) {
      console.error('Failed to add member:', err);
      alert('Failed to add member');
    } finally {
      setAddingMember(false);
    }
  };

  // Remove member from group
  const removeMember = async (email) => {
    if (!selectedGroup) return;
    
    try {
      await axios.delete(`/chat/groups/${selectedGroup.id}/members/${email}`);
      fetchGroupDetails();
      fetchGroups();
    } catch (err) {
      console.error('Failed to remove member:', err);
    }
  };

  // Send message
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedGroup || sending) return;
    
    const messageText = newMessage;
    setNewMessage('');
    setSending(true);
    
    try {
      const response = await axios.post(`/chat/groups/${selectedGroup.id}/messages`, {
        content: messageText
      });
      
      // Show email status
      if (response.data.gmail_sent) {
        console.log('✅ Message sent and emailed to group members');
      } else if (response.data.gmail_error) {
        console.log('⚠️ Message saved but email not sent:', response.data.gmail_error);
      }
      
      await fetchMessages();
      inputRef.current?.focus();
    } catch (err) {
      console.error('Failed to send message:', err);
      setNewMessage(messageText);
    } finally {
      setSending(false);
    }
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="team-workspace">
      {/* Gmail Status Banner */}
      <div className={`gmail-banner ${gmailStatus.connected ? 'connected' : 'disconnected'}`}>
        {gmailStatus.connected ? (
          <span>✅ Gmail connected: {gmailStatus.email}</span>
        ) : (
          <>
            <span>⚠️ Gmail not connected - messages won't be sent as emails</span>
            <button onClick={connectGmail} className="connect-gmail-btn">
              🔗 Connect Gmail
            </button>
            <button onClick={checkGmailStatus} className="refresh-gmail-btn">
              🔄
            </button>
          </>
        )}
      </div>

      <div className="workspace-main">
        {/* Groups Sidebar */}
        <div className="groups-panel">
        <div className="groups-header">
          <h2>💬 Chat Groups</h2>
          <button 
            className="new-group-btn"
            onClick={() => setShowNewGroup(!showNewGroup)}
          >
            {showNewGroup ? '✕' : '+'}
          </button>
        </div>

        {showNewGroup && (
          <div className="new-group-form">
            <input
              type="text"
              placeholder="Group name..."
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && createGroup()}
            />
            <button onClick={createGroup} disabled={loading}>
              {loading ? '...' : 'Create'}
            </button>
          </div>
        )}

        <div className="groups-list">
          {groups.map((group) => (
            <div
              key={group.id}
              className={`group-item ${selectedGroup?.id === group.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedGroup(group);
                setShowSettings(false);
              }}
            >
              <div className="group-icon">💬</div>
              <div className="group-info">
                <h4>{group.name}</h4>
                <p>{group.last_message || 'No messages yet'}</p>
              </div>
              {group.member_count > 0 && (
                <span className="member-count">{group.member_count}</span>
              )}
              <button 
                className="delete-group-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(`Delete "${group.name}"? This will remove all messages.`)) {
                    deleteGroup(group.id);
                  }
                }}
                title="Delete group"
              >
                🗑️
              </button>
            </div>
          ))}
          
          {groups.length === 0 && (
            <p className="no-groups">No groups yet. Create one!</p>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-panel">
        {selectedGroup ? (
          <>
            <div className="chat-header">
              <div className="chat-title">
                <h3>{selectedGroup.name}</h3>
                <span className="member-info">
                  {groupDetails?.members?.length || 0} members
                </span>
              </div>
              <div className="chat-actions">
                <button 
                  className="scan-events-btn"
                  onClick={async () => {
                    try {
                      const response = await axios.post(`/calendar/scan-messages?group_id=${selectedGroup.id}`);
                      console.log('[TeamWorkspace] Scan response:', response.data);
                      if (response.data.detected > 0) {
                        alert(`Found ${response.data.detected} potential events!\n\n${response.data.suggestions_created} suggestions created.\n\nGo to Calendar tab to review and add them.`);
                      } else {
                        alert('No scheduling events detected in recent messages.\n\nTry sending messages with dates/times like:\n• "Let\'s meet tomorrow at 3pm"\n• "Call scheduled for Monday 10am"');
                      }
                    } catch (err) {
                      console.error('Scan failed:', err);
                      alert('Failed to scan messages. Please try again.');
                    }
                  }}
                  title="Scan messages for scheduling"
                >
                  🤖 Scan for Events
                </button>
                <span className="refresh-indicator">🔄 Auto-refreshing</span>
                <button 
                  className="settings-btn"
                  onClick={() => setShowSettings(!showSettings)}
                >
                  ⚙️ Settings
                </button>
              </div>
            </div>

            {/* Settings Panel */}
            {showSettings && (
              <div className="settings-panel">
                <div className="settings-section">
                  <h4>👥 Members</h4>
                  <div className="members-list">
                    {groupDetails?.members?.map((member) => (
                      <div key={member.email} className="member-item">
                        <span className="member-avatar">
                          {(member.name || member.email)[0].toUpperCase()}
                        </span>
                        <div className="member-details">
                          <span className="member-name">{member.name || 'No name'}</span>
                          <span className="member-email">{member.email}</span>
                        </div>
                        <button 
                          className="remove-member-btn"
                          onClick={() => removeMember(member.email)}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                    {(!groupDetails?.members || groupDetails.members.length === 0) && (
                      <p className="no-members">No members yet</p>
                    )}
                  </div>
                </div>

                <div className="settings-section">
                  <h4>➕ Add Member</h4>
                  <div className="add-member-form">
                    <input
                      type="email"
                      placeholder="Email address"
                      value={newMemberEmail}
                      onChange={(e) => setNewMemberEmail(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Name (optional)"
                      value={newMemberName}
                      onChange={(e) => setNewMemberName(e.target.value)}
                    />
                    <button 
                      onClick={addMember} 
                      disabled={addingMember || !newMemberEmail.trim()}
                    >
                      {addingMember ? 'Adding...' : 'Add Member'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="messages-container">
              {messages.map((msg) => {
                const isMe = msg.sender_email === user.email;
                const hasChart = msg.type === 'chart' && msg.chart_json;
                
                return (
                  <div
                    key={msg.id}
                    className={`message ${isMe ? 'sent' : 'received'} ${hasChart ? 'has-chart' : ''}`}
                  >
                    <div className="message-bubble">
                      {!isMe && <span className="sender-name">{msg.sender_name}</span>}
                      <p>{msg.content}</p>
                      
                      {/* Render shared chart */}
                      {hasChart && (
                        <div className="shared-chart">
                          {(() => {
                            try {
                              const chartData = JSON.parse(msg.chart_json);
                              const isPieChart = chartData.data?.some(d => d.type === 'pie');
                              
                              return (
                                <Plot
                                  data={chartData.data}
                                  layout={{
                                    ...chartData.layout,
                                    autosize: true,
                                    margin: isPieChart 
                                      ? { t: 40, r: 10, b: 40, l: 10 }
                                      : { t: 40, r: 20, b: 50, l: 50 },
                                    paper_bgcolor: 'rgba(255,255,255,0.95)',
                                    plot_bgcolor: 'rgba(255,255,255,0.95)',
                                    height: isPieChart ? 320 : 280,
                                    showlegend: true,
                                    legend: isPieChart ? {
                                      orientation: 'h',
                                      y: -0.15,
                                      x: 0.5,
                                      xanchor: 'center',
                                      font: { size: 11 }
                                    } : {
                                      orientation: 'v',
                                      y: 1,
                                      x: 1.02,
                                      font: { size: 10 }
                                    }
                                  }}
                                  config={{ responsive: true, displayModeBar: false }}
                                  style={{ width: '100%', height: isPieChart ? '320px' : '280px' }}
                                />
                              );
                            } catch (e) {
                              return <p className="chart-error">Unable to display chart</p>;
                            }
                          })()}
                        </div>
                      )}
                      
                      <span className="message-time">
                        {formatTime(msg.timestamp)}
                        {msg.is_email_synced && <span title="Email sent"> ✉️</span>}
                      </span>
                    </div>
                  </div>
                );
              })}
              {messages.length === 0 && (
                <div className="no-messages">
                  <p>No messages yet. Start the conversation!</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form className="message-input" onSubmit={sendMessage}>
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                disabled={sending}
              />
              <button type="submit" disabled={sending || !newMessage.trim()}>
                {sending ? '...' : '📤 Send'}
              </button>
            </form>
          </>
        ) : (
          <div className="no-chat-selected">
            <div className="empty-state">
              <span className="empty-icon">💬</span>
              <h3>Select a chat group</h3>
              <p>Choose a group from the sidebar or create a new one</p>
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}

export default TeamWorkspace;
