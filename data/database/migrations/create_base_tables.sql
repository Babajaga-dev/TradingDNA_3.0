-- Script di migrazione per creare le tabelle di base

-- Tabella exchanges
CREATE TABLE IF NOT EXISTS exchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabella symbols
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_id INTEGER NOT NULL,
    name VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10) NOT NULL,
    quote_asset VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
    UNIQUE (exchange_id, name)
) WITHOUT ROWID;

-- Indici per symbols
CREATE INDEX IF NOT EXISTS idx_symbol_lookup ON symbols (exchange_id, name, is_active);

-- Trigger per aggiornare updated_at
CREATE TRIGGER IF NOT EXISTS update_symbols_timestamp 
AFTER UPDATE ON symbols
BEGIN
    UPDATE symbols SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
