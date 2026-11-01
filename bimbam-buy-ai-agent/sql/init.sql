-- Schema de testing regulatorio
-- Todos los campos personales marcados como confidenciales

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT[],
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    region VARCHAR(10) DEFAULT 'latam',
    is_personal_data BOOLEAN DEFAULT false
);

CREATE TABLE api_usage_logs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    session_id VARCHAR(255)
);