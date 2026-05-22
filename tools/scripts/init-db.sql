-- Lira V2 — Initial Database Schema
-- 6 memory layers: identity, relationship, lore, project, episodic, technical

-- Enable pgvector extension for future vector similarity queries
CREATE EXTENSION IF NOT EXISTS vector;

-- Memory categories enum
CREATE TYPE memory_category AS ENUM (
    'identity',
    'relationship',
    'lore',
    'project',
    'episodic',
    'technical'
);

-- Merge strategy enum
CREATE TYPE merge_strategy AS ENUM (
    'create_new',
    'update_existing',
    'ignore'
);

-- Core memories table
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    category memory_category NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER NOT NULL DEFAULT 0
);

-- Indexes for retrieval
CREATE INDEX idx_memories_category ON memories (category);
CREATE INDEX idx_memories_importance ON memories (importance DESC);
CREATE INDEX idx_memories_created_at ON memories (created_at DESC);
CREATE INDEX idx_memories_metadata ON memories USING GIN (metadata);

-- Vector similarity index (HNSW for fast approximate nearest neighbor)
CREATE INDEX idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);

-- Full-text search index for keyword retrieval
CREATE INDEX idx_memories_content_fts ON memories USING GIN (to_tsvector('english', content));
CREATE INDEX idx_memories_title_fts ON memories USING GIN (to_tsvector('english', title));

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Increment access count on retrieval
CREATE OR REPLACE FUNCTION increment_access_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.access_count = OLD.access_count + 1;
    NEW.last_accessed_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Sessions table for conversation tracking
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sessions_session_id ON sessions (session_id);

-- Messages table for episodic conversation history
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session_id ON messages (session_id);
CREATE INDEX idx_messages_created_at ON messages (created_at DESC);

-- Emotional state table for persistence across sessions
CREATE TABLE emotional_state (
    id SERIAL PRIMARY KEY,
    mood VARCHAR(100),
    relationship_level INTEGER NOT NULL DEFAULT 0 CHECK (relationship_level BETWEEN 0 AND 10),
    personality_mode VARCHAR(50) NOT NULL DEFAULT 'work',
    last_interaction TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unresolved_topics JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Insert initial emotional state
INSERT INTO emotional_state (mood, relationship_level, personality_mode)
VALUES ('neutral', 0, 'work');
