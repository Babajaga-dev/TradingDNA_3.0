-- Script di creazione tabelle base (PostgreSQL)

-- Funzione per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER 
LANGUAGE plpgsql
AS '
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE ''UTC'';
    RETURN NEW;
END;
';

-- Tabella exchanges
CREATE TABLE IF NOT EXISTS exchanges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    api_config JSONB DEFAULT '{}',
    rate_limits JSONB DEFAULT '{}',
    supported_features JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger per exchanges
DROP TRIGGER IF EXISTS update_exchanges_timestamp ON exchanges;
CREATE TRIGGER update_exchanges_timestamp
    BEFORE UPDATE ON exchanges
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella symbols
CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20) NOT NULL,
    quote_asset VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    trading_config JSONB DEFAULT '{}',
    filters JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE,
    UNIQUE (exchange_id, name)
);

-- Trigger per symbols
DROP TRIGGER IF EXISTS update_symbols_timestamp ON symbols;
CREATE TRIGGER update_symbols_timestamp
    BEFORE UPDATE ON symbols
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella market_data
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    sma_20 DOUBLE PRECISION,
    ema_50 DOUBLE PRECISION,
    rsi_14 DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_hist DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_middle DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    volatility DOUBLE PRECISION,
    trend_strength DOUBLE PRECISION,
    volume_ma_20 DOUBLE PRECISION,
    technical_indicators JSONB DEFAULT '{}',
    pattern_recognition JSONB DEFAULT '{}',
    market_metrics JSONB DEFAULT '{}',
    is_valid BOOLEAN DEFAULT true,
    validation_errors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
    UNIQUE (exchange_id, symbol_id, timeframe, timestamp)
);

-- Trigger per market_data
DROP TRIGGER IF EXISTS update_market_data_timestamp ON market_data;
CREATE TRIGGER update_market_data_timestamp
    BEFORE UPDATE ON market_data
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella gene_parameters
CREATE TABLE IF NOT EXISTS gene_parameters (
    id SERIAL PRIMARY KEY,
    gene_type VARCHAR(50) NOT NULL,
    parameter_name VARCHAR(50) NOT NULL,
    value VARCHAR(100) NOT NULL,
    validation_rules JSONB DEFAULT '{}',
    optimization_bounds JSONB DEFAULT '{}',
    dependencies JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (gene_type, parameter_name)
);

-- Trigger per gene_parameters
DROP TRIGGER IF EXISTS update_gene_parameters_timestamp ON gene_parameters;
CREATE TRIGGER update_gene_parameters_timestamp
    BEFORE UPDATE ON gene_parameters
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Indici per ottimizzare le query più comuni
CREATE INDEX IF NOT EXISTS idx_exchange_lookup 
ON exchanges (name, is_active);

CREATE INDEX IF NOT EXISTS idx_symbol_lookup 
ON symbols (exchange_id, name, is_active);

CREATE INDEX IF NOT EXISTS idx_symbol_assets
ON symbols (base_asset, quote_asset);

CREATE INDEX IF NOT EXISTS idx_market_data_lookup 
ON market_data (exchange_id, symbol_id, timeframe, timestamp, is_valid);

CREATE INDEX IF NOT EXISTS idx_market_timestamp 
ON market_data (timestamp);

CREATE INDEX IF NOT EXISTS idx_market_validation
ON market_data (is_valid);

CREATE INDEX IF NOT EXISTS idx_gene_lookup
ON gene_parameters (gene_type, parameter_name);
