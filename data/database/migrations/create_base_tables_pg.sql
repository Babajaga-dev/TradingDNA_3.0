-- Script di migrazione per creare le tabelle di base (PostgreSQL)

-- Tabella exchanges
CREATE TABLE IF NOT EXISTS exchanges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella symbols
CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    name VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10) NOT NULL,
    quote_asset VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
    UNIQUE (exchange_id, name)
);

-- Indici per symbols
CREATE INDEX IF NOT EXISTS idx_symbol_lookup ON symbols (exchange_id, name, is_active);

-- Funzione per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS
$BODY$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;

-- Trigger per aggiornare updated_at
DROP TRIGGER IF EXISTS update_symbols_timestamp ON symbols;

CREATE TRIGGER update_symbols_timestamp
    BEFORE UPDATE ON symbols
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
