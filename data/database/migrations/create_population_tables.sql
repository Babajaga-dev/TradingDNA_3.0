-- Script di migrazione per creare le tabelle delle popolazioni

-- Tabella populations
CREATE TABLE IF NOT EXISTS populations (
    population_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    max_size INTEGER NOT NULL CHECK (max_size BETWEEN 50 AND 500),
    current_generation INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    diversity_score FLOAT DEFAULT 1.0 CHECK (diversity_score BETWEEN 0.0 AND 1.0),
    performance_score FLOAT DEFAULT 0.0,
    -- Parametri evolutivi dalla configurazione
    mutation_rate FLOAT DEFAULT 0.01 CHECK (mutation_rate BETWEEN 0.001 AND 0.05),
    selection_pressure INTEGER DEFAULT 5 CHECK (selection_pressure BETWEEN 1 AND 10),
    generation_interval INTEGER DEFAULT 4 CHECK (generation_interval BETWEEN 1 AND 24),
    diversity_threshold FLOAT DEFAULT 0.7 CHECK (diversity_threshold BETWEEN 0.5 AND 1.0),
    -- Configurazione trading
    symbol_id INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

-- Tabella chromosomes
CREATE TABLE IF NOT EXISTS chromosomes (
    chromosome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    population_id INTEGER NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,  -- Hash unico del DNA
    generation INTEGER NOT NULL,
    age INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    parent1_id INTEGER,
    parent2_id INTEGER,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'testing', 'archived')),
    performance_metrics JSON,  -- Metriche dettagliate di performance
    weight_distribution JSON,  -- Distribuzione pesi dei geni
    last_test_date DATETIME,  -- Data ultimo test
    test_results JSON,        -- Risultati dettagliati dei test
    FOREIGN KEY (population_id) REFERENCES populations(population_id),
    FOREIGN KEY (parent1_id) REFERENCES chromosomes(chromosome_id),
    FOREIGN KEY (parent2_id) REFERENCES chromosomes(chromosome_id)
);

-- Tabella chromosome_genes
CREATE TABLE IF NOT EXISTS chromosome_genes (
    chromosome_gene_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chromosome_id INTEGER NOT NULL,
    gene_type VARCHAR(50) NOT NULL,
    parameters JSON NOT NULL,  -- Parametri specifici del gene
    weight FLOAT NOT NULL CHECK (weight BETWEEN 0.0 AND 1.0),
    is_active BOOLEAN DEFAULT 1,
    performance_contribution FLOAT DEFAULT 0.0,
    last_mutation_date DATETIME,  -- Data ultima mutazione
    mutation_history JSON,        -- Storia delle mutazioni
    validation_rules JSON,        -- Regole di validazione parametri
    FOREIGN KEY (chromosome_id) REFERENCES chromosomes(chromosome_id)
);

-- Tabella evolution_history
CREATE TABLE IF NOT EXISTS evolution_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    population_id INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    best_fitness FLOAT NOT NULL,
    avg_fitness FLOAT NOT NULL,
    diversity_metric FLOAT NOT NULL,
    mutation_rate FLOAT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    generation_stats JSON,         -- Statistiche dettagliate generazione
    mutation_stats JSON,           -- Statistiche mutazioni
    selection_stats JSON,          -- Statistiche selezione
    performance_breakdown JSON,    -- Breakdown performance per tipo gene
    FOREIGN KEY (population_id) REFERENCES populations(population_id)
);

-- Indici per ottimizzare le query più comuni
CREATE INDEX IF NOT EXISTS idx_population_status ON populations(status);
CREATE INDEX IF NOT EXISTS idx_population_symbol ON populations(symbol_id);
CREATE INDEX IF NOT EXISTS idx_chromosome_population ON chromosomes(population_id);
CREATE INDEX IF NOT EXISTS idx_chromosome_generation ON chromosomes(generation);
CREATE INDEX IF NOT EXISTS idx_chromosome_status ON chromosomes(status);
CREATE INDEX IF NOT EXISTS idx_chromosome_genes_type ON chromosome_genes(gene_type);
CREATE INDEX IF NOT EXISTS idx_evolution_history_population ON evolution_history(population_id);
CREATE INDEX IF NOT EXISTS idx_evolution_history_generation ON evolution_history(generation);

-- Trigger per aggiornare updated_at in populations
CREATE TRIGGER IF NOT EXISTS update_populations_timestamp 
AFTER UPDATE ON populations
BEGIN
    UPDATE populations SET updated_at = CURRENT_TIMESTAMP WHERE population_id = NEW.population_id;
END;

-- Trigger per validazione inserimento chromosome_genes
CREATE TRIGGER IF NOT EXISTS validate_chromosome_gene_insert
BEFORE INSERT ON chromosome_genes
BEGIN
    SELECT CASE 
        WHEN NEW.weight < 0 OR NEW.weight > 1 THEN
            RAISE(ABORT, 'Weight must be between 0 and 1')
    END;
END;

-- Trigger per aggiornamento statistiche popolazione
CREATE TRIGGER IF NOT EXISTS update_population_stats
AFTER INSERT ON evolution_history
BEGIN
    UPDATE populations 
    SET 
        current_generation = NEW.generation,
        performance_score = NEW.best_fitness,
        diversity_score = NEW.diversity_metric
    WHERE population_id = NEW.population_id;
END;
