-- Aggiornamento struttura tabelle

-- Converti colonne JSON in JSONB per migliore gestione JSON
ALTER TABLE chromosomes
ALTER COLUMN performance_metrics TYPE JSONB USING CASE 
    WHEN performance_metrics IS NULL THEN NULL 
    ELSE performance_metrics::jsonb 
END;

ALTER TABLE chromosomes
ALTER COLUMN weight_distribution TYPE JSONB USING CASE 
    WHEN weight_distribution IS NULL THEN NULL 
    ELSE weight_distribution::jsonb 
END;

ALTER TABLE chromosomes
ALTER COLUMN test_results TYPE JSONB USING CASE 
    WHEN test_results IS NULL THEN NULL 
    ELSE test_results::jsonb 
END;

ALTER TABLE chromosome_genes
ALTER COLUMN parameters TYPE JSONB USING CASE 
    WHEN parameters IS NULL THEN NULL 
    ELSE parameters::jsonb 
END;

ALTER TABLE chromosome_genes
ALTER COLUMN mutation_history TYPE JSONB USING CASE 
    WHEN mutation_history IS NULL THEN NULL 
    ELSE mutation_history::jsonb 
END;

ALTER TABLE chromosome_genes
ALTER COLUMN validation_rules TYPE JSONB USING CASE 
    WHEN validation_rules IS NULL THEN NULL 
    ELSE validation_rules::jsonb 
END;

ALTER TABLE evolution_history
ALTER COLUMN generation_stats TYPE JSONB USING CASE 
    WHEN generation_stats IS NULL THEN NULL 
    ELSE generation_stats::jsonb 
END;

ALTER TABLE evolution_history
ALTER COLUMN mutation_stats TYPE JSONB USING CASE 
    WHEN mutation_stats IS NULL THEN NULL 
    ELSE mutation_stats::jsonb 
END;

ALTER TABLE evolution_history
ALTER COLUMN selection_stats TYPE JSONB USING CASE 
    WHEN selection_stats IS NULL THEN NULL 
    ELSE selection_stats::jsonb 
END;

ALTER TABLE evolution_history
ALTER COLUMN performance_breakdown TYPE JSONB USING CASE 
    WHEN performance_breakdown IS NULL THEN NULL 
    ELSE performance_breakdown::jsonb 
END;
