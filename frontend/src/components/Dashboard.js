import React, { useState } from 'react';
import TeamWorkspace from './TeamWorkspace';
import Analysis from './Analysis';
import Briefings from './Briefings';
import Calendar from './Calendar';
import Settings from './Settings';
import Logo from './Logo';
import './Dashboard.css';

function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('analysis');

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="user-info">
          <div className="avatar">{user.name?.[0] || user.email[0]}</div>
          <div className="user-details">
            <h3>{user.name || user.email.split('@')[0]}</h3>
            <p>{user.email}</p>
          </div>
        </div>

        <nav className="nav-menu">
          <button 
            className={`nav-item ${activeTab === 'analysis' ? 'active' : ''}`}
            onClick={() => setActiveTab('analysis')}
          >
            📊 Analysis
          </button>
          <button 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Team Chat
          </button>
          <button 
            className={`nav-item ${activeTab === 'calendar' ? 'active' : ''}`}
            onClick={() => setActiveTab('calendar')}
          >
            📅 Calendar
          </button>
          <button 
            className={`nav-item ${activeTab === 'briefings' ? 'active' : ''}`}
            onClick={() => setActiveTab('briefings')}
          >
            📋 Briefings
          </button>
          <button 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            ⚙️ Settings
          </button>
        </nav>

        <button className="logout-btn" onClick={onLogout}>
          🚪 Logout
        </button>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <div className="header-brand">
            <Logo size={32} showText={false} variant="white" />
            <div className="header-title">
              <span className="header-name">DataInsight Pro</span>
              <span className="header-subtitle">AI-Powered Business Analytics Platform</span>
            </div>
          </div>
        </header>

        <div className="content-area">
          {/* Keep all tabs mounted but hidden to preserve state */}
          <div className={`tab-content ${activeTab === 'analysis' ? 'active' : 'hidden'}`}>
            <Analysis user={user} />
          </div>
          <div className={`tab-content ${activeTab === 'chat' ? 'active' : 'hidden'}`}>
            <TeamWorkspace user={user} />
          </div>
          <div className={`tab-content ${activeTab === 'calendar' ? 'active' : 'hidden'}`}>
            <Calendar user={user} />
          </div>
          <div className={`tab-content ${activeTab === 'briefings' ? 'active' : 'hidden'}`}>
            <Briefings user={user} />
          </div>
          <div className={`tab-content ${activeTab === 'settings' ? 'active' : 'hidden'}`}>
            <Settings user={user} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
