-- DataInsight Pro - Chat Tables for Team Workspace
-- Run this SQL in your Supabase SQL Editor

-- 1. User Sessions table (for Clerk auth - stores session tokens and Gmail tokens)
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    token TEXT,
    user_id TEXT NOT NULL,
    email TEXT,
    name TEXT,
    gmail_tokens TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Add gmail_tokens column if table exists but column doesn't
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS gmail_tokens TEXT;

-- 2. Chat Groups table
CREATE TABLE IF NOT EXISTS chat_groups (
    id SERIAL PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    gmail_thread_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Group Members table
CREATE TABLE IF NOT EXISTS group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES chat_groups(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(group_id, email)
);

-- 4. Chat Messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES chat_groups(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL,
    sender_email TEXT NOT NULL,
    sender_name TEXT,
    message_type TEXT DEFAULT 'text',
    content TEXT NOT NULL,
    chart_json TEXT,
    chart_title TEXT,
    gmail_message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. File Uploads table (for tracking uploaded files)
CREATE TABLE IF NOT EXISTS file_uploads (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Token Usage table
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    operation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Briefings table
CREATE TABLE IF NOT EXISTS briefings (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    briefing_type TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Teams table (for team management)
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Team Members table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_email)
);

-- Disable RLS for simplicity (since we're using Clerk auth, not Supabase auth)
-- You can enable RLS later with custom policies if needed
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_groups DISABLE ROW LEVEL SECURITY;
ALTER TABLE group_members DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE file_uploads DISABLE ROW LEVEL SECURITY;
ALTER TABLE token_usage DISABLE ROW LEVEL SECURITY;
ALTER TABLE briefings DISABLE ROW LEVEL SECURITY;
ALTER TABLE teams DISABLE ROW LEVEL SECURITY;
ALTER TABLE team_members DISABLE ROW LEVEL SECURITY;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_chat_groups_owner ON chat_groups(owner_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_email ON group_members(email);
CREATE INDEX IF NOT EXISTS idx_chat_messages_group ON chat_messages(group_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_file_uploads_user ON file_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_briefings_user ON briefings(user_id);

-- Done! Your chat tables are ready.


-- ============================================
-- CALENDAR TABLES
-- ============================================

-- 10. Calendar Events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    event_type TEXT DEFAULT 'meeting',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    participants TEXT,
    location TEXT,
    description TEXT,
    source_message_id INTEGER,
    status TEXT DEFAULT 'confirmed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 11. Event Suggestions table (AI-suggested events pending approval)
CREATE TABLE IF NOT EXISTS event_suggestions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    event_type TEXT DEFAULT 'meeting',
    suggested_date DATE,
    suggested_time TIME,
    duration_minutes INTEGER DEFAULT 60,
    participants TEXT,
    source_message TEXT,
    confidence INTEGER DEFAULT 50,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for calendar
CREATE INDEX IF NOT EXISTS idx_calendar_events_user ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_event_suggestions_user ON event_suggestions(user_id);
CREATE INDEX IF NOT EXISTS idx_event_suggestions_status ON event_suggestions(status);

-- Disable RLS for calendar tables
ALTER TABLE calendar_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE event_suggestions DISABLE ROW LEVEL SECURITY;


-- ============================================
-- USER API KEYS TABLE
-- ============================================

-- 12. User API Keys table (encrypted storage for user's own API keys)
CREATE TABLE IF NOT EXISTS user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    key_name TEXT NOT NULL,
    key_value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, key_name)
);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user ON user_api_keys(user_id);

-- Disable RLS (using Clerk auth, not Supabase auth)
ALTER TABLE user_api_keys DISABLE ROW LEVEL SECURITY;
