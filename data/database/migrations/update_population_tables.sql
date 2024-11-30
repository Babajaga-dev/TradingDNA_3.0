-- Aggiornamento vincoli e trigger per le tabelle delle popolazioni

-- Rimuovi vecchi vincoli
ALTER TABLE chromosome_genes DROP CONSTRAINT IF EXISTS chromosome_genes_weight_check;

-- Aggiungi nuovi vincoli
ALTER TABLE chromosome_genes ADD CONSTRAINT chromosome_genes_weight_check 
    CHECK (weight BETWEEN 0.1 AND 5.0);

-- Rimuovi vecchi trigger
DROP TRIGGER IF EXISTS update_populations_timestamp ON populations;
DROP TRIGGER IF EXISTS validate_chromosome_gene_insert ON chromosome_genes;
DROP TRIGGER IF EXISTS update_population_stats ON evolution_history;

-- Crea nuovi trigger in stile PostgreSQL
CREATE OR REPLACE FUNCTION update_populations_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_populations_timestamp
    BEFORE UPDATE ON populations
    FOR EACH ROW
    EXECUTE FUNCTION update_populations_timestamp();

CREATE OR REPLACE FUNCTION validate_chromosome_gene_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.weight < 0.1 OR NEW.weight > 5.0 THEN
        RAISE EXCEPTION 'Weight must be between 0.1 and 5.0';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_chromosome_gene_insert
    BEFORE INSERT ON chromosome_genes
    FOR EACH ROW
    EXECUTE FUNCTION validate_chromosome_gene_insert();

CREATE OR REPLACE FUNCTION update_population_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE populations 
    SET 
        current_generation = NEW.generation,
        performance_score = NEW.best_fitness,
        diversity_score = NEW.diversity_metric
    WHERE population_id = NEW.population_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_population_stats
    AFTER INSERT ON evolution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_population_stats();
