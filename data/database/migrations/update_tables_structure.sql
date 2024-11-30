-- Script di aggiornamento struttura tabelle

-- Aggiorna i timestamp per includere timezone
ALTER TABLE exchanges 
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE symbols 
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE market_data 
    ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE gene_parameters 
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE populations 
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE chromosomes 
    ALTER COLUMN last_test_date TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE chromosome_genes 
    ALTER COLUMN last_mutation_date TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE evolution_history 
    ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE performance_metrics 
    ALTER COLUMN start_time TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN end_time TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
    ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

-- Aggiorna le dimensioni delle colonne VARCHAR
ALTER TABLE exchanges 
    ALTER COLUMN name TYPE VARCHAR(100);

ALTER TABLE symbols 
    ALTER COLUMN name TYPE VARCHAR(50),
    ALTER COLUMN base_asset TYPE VARCHAR(20),
    ALTER COLUMN quote_asset TYPE VARCHAR(20);

-- Aggiunge nuovi campi JSON a exchanges
ALTER TABLE exchanges 
    ADD COLUMN IF NOT EXISTS api_config JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS rate_limits JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS supported_features JSONB DEFAULT '[]';

-- Aggiunge nuovi campi JSON a symbols
ALTER TABLE symbols 
    ADD COLUMN IF NOT EXISTS trading_config JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS filters JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS limits JSONB DEFAULT '{}';

-- Aggiunge nuovi campi a market_data
ALTER TABLE market_data 
    ADD COLUMN IF NOT EXISTS technical_indicators JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS pattern_recognition JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS market_metrics JSONB DEFAULT '{}',
    ALTER COLUMN validation_errors TYPE JSONB USING validation_errors::JSONB,
    ALTER COLUMN validation_errors SET DEFAULT '[]';

-- Aggiunge nuovi campi a gene_parameters
ALTER TABLE gene_parameters 
    ADD COLUMN IF NOT EXISTS validation_rules JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS optimization_bounds JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS dependencies JSONB DEFAULT '[]';

-- Aggiunge nuovi campi a populations
ALTER TABLE populations 
    ADD COLUMN IF NOT EXISTS evolution_config JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS performance_thresholds JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS optimization_settings JSONB DEFAULT '{}',
    ALTER COLUMN max_size SET DEFAULT 100,
    ALTER COLUMN mutation_rate SET DEFAULT 0.01,
    ALTER COLUMN selection_pressure SET DEFAULT 5,
    ALTER COLUMN generation_interval SET DEFAULT 4,
    ALTER COLUMN diversity_threshold SET DEFAULT 0.7;

-- Converte e aggiunge campi a chromosomes
ALTER TABLE chromosomes 
    ALTER COLUMN performance_metrics TYPE JSONB USING COALESCE(performance_metrics::JSONB, '{}'),
    ALTER COLUMN weight_distribution TYPE JSONB USING COALESCE(weight_distribution::JSONB, '{}'),
    ALTER COLUMN test_results TYPE JSONB USING COALESCE(test_results::JSONB, '{}'),
    ADD COLUMN IF NOT EXISTS fitness_history JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS mutation_stats JSONB DEFAULT '{}',
    ALTER COLUMN age SET DEFAULT 0;

-- Converte e aggiunge campi a chromosome_genes
ALTER TABLE chromosome_genes 
    ALTER COLUMN parameters TYPE JSONB USING COALESCE(parameters::JSONB, '{}'),
    ALTER COLUMN mutation_history TYPE JSONB USING COALESCE(mutation_history::JSONB, '[]'),
    ALTER COLUMN validation_rules TYPE JSONB USING COALESCE(validation_rules::JSONB, '{}'),
    ADD COLUMN IF NOT EXISTS optimization_history JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS performance_metrics JSONB DEFAULT '{}',
    ALTER COLUMN weight SET DEFAULT 1.0;

-- Converte e aggiunge campi a evolution_history
ALTER TABLE evolution_history 
    ALTER COLUMN generation_stats TYPE JSONB USING COALESCE(generation_stats::JSONB, '{}'),
    ALTER COLUMN mutation_stats TYPE JSONB USING COALESCE(mutation_stats::JSONB, '{}'),
    ALTER COLUMN selection_stats TYPE JSONB USING COALESCE(selection_stats::JSONB, '{}'),
    ALTER COLUMN performance_breakdown TYPE JSONB USING COALESCE(performance_breakdown::JSONB, '{}'),
    ADD COLUMN IF NOT EXISTS fitness_distribution JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS population_metrics JSONB DEFAULT '{}',
    ALTER COLUMN best_fitness SET DEFAULT 0.0,
    ALTER COLUMN avg_fitness SET DEFAULT 0.0,
    ALTER COLUMN diversity_metric SET DEFAULT 1.0,
    ALTER COLUMN mutation_rate SET DEFAULT 0.01;

-- Aggiunge nuovi campi a performance_metrics
ALTER TABLE performance_metrics 
    ADD COLUMN IF NOT EXISTS risk_free_rate DOUBLE PRECISION DEFAULT 0.02,
    ADD COLUMN IF NOT EXISTS alpha DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS beta DOUBLE PRECISION DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS sortino_ratio DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS downside_volatility DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS upside_volatility DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS skewness DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS kurtosis DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS volume_trend DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS volume_volatility DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS detailed_metrics JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS risk_metrics JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS trade_statistics JSONB DEFAULT '{}',
    ALTER COLUMN total_return SET DEFAULT 0.0,
    ALTER COLUMN annualized_return SET DEFAULT 0.0,
    ALTER COLUMN sharpe_ratio SET DEFAULT 0.0,
    ALTER COLUMN max_drawdown SET DEFAULT 0.0,
    ALTER COLUMN avg_volume SET DEFAULT 0.0;

-- Aggiorna la funzione update_timestamp per usare timezone
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
