-- DataInsight Pro - Supabase Database Setup
-- Run this SQL in your Supabase SQL Editor (https://supabase.com/dashboard/project/YOUR_PROJECT/sql)

-- 1. Create profiles table (extends Supabase Auth users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- 2. Create teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    owner_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create team members table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_email)
);

-- 4. Create token usage tracking table
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    tokens_used INTEGER NOT NULL,
    operation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create uploaded files tracking table
CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    summary TEXT
);

-- 6. Create briefings table
CREATE TABLE IF NOT EXISTS briefings (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES uploaded_files(id),
    briefing_type TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Create email threads table (for mock email/team chat)
CREATE TABLE IF NOT EXISTS email_threads (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    thread_id TEXT,
    subject TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Create email messages table
CREATE TABLE IF NOT EXISTS email_messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES email_threads(id) ON DELETE CASCADE,
    sender TEXT NOT NULL,
    recipients TEXT,
    body TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_from_user BOOLEAN DEFAULT FALSE
);

-- 9. Enable Row Level Security (RLS) on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefings ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY;

-- 10. Create RLS Policies

-- Profiles: Users can read/update their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- Allow service role to insert profiles (for registration)
CREATE POLICY "Service role can insert profiles" ON profiles
    FOR INSERT WITH CHECK (true);

-- Teams: Users can manage their own teams
CREATE POLICY "Users can view own teams" ON teams
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Users can create teams" ON teams
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Users can update own teams" ON teams
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "Users can delete own teams" ON teams
    FOR DELETE USING (auth.uid() = owner_id);

-- Team members: Team owners can manage members
CREATE POLICY "Team owners can view members" ON team_members
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM teams WHERE teams.id = team_members.team_id AND teams.owner_id = auth.uid())
    );

CREATE POLICY "Team owners can add members" ON team_members
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM teams WHERE teams.id = team_members.team_id AND teams.owner_id = auth.uid())
    );

CREATE POLICY "Team owners can remove members" ON team_members
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM teams WHERE teams.id = team_members.team_id AND teams.owner_id = auth.uid())
    );

-- Token usage: Users can view/insert their own usage
CREATE POLICY "Users can view own token usage" ON token_usage
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can log token usage" ON token_usage
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Uploaded files: Users can manage their own files
CREATE POLICY "Users can view own files" ON uploaded_files
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can upload files" ON uploaded_files
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Briefings: Users can manage their own briefings
CREATE POLICY "Users can view own briefings" ON briefings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create briefings" ON briefings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Email threads: Users can manage their own threads
CREATE POLICY "Users can view own email threads" ON email_threads
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create email threads" ON email_threads
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own email threads" ON email_threads
    FOR UPDATE USING (auth.uid() = user_id);

-- Email messages: Users can view/add messages to their threads
CREATE POLICY "Users can view messages in own threads" ON email_messages
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM email_threads WHERE email_threads.id = email_messages.thread_id AND email_threads.user_id = auth.uid())
    );

CREATE POLICY "Users can add messages to own threads" ON email_messages
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM email_threads WHERE email_threads.id = email_messages.thread_id AND email_threads.user_id = auth.uid())
    );

-- 11. Create function to auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, name)
    VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'name');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 12. Create trigger for auto-profile creation
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Done! Your Supabase database is now ready for DataInsight Pro


-- User Preferences table (for model selection, etc.)
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    pref_name TEXT NOT NULL,
    pref_value TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, pref_name)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);
