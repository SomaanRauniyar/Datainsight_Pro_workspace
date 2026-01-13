-- DataInsight Pro - Supabase RLS (Row Level Security) Fix
-- Run this in your Supabase SQL Editor to secure your database tables

-- ============== Enable RLS on all tables ==============

-- User authentication tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Team and collaboration tables
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- File and data tables
ALTER TABLE public.file_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.briefings ENABLE ROW LEVEL SECURITY;

-- Email and communication tables
ALTER TABLE public.email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_threads ENABLE ROW LEVEL SECURITY;

-- Calendar tables
ALTER TABLE public.calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_suggestions ENABLE ROW LEVEL SECURITY;

-- ============== Create RLS Policies ==============

-- Users table - users can only see/modify their own data
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid()::text = user_id OR auth.uid()::text = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid()::text = user_id OR auth.uid()::text = id);

-- User sessions - users can only access their own sessions
CREATE POLICY "Users can view own sessions" ON public.user_sessions
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can manage own sessions" ON public.user_sessions
    FOR ALL USING (auth.uid()::text = user_id);

-- User API keys - users can only access their own keys
CREATE POLICY "Users can manage own API keys" ON public.user_api_keys
    FOR ALL USING (auth.uid()::text = user_id);

-- User preferences - users can only access their own preferences
CREATE POLICY "Users can manage own preferences" ON public.user_preferences
    FOR ALL USING (auth.uid()::text = user_id);

-- Teams - users can view teams they belong to
CREATE POLICY "Users can view their teams" ON public.teams
    FOR SELECT USING (
        auth.uid()::text = owner_id OR 
        EXISTS (
            SELECT 1 FROM public.team_members 
            WHERE team_id = teams.id AND user_id = auth.uid()::text
        )
    );

CREATE POLICY "Users can create teams" ON public.teams
    FOR INSERT WITH CHECK (auth.uid()::text = owner_id);

CREATE POLICY "Team owners can update teams" ON public.teams
    FOR UPDATE USING (auth.uid()::text = owner_id);

-- Team members - users can view members of their teams
CREATE POLICY "Users can view team members" ON public.team_members
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.teams 
            WHERE id = team_members.team_id AND 
            (owner_id = auth.uid()::text OR 
             EXISTS (SELECT 1 FROM public.team_members tm WHERE tm.team_id = teams.id AND tm.user_id = auth.uid()::text))
        )
    );

CREATE POLICY "Team owners can manage members" ON public.team_members
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.teams 
            WHERE id = team_members.team_id AND owner_id = auth.uid()::text
        )
    );

-- Chat groups - users can view groups they belong to
CREATE POLICY "Users can view their chat groups" ON public.chat_groups
    FOR SELECT USING (
        auth.uid()::text = owner_id OR 
        EXISTS (
            SELECT 1 FROM public.group_members 
            WHERE group_id = chat_groups.id AND user_email = (
                SELECT email FROM public.users WHERE id = auth.uid()::text
            )
        )
    );

CREATE POLICY "Users can create chat groups" ON public.chat_groups
    FOR INSERT WITH CHECK (auth.uid()::text = owner_id);

CREATE POLICY "Group owners can update groups" ON public.chat_groups
    FOR UPDATE USING (auth.uid()::text = owner_id);

-- Group members - users can view members of their groups
CREATE POLICY "Users can view group members" ON public.group_members
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chat_groups 
            WHERE id = group_members.group_id AND 
            (owner_id = auth.uid()::text OR 
             EXISTS (SELECT 1 FROM public.group_members gm WHERE gm.group_id = chat_groups.id AND gm.user_email = (
                SELECT email FROM public.users WHERE id = auth.uid()::text
             )))
        )
    );

-- Chat messages - users can view messages in their groups
CREATE POLICY "Users can view group messages" ON public.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chat_groups 
            WHERE id = chat_messages.group_id AND 
            (owner_id = auth.uid()::text OR 
             EXISTS (SELECT 1 FROM public.group_members gm WHERE gm.group_id = chat_groups.id AND gm.user_email = (
                SELECT email FROM public.users WHERE id = auth.uid()::text
             )))
        )
    );

CREATE POLICY "Users can send messages to their groups" ON public.chat_messages
    FOR INSERT WITH CHECK (
        auth.uid()::text = user_id AND
        EXISTS (
            SELECT 1 FROM public.chat_groups 
            WHERE id = chat_messages.group_id AND 
            (owner_id = auth.uid()::text OR 
             EXISTS (SELECT 1 FROM public.group_members gm WHERE gm.group_id = chat_groups.id AND gm.user_email = (
                SELECT email FROM public.users WHERE id = auth.uid()::text
             )))
        )
    );

-- File uploads - users can only see their own files
CREATE POLICY "Users can view own files" ON public.file_uploads
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can upload files" ON public.file_uploads
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Token usage - users can only see their own usage
CREATE POLICY "Users can view own token usage" ON public.token_usage
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "System can log token usage" ON public.token_usage
    FOR INSERT WITH CHECK (true); -- Allow system to log usage

-- Briefings - users can only see their own briefings
CREATE POLICY "Users can view own briefings" ON public.briefings
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can create briefings" ON public.briefings
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Email messages - users can only see their own emails
CREATE POLICY "Users can view own emails" ON public.email_messages
    FOR ALL USING (auth.uid()::text = user_id);

-- Email threads - users can only see their own threads
CREATE POLICY "Users can view own email threads" ON public.email_threads
    FOR ALL USING (auth.uid()::text = user_id);

-- Calendar events - users can only see their own events
CREATE POLICY "Users can view own calendar events" ON public.calendar_events
    FOR ALL USING (auth.uid()::text = user_id);

-- Event suggestions - users can only see their own suggestions
CREATE POLICY "Users can view own event suggestions" ON public.event_suggestions
    FOR ALL USING (auth.uid()::text = user_id);

-- ============== Admin Policies (Optional) ==============

-- Allow service role (your backend) to access all data
-- This is needed for your FastAPI backend to function properly

CREATE POLICY "Service role full access" ON public.users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role sessions access" ON public.user_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role api keys access" ON public.user_api_keys
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role preferences access" ON public.user_preferences
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role teams access" ON public.teams
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role team members access" ON public.team_members
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role chat groups access" ON public.chat_groups
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role group members access" ON public.group_members
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role chat messages access" ON public.chat_messages
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role file uploads access" ON public.file_uploads
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role token usage access" ON public.token_usage
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role briefings access" ON public.briefings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role email messages access" ON public.email_messages
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role email threads access" ON public.email_threads
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role calendar events access" ON public.calendar_events
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role event suggestions access" ON public.event_suggestions
    FOR ALL USING (auth.role() = 'service_role');

-- ============== Verification Query ==============

-- Run this to verify RLS is enabled on all tables
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled,
    (SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = t.tablename) as policy_count
FROM pg_tables t
WHERE schemaname = 'public'
ORDER BY tablename;