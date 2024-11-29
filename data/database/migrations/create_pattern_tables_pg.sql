-- Script di migrazione per creare le tabelle dei pattern

-- Tabella pattern_definitions
CREATE TABLE IF NOT EXISTS pattern_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    rules TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella pattern_instances
CREATE TABLE IF NOT EXISTS pattern_instances (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER NOT NULL,
    exchange_id INTEGER NOT NULL,
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    confidence REAL NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pattern_id) REFERENCES pattern_definitions(id),
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

-- Indici per pattern_instances
CREATE INDEX IF NOT EXISTS idx_pattern_lookup ON pattern_instances (
    exchange_id, symbol_id, pattern_id, timeframe, start_time
);
CREATE INDEX IF NOT EXISTS idx_pattern_time ON pattern_instances (start_time, end_time);
