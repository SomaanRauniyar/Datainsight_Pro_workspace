import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './Calendar.css';

function Calendar({ user }) {
  const [events, setEvents] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('month'); // 'month', 'week', 'day'
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [newEvent, setNewEvent] = useState({
    title: '',
    date: '',
    time: '09:00',
    duration_minutes: 60,
    event_type: 'meeting'
  });

  // Fetch events
  const fetchEvents = useCallback(async () => {
    try {
      const response = await axios.get('/calendar/events');
      setEvents(response.data.events || []);
    } catch (err) {
      console.error('Failed to fetch events:', err);
    }
  }, []);

  // Fetch suggestions
  const fetchSuggestions = useCallback(async () => {
    try {
      console.log('[Calendar] Fetching suggestions...');
      const response = await axios.get('/calendar/suggestions');
      console.log('[Calendar] Suggestions response:', response.data);
      setSuggestions(response.data.suggestions || []);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchEvents(), fetchSuggestions()]);
      setLoading(false);
    };
    loadData();
  }, [fetchEvents, fetchSuggestions]);

  // Auto-refresh suggestions every 5 seconds to catch new ones
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSuggestions();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchSuggestions]);

  // Create event
  const createEvent = async () => {
    if (!newEvent.title || !newEvent.date) return;
    
    try {
      await axios.post('/calendar/events', newEvent);
      setShowAddEvent(false);
      setNewEvent({ title: '', date: '', time: '09:00', duration_minutes: 60, event_type: 'meeting' });
      fetchEvents();
    } catch (err) {
      console.error('Failed to create event:', err);
      alert('Failed to create event');
    }
  };

  // Delete event
  const deleteEvent = async (eventId) => {
    if (!window.confirm('Delete this event?')) return;
    
    try {
      await axios.delete(`/calendar/events/${eventId}`);
      fetchEvents();
    } catch (err) {
      console.error('Failed to delete event:', err);
    }
  };

  // Accept suggestion
  const acceptSuggestion = async (suggestionId, modifications = null) => {
    try {
      await axios.post(`/calendar/suggestions/${suggestionId}/accept`, modifications);
      fetchSuggestions();
      fetchEvents();
    } catch (err) {
      console.error('Failed to accept suggestion:', err);
    }
  };

  // Dismiss suggestion
  const dismissSuggestion = async (suggestionId) => {
    try {
      await axios.post(`/calendar/suggestions/${suggestionId}/dismiss`);
      fetchSuggestions();
    } catch (err) {
      console.error('Failed to dismiss suggestion:', err);
    }
  };

  // Get days in month
  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days = [];
    
    // Add padding for first week
    for (let i = 0; i < firstDay.getDay(); i++) {
      days.push(null);
    }
    
    // Add days
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(new Date(year, month, i));
    }
    
    return days;
  };

  // Get events for a specific date
  const getEventsForDate = (date) => {
    if (!date) return [];
    const dateStr = date.toISOString().split('T')[0];
    return events.filter(e => e.start_time?.startsWith(dateStr));
  };

  // Format time
  const formatTime = (datetime) => {
    if (!datetime) return '';
    const date = new Date(datetime);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Navigate months
  const prevMonth = () => {
    setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1, 1));
  };

  const days = getDaysInMonth(selectedDate);
  const monthName = selectedDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  if (loading) {
    return <div className="calendar-loading">Loading calendar...</div>;
  }

  return (
    <div className="calendar-container">
      {/* AI Suggestions */}
      {suggestions.length > 0 && (
        <div className="suggestions-panel">
          <div className="suggestions-header">
            <h3>🤖 AI Suggested Events</h3>
            <button className="refresh-suggestions-btn" onClick={fetchSuggestions}>
              🔄 Refresh
            </button>
          </div>
          <div className="suggestions-list">
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="suggestion-card">
                <div className="suggestion-header">
                  <span className="suggestion-type">{suggestion.event_type}</span>
                  <span className="suggestion-confidence">{suggestion.confidence}% confident</span>
                </div>
                <h4>{suggestion.title}</h4>
                <p className="suggestion-time">
                  📅 {suggestion.suggested_date} {suggestion.suggested_time && `at ${suggestion.suggested_time}`}
                </p>
                {suggestion.source_message && (
                  <p className="suggestion-source">
                    From: "{suggestion.source_message.substring(0, 50)}..."
                  </p>
                )}
                <div className="suggestion-actions">
                  <button 
                    className="accept-btn"
                    onClick={() => acceptSuggestion(suggestion.id)}
                  >
                    ✓ Add to Calendar
                  </button>
                  <button 
                    className="dismiss-btn"
                    onClick={() => dismissSuggestion(suggestion.id)}
                  >
                    ✗ Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No suggestions message - show when empty but user might expect them */}
      {suggestions.length === 0 && (
        <div className="no-suggestions-banner">
          <span>💡 No pending event suggestions. Use "Scan for Events" in Team Chat to detect scheduling from messages.</span>
          <button className="refresh-suggestions-btn" onClick={fetchSuggestions}>
            🔄 Check Again
          </button>
        </div>
      )}

      {/* Calendar Header */}
      <div className="calendar-header">
        <div className="calendar-nav">
          <button onClick={prevMonth}>←</button>
          <h2>{monthName}</h2>
          <button onClick={nextMonth}>→</button>
        </div>
        <button className="add-event-btn" onClick={() => setShowAddEvent(true)}>
          + Add Event
        </button>
      </div>

      {/* Add Event Modal */}
      {showAddEvent && (
        <div className="modal-overlay" onClick={() => setShowAddEvent(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Add New Event</h3>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={newEvent.title}
                onChange={e => setNewEvent({...newEvent, title: e.target.value})}
                placeholder="Event title"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Date</label>
                <input
                  type="date"
                  value={newEvent.date}
                  onChange={e => setNewEvent({...newEvent, date: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Time</label>
                <input
                  type="time"
                  value={newEvent.time}
                  onChange={e => setNewEvent({...newEvent, time: e.target.value})}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Duration</label>
                <select
                  value={newEvent.duration_minutes}
                  onChange={e => setNewEvent({...newEvent, duration_minutes: parseInt(e.target.value)})}
                >
                  <option value={15}>15 min</option>
                  <option value={30}>30 min</option>
                  <option value={60}>1 hour</option>
                  <option value={90}>1.5 hours</option>
                  <option value={120}>2 hours</option>
                </select>
              </div>
              <div className="form-group">
                <label>Type</label>
                <select
                  value={newEvent.event_type}
                  onChange={e => setNewEvent({...newEvent, event_type: e.target.value})}
                >
                  <option value="meeting">Meeting</option>
                  <option value="call">Call</option>
                  <option value="deadline">Deadline</option>
                  <option value="reminder">Reminder</option>
                </select>
              </div>
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setShowAddEvent(false)}>Cancel</button>
              <button className="save-btn" onClick={createEvent}>Save Event</button>
            </div>
          </div>
        </div>
      )}

      {/* Calendar Grid */}
      <div className="calendar-grid">
        <div className="calendar-weekdays">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="weekday">{day}</div>
          ))}
        </div>
        <div className="calendar-days">
          {days.map((day, index) => {
            const dayEvents = getEventsForDate(day);
            const isToday = day && day.toDateString() === new Date().toDateString();
            
            return (
              <div 
                key={index} 
                className={`calendar-day ${!day ? 'empty' : ''} ${isToday ? 'today' : ''}`}
              >
                {day && (
                  <>
                    <span className="day-number">{day.getDate()}</span>
                    <div className="day-events">
                      {dayEvents.slice(0, 3).map(event => (
                        <div 
                          key={event.id} 
                          className={`event-pill ${event.event_type}`}
                          title={`${event.title} at ${formatTime(event.start_time)}`}
                          onClick={() => deleteEvent(event.id)}
                        >
                          {event.title}
                        </div>
                      ))}
                      {dayEvents.length > 3 && (
                        <span className="more-events">+{dayEvents.length - 3} more</span>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Upcoming Events */}
      <div className="upcoming-events">
        <h3>📅 Upcoming Events</h3>
        <div className="events-list">
          {events
            .filter(e => new Date(e.start_time) >= new Date())
            .slice(0, 5)
            .map(event => (
              <div key={event.id} className="event-item">
                <div className={`event-type-badge ${event.event_type}`}>
                  {event.event_type === 'meeting' ? '👥' : 
                   event.event_type === 'call' ? '📞' : 
                   event.event_type === 'deadline' ? '⏰' : '📌'}
                </div>
                <div className="event-details">
                  <h4>{event.title}</h4>
                  <p>{new Date(event.start_time).toLocaleDateString()} at {formatTime(event.start_time)}</p>
                </div>
                <button className="delete-event-btn" onClick={() => deleteEvent(event.id)}>
                  🗑️
                </button>
              </div>
            ))}
          {events.filter(e => new Date(e.start_time) >= new Date()).length === 0 && (
            <p className="no-events">No upcoming events</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Calendar;
