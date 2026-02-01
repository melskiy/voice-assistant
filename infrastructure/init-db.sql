-- Database initialization script for voice assistant core

-- Create tables
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    state VARCHAR(50) NOT NULL,
    context_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_phone ON sessions(phone_number);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);

CREATE TABLE IF NOT EXISTS shopping_items (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    item_name VARCHAR(200) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit VARCHAR(20),
    priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shopping_session_id ON shopping_items(session_id);
CREATE INDEX IF NOT EXISTS idx_shopping_added_at ON shopping_items(added_at);

CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    reminder_date TIMESTAMP WITH TIME ZONE NOT NULL,
    location VARCHAR(200),
    repeat_interval VARCHAR(20) CHECK (repeat_interval IN ('none', 'daily', 'weekly', 'monthly')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_reminders_session_id ON reminders(session_id);
CREATE INDEX IF NOT EXISTS idx_reminders_date ON reminders(reminder_date);
CREATE INDEX IF NOT EXISTS idx_reminders_notified ON reminders(notified);

CREATE TABLE IF NOT EXISTS interaction_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    input_text TEXT,
    output_text TEXT,
    intent_name VARCHAR(100),
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interaction_session_created ON interaction_logs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_interaction_created_at ON interaction_logs(created_at);

-- Insert initial data if needed
-- (Currently empty, but can be extended with seed data)