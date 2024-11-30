-- Script di creazione tabelle base (PostgreSQL)

-- Funzione per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tabella exchanges
CREATE TABLE IF NOT EXISTS exchanges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    name VARCHAR(20) NOT NULL,
    base_asset VARCHAR(10) NOT NULL,
    quote_asset VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
);

-- Trigger per market_data
DROP TRIGGER IF EXISTS update_market_data_timestamp ON market_data;
CREATE TRIGGER update_market_data_timestamp
    BEFORE UPDATE ON market_data
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella populations
CREATE TABLE IF NOT EXISTS populations (
    population_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    max_size INTEGER NOT NULL,
    current_generation INTEGER DEFAULT 0,
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    diversity_score FLOAT DEFAULT 1.0,
    performance_score FLOAT DEFAULT 0.0,
    mutation_rate FLOAT NOT NULL,
    selection_pressure INTEGER NOT NULL,
    generation_interval INTEGER NOT NULL,
    diversity_threshold FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
    CHECK (max_size BETWEEN 50 AND 500),
    CHECK (mutation_rate BETWEEN 0.001 AND 0.05),
    CHECK (selection_pressure BETWEEN 1 AND 10),
    CHECK (generation_interval BETWEEN 1 AND 24),
    CHECK (diversity_threshold BETWEEN 0.5 AND 1.0),
    CHECK (status IN ('active', 'paused', 'archived'))
);

-- Trigger per populations
DROP TRIGGER IF EXISTS update_populations_timestamp ON populations;
CREATE TRIGGER update_populations_timestamp
    BEFORE UPDATE ON populations
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella chromosomes
CREATE TABLE IF NOT EXISTS chromosomes (
    chromosome_id SERIAL PRIMARY KEY,
    population_id INTEGER NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    generation INTEGER NOT NULL DEFAULT 0,
    age INTEGER NOT NULL DEFAULT 0,
    parent1_id INTEGER,
    parent2_id INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    performance_metrics JSONB,
    weight_distribution JSONB,
    last_test_date TIMESTAMP,
    test_results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (population_id) REFERENCES populations(population_id) ON DELETE CASCADE,
    FOREIGN KEY (parent1_id) REFERENCES chromosomes(chromosome_id) ON DELETE SET NULL,
    FOREIGN KEY (parent2_id) REFERENCES chromosomes(chromosome_id) ON DELETE SET NULL,
    CHECK (status IN ('active', 'testing', 'archived'))
);

-- Trigger per chromosomes
DROP TRIGGER IF EXISTS update_chromosomes_timestamp ON chromosomes;
CREATE TRIGGER update_chromosomes_timestamp
    BEFORE UPDATE ON chromosomes
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella chromosome_genes
CREATE TABLE IF NOT EXISTS chromosome_genes (
    chromosome_gene_id SERIAL PRIMARY KEY,
    chromosome_id INTEGER NOT NULL,
    gene_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    weight FLOAT NOT NULL,
    performance_contribution FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT true,
    last_mutation_date TIMESTAMP,
    mutation_history JSONB,
    validation_rules JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chromosome_id) REFERENCES chromosomes(chromosome_id) ON DELETE CASCADE,
    CHECK (weight BETWEEN 0.1 AND 5.0)
);

-- Trigger per chromosome_genes
DROP TRIGGER IF EXISTS update_chromosome_genes_timestamp ON chromosome_genes;
CREATE TRIGGER update_chromosome_genes_timestamp
    BEFORE UPDATE ON chromosome_genes
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella evolution_history
CREATE TABLE IF NOT EXISTS evolution_history (
    history_id SERIAL PRIMARY KEY,
    population_id INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    best_fitness FLOAT NOT NULL,
    avg_fitness FLOAT NOT NULL,
    diversity_metric FLOAT NOT NULL,
    mutation_rate FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generation_stats JSONB,
    mutation_stats JSONB,
    selection_stats JSONB,
    performance_breakdown JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (population_id) REFERENCES populations(population_id) ON DELETE CASCADE,
    UNIQUE (population_id, generation)
);

-- Trigger per evolution_history
DROP TRIGGER IF EXISTS update_evolution_history_timestamp ON evolution_history;
CREATE TRIGGER update_evolution_history_timestamp
    BEFORE UPDATE ON evolution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella performance_metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    total_return DOUBLE PRECISION,
    annualized_return DOUBLE PRECISION,
    volatility DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    avg_daily_volume DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
);

-- Trigger per performance_metrics
DROP TRIGGER IF EXISTS update_performance_metrics_timestamp ON performance_metrics;
CREATE TRIGGER update_performance_metrics_timestamp
    BEFORE UPDATE ON performance_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Tabella risk_metrics
CREATE TABLE IF NOT EXISTS risk_metrics (
    id SERIAL PRIMARY KEY,
    exchange_id INTEGER NOT NULL,
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    beta DOUBLE PRECISION,
    alpha DOUBLE PRECISION,
    var_95 DOUBLE PRECISION,
    var_99 DOUBLE PRECISION,
    expected_shortfall DOUBLE PRECISION,
    liquidity_ratio DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
);

-- Trigger per risk_metrics
DROP TRIGGER IF EXISTS update_risk_metrics_timestamp ON risk_metrics;
CREATE TRIGGER update_risk_metrics_timestamp
    BEFORE UPDATE ON risk_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Indici per ottimizzare le query più comuni
CREATE INDEX IF NOT EXISTS idx_market_data_lookup 
ON market_data (exchange_id, symbol_id, timeframe, timestamp);

CREATE INDEX IF NOT EXISTS idx_symbol_lookup 
ON symbols (exchange_id, name, is_active);

CREATE INDEX IF NOT EXISTS idx_population_symbol 
ON populations (symbol_id);

CREATE INDEX IF NOT EXISTS idx_population_status 
ON populations (status);

CREATE INDEX IF NOT EXISTS idx_chromosome_population 
ON chromosomes (population_id);

CREATE INDEX IF NOT EXISTS idx_chromosome_fingerprint 
ON chromosomes (fingerprint);

CREATE INDEX IF NOT EXISTS idx_chromosome_status 
ON chromosomes (status);

CREATE INDEX IF NOT EXISTS idx_gene_chromosome 
ON chromosome_genes (chromosome_id);

CREATE INDEX IF NOT EXISTS idx_gene_type 
ON chromosome_genes (gene_type);

CREATE INDEX IF NOT EXISTS idx_gene_active 
ON chromosome_genes (is_active);

CREATE INDEX IF NOT EXISTS idx_history_population 
ON evolution_history (population_id);

CREATE INDEX IF NOT EXISTS idx_history_generation 
ON evolution_history (generation);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_lookup
ON performance_metrics (exchange_id, symbol_id, timeframe, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_risk_metrics_lookup
ON risk_metrics (exchange_id, symbol_id, timeframe, start_time, end_time);
