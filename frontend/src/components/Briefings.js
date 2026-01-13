import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './Briefings.css';

function Briefings({ user }) {
  const [briefings, setBriefings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState('all');
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [generating, setGenerating] = useState(false);
  const [meetingContext, setMeetingContext] = useState('');
  const [meetingInsights, setMeetingInsights] = useState('');
  const [showMeetingForm, setShowMeetingForm] = useState(false);

  // Fetch briefings
  const fetchBriefings = useCallback(async () => {
    try {
      const params = selectedType !== 'all' ? { briefing_type: selectedType } : {};
      const response = await axios.get('/briefing/history', { params });
      setBriefings(response.data.briefings || response.data || []);
    } catch (err) {
      console.error('Failed to fetch briefings:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedType]);

  // Fetch user's files
  const fetchFiles = useCallback(async () => {
    try {
      const response = await axios.get('/user/files');
      setFiles(response.data.files || []);
    } catch (err) {
      console.error('Failed to fetch files:', err);
    }
  }, []);

  useEffect(() => {
    fetchBriefings();
    fetchFiles();
  }, [fetchBriefings, fetchFiles]);

  // Generate executive summary
  const generateExecutiveSummary = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }
    
    setGenerating(true);
    try {
      const formData = new FormData();
      formData.append('file_id', selectedFile);
      
      const response = await axios.post('/briefing/executive-summary', formData);
      
      if (response.data) {
        fetchBriefings();
        alert('Executive summary generated!');
      }
    } catch (err) {
      console.error('Failed to generate summary:', err);
      alert('Failed to generate summary: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGenerating(false);
    }
  };

  // Generate meeting prep
  const generateMeetingPrep = async () => {
    if (!meetingContext.trim()) {
      alert('Please enter meeting context');
      return;
    }
    
    setGenerating(true);
    try {
      const response = await axios.post('/briefing/meeting-prep', {
        context: meetingContext,
        insights: meetingInsights
      });
      
      if (response.data) {
        fetchBriefings();
        setShowMeetingForm(false);
        setMeetingContext('');
        setMeetingInsights('');
        alert('Meeting prep generated!');
      }
    } catch (err) {
      console.error('Failed to generate meeting prep:', err);
      alert('Failed to generate: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGenerating(false);
    }
  };

  // Delete briefing
  const deleteBriefing = async (briefingId) => {
    try {
      await axios.delete(`/briefing/${briefingId}`);
      fetchBriefings();
    } catch (err) {
      console.error('Failed to delete briefing:', err);
      alert('Failed to delete briefing: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get icon for briefing type
  const getTypeIcon = (type) => {
    switch (type) {
      case 'executive_summary': return '📋';
      case 'meeting_prep': return '📅';
      case 'data_summary': return '📊';
      default: return '📄';
    }
  };

  // Get label for briefing type
  const getTypeLabel = (type) => {
    switch (type) {
      case 'executive_summary': return 'Executive Summary';
      case 'meeting_prep': return 'Meeting Prep';
      case 'data_summary': return 'Data Summary';
      default: return type || 'Briefing';
    }
  };

  // Render briefing content
  const renderContent = (content) => {
    if (!content) return <p>No content</p>;
    
    // Parse content - handle multiple levels of JSON encoding
    let data = content;
    
    // If it's a string, try to parse it
    if (typeof data === 'string') {
      // Try parsing multiple times to handle nested JSON strings
      for (let i = 0; i < 3; i++) {
        if (typeof data !== 'string') break;
        try {
          data = JSON.parse(data);
        } catch (e) {
          break;
        }
      }
    }
    
    // If still a string after parsing attempts, display as text
    if (typeof data === 'string') {
      return <p className="briefing-text">{data}</p>;
    }
    
    // Handle {"text": "json_string"} wrapper
    if (data && typeof data === 'object' && data.text && Object.keys(data).length === 1) {
      if (typeof data.text === 'string' && data.text.startsWith('{')) {
        try {
          data = JSON.parse(data.text);
        } catch (e) {
          return <p className="briefing-text">{data.text}</p>;
        }
      } else if (typeof data.text === 'string') {
        return <p className="briefing-text">{data.text}</p>;
      }
    }
    
    // Now render based on structure
    
    // Handle headline + bullets format
    if (data && (data.headline || data.bullets)) {
      return (
        <div className="briefing-formatted">
          {data.headline && (
            <h4 className="briefing-headline">📊 {data.headline}</h4>
          )}
          {data.bullets && Array.isArray(data.bullets) && data.bullets.length > 0 && (
            <ul className="briefing-bullets">
              {data.bullets.map((bullet, i) => {
                const text = typeof bullet === 'string' ? bullet : (bullet.point || bullet.text || String(bullet));
                return <li key={i}>{text}</li>;
              })}
            </ul>
          )}
        </div>
      );
    }
    
    // Handle talking_points format
    if (data && data.talking_points && Array.isArray(data.talking_points)) {
      return (
        <div className="briefing-formatted">
          {data.meeting_focus && (
            <h4 className="briefing-headline">🎯 {data.meeting_focus}</h4>
          )}
          <div className="briefing-section">
            <h5>💬 Talking Points</h5>
            <ul className="briefing-bullets">
              {data.talking_points.map((item, i) => {
                const point = typeof item === 'string' ? item : (item.point || String(item));
                const type = typeof item === 'object' ? item.type : null;
                return (
                  <li key={i} className={type ? `point-${type}` : ''}>
                    {type && <span className="point-type">{type}</span>}
                    {point}
                  </li>
                );
              })}
            </ul>
          </div>
          {data.key_questions && Array.isArray(data.key_questions) && (
            <div className="briefing-section">
              <h5>❓ Key Questions</h5>
              <ul className="briefing-bullets questions">
                {data.key_questions.map((q, i) => (
                  <li key={i}>{typeof q === 'string' ? q : (q.question || String(q))}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }
    
    // Handle array directly
    if (Array.isArray(data)) {
      return (
        <ul className="briefing-bullets">
          {data.map((item, i) => (
            <li key={i}>{typeof item === 'string' ? item : (item.point || item.text || String(item))}</li>
          ))}
        </ul>
      );
    }
    
    // Handle other object structures
    if (data && typeof data === 'object') {
      // Check for summary wrapper
      if (data.summary) {
        return renderContent(data.summary);
      }
      
      // Render object properties
      const entries = Object.entries(data).filter(([k, v]) => v != null && !k.startsWith('_'));
      
      if (entries.length > 0) {
        return (
          <div className="briefing-formatted">
            {entries.map(([key, value], i) => {
              const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
              
              if (Array.isArray(value)) {
                return (
                  <div key={i} className="briefing-section">
                    <h5>{label}</h5>
                    <ul className="briefing-bullets">
                      {value.map((item, j) => (
                        <li key={j}>{typeof item === 'string' ? item : (item.point || item.text || String(item))}</li>
                      ))}
                    </ul>
                  </div>
                );
              }
              
              if (typeof value === 'string') {
                return (
                  <div key={i} className="briefing-field">
                    <strong>{label}:</strong> {value}
                  </div>
                );
              }
              
              return null;
            })}
          </div>
        );
      }
    }
    
    // Fallback - just show as string
    return <p className="briefing-text">{typeof data === 'object' ? JSON.stringify(data) : String(data)}</p>;
  };

  return (
    <div className="briefings-container">
      <div className="briefings-header">
        <h2>📋 Your Briefings</h2>
        <div className="filter-tabs">
          <button 
            className={selectedType === 'all' ? 'active' : ''}
            onClick={() => setSelectedType('all')}
          >
            All
          </button>
          <button 
            className={selectedType === 'executive_summary' ? 'active' : ''}
            onClick={() => setSelectedType('executive_summary')}
          >
            Executive
          </button>
          <button 
            className={selectedType === 'meeting_prep' ? 'active' : ''}
            onClick={() => setSelectedType('meeting_prep')}
          >
            Meeting Prep
          </button>
          <button 
            className={selectedType === 'data_summary' ? 'active' : ''}
            onClick={() => setSelectedType('data_summary')}
          >
            Data Summary
          </button>
        </div>
      </div>

      {/* Generate New Briefing Section */}
      <div className="generate-section">
        <h3>✨ Generate New Briefing</h3>
        
        <div className="generate-options">
          {/* Executive Summary */}
          <div className="generate-card">
            <h4>📋 Executive Summary</h4>
            <p>Generate a summary from your uploaded data</p>
            <select 
              value={selectedFile} 
              onChange={(e) => setSelectedFile(e.target.value)}
              className="file-select"
            >
              <option value="">Select a file...</option>
              {files.map((file, i) => (
                <option key={i} value={file.filename}>{file.filename}</option>
              ))}
            </select>
            <button 
              onClick={generateExecutiveSummary}
              disabled={generating || !selectedFile}
              className="generate-btn"
            >
              {generating ? 'Generating...' : 'Generate Summary'}
            </button>
          </div>

          {/* Meeting Prep */}
          <div className="generate-card">
            <h4>📅 Meeting Prep</h4>
            <p>Generate talking points for your meeting</p>
            <button 
              onClick={() => setShowMeetingForm(!showMeetingForm)}
              className="generate-btn secondary"
            >
              {showMeetingForm ? 'Cancel' : 'Create Meeting Prep'}
            </button>
          </div>
        </div>

        {/* Meeting Prep Form */}
        {showMeetingForm && (
          <div className="meeting-form">
            <div className="form-group">
              <label>Meeting Context</label>
              <textarea
                placeholder="Describe the meeting purpose, attendees, and goals..."
                value={meetingContext}
                onChange={(e) => setMeetingContext(e.target.value)}
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Key Insights (optional)</label>
              <textarea
                placeholder="Any data insights or points you want to discuss..."
                value={meetingInsights}
                onChange={(e) => setMeetingInsights(e.target.value)}
                rows={2}
              />
            </div>
            <button 
              onClick={generateMeetingPrep}
              disabled={generating || !meetingContext.trim()}
              className="generate-btn"
            >
              {generating ? 'Generating...' : 'Generate Meeting Prep'}
            </button>
          </div>
        )}
      </div>

      {/* Briefings List */}
      {loading ? (
        <div className="loading-state">
          <p>Loading briefings...</p>
        </div>
      ) : briefings.length > 0 ? (
        <div className="briefings-list">
          {briefings.map((briefing, index) => (
            <div key={briefing.id || index} className="briefing-card">
              <div className="briefing-header">
                <span className="briefing-icon">{getTypeIcon(briefing.briefing_type || briefing.type)}</span>
                <div className="briefing-meta">
                  <span className="briefing-type">{getTypeLabel(briefing.briefing_type || briefing.type)}</span>
                  <span className="briefing-date">{formatDate(briefing.created_at)}</span>
                </div>
                <button 
                  className="delete-briefing-btn"
                  onClick={() => {
                    if (window.confirm('Delete this briefing?')) {
                      deleteBriefing(briefing.id);
                    }
                  }}
                  title="Delete briefing"
                >
                  🗑️
                </button>
              </div>
              <div className="briefing-content">
                {renderContent(briefing.content)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <span className="empty-icon">📋</span>
          <h3>No briefings yet</h3>
          <p>Upload data in Analysis tab, then generate briefings here</p>
        </div>
      )}
    </div>
  );
}

export default Briefings;
