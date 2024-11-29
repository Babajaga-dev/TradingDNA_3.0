-- Script di migrazione per creare la tabella market_data

CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    symbol_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    timeframe TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    sma_20 REAL,
    ema_50 REAL,
    rsi_14 REAL,
    macd REAL,
    macd_signal REAL,
    macd_hist REAL,
    bb_upper REAL,
    bb_middle REAL,
    bb_lower REAL,
    volatility REAL,
    trend_strength REAL,
    volume_ma_20 REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT true,
    validation_errors TEXT,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
    FOREIGN KEY (symbol_id) REFERENCES symbols(id),
    UNIQUE (exchange_id, symbol_id, timeframe, timestamp)
) ;

-- Indici per ottimizzazione query
CREATE INDEX IF NOT EXISTS idx_market_lookup ON market_data (exchange_id, symbol_id, timeframe, timestamp, is_valid);
CREATE INDEX IF NOT EXISTS idx_timestamp ON market_data (timestamp);
CREATE INDEX IF NOT EXISTS idx_validation ON market_data (is_valid);

-- Trigger per aggiornare updated_at
CREATE TRIGGER IF NOT EXISTS update_market_data_timestamp 
AFTER UPDATE ON market_data
BEGIN
    UPDATE market_data SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
