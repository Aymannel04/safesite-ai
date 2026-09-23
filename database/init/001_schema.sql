CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE violations (
    id SERIAL PRIMARY KEY,
    camera_id INTEGER NOT NULL REFERENCES cameras(id),
    track_id INTEGER,
    violation_type TEXT NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    evidence_uri TEXT
);
