"""
Reproduction Manager
-----------------
Gestione della riproduzione tra cromosomi.
"""

from typing import List, Dict, Tuple
import random
import json
import hashlib
from datetime import datetime

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('reproduction_manager')

class ReproductionManager(PopulationBaseManager):
    """Gestisce la riproduzione tra cromosomi."""
    
    def reproduce(self, parent1: Chromosome, parent2: Chromosome) -> Chromosome:
        """
        Crea un nuovo cromosoma attraverso il crossover di due genitori.
        
        Args:
            parent1: Primo genitore
            parent2: Secondo genitore
            
        Returns:
            Chromosome: Nuovo cromosoma
        """
        try:
            # Crea nuovo cromosoma
            child = Chromosome(
                population_id=parent1.population_id,
                generation=parent1.population.current_generation + 1,
                parent1_id=parent1.chromosome_id,
                parent2_id=parent2.chromosome_id,
                status='active'
            )
            
            # Esegui crossover dei geni
            child_genes = self._crossover_genes(parent1, parent2)
            
            # Calcola distribuzione pesi
            weight_distribution = {
                gene.gene_type: gene.weight
                for gene in child_genes
            }
            
            # Genera fingerprint
            fingerprint = self._generate_fingerprint(child_genes)
            
            # Aggiorna cromosoma
            child.fingerprint = fingerprint
            child.weight_distribution = json.dumps(weight_distribution)
            
            # Aggiungi geni
            child.genes = child_genes
            
            # Log riproduzione
            logger.info(
                f"Creato nuovo cromosoma da genitori "
                f"{parent1.chromosome_id} e {parent2.chromosome_id}"
            )
            
            return child
            
        except Exception as e:
            logger.error(f"Errore riproduzione: {str(e)}")
            raise
            
    def reproduce_batch(self, pairs: List[Tuple[Chromosome, Chromosome]]) -> List[Chromosome]:
        """
        Crea nuovi cromosomi da una lista di coppie.
        
        Args:
            pairs: Lista di coppie di genitori
            
        Returns:
            List[Chromosome]: Nuovi cromosomi
        """
        try:
            offspring = []
            
            for parent1, parent2 in pairs:
                # Crea due figli per coppia
                child1 = self.reproduce(parent1, parent2)
                child2 = self.reproduce(parent2, parent1)
                
                offspring.extend([child1, child2])
                
            # Log batch
            logger.info(f"Creati {len(offspring)} nuovi cromosomi")
            
            return offspring
            
        except Exception as e:
            logger.error(f"Errore riproduzione batch: {str(e)}")
            raise
            
    def _crossover_genes(self, parent1: Chromosome, parent2: Chromosome) -> List[ChromosomeGene]:
        """
        Esegue il crossover dei geni tra due genitori.
        
        Args:
            parent1: Primo genitore
            parent2: Secondo genitore
            
        Returns:
            List[ChromosomeGene]: Geni del figlio
        """
        child_genes = []
        
        # Mappa geni per tipo
        p1_genes = {g.gene_type: g for g in parent1.genes}
        p2_genes = {g.gene_type: g for g in parent2.genes}
        
        # Unisci tipi di geni
        gene_types = set(p1_genes.keys()) | set(p2_genes.keys())
        
        for gene_type in gene_types:
            # Decidi da quale genitore prendere il gene
            if random.random() < 0.5:
                source = p1_genes.get(gene_type)
                other = p2_genes.get(gene_type)
            else:
                source = p2_genes.get(gene_type)
                other = p1_genes.get(gene_type)
                
            if not source:
                source = other
                
            if source:
                # Crea nuovo gene
                new_gene = ChromosomeGene(
                    gene_type=gene_type,
                    parameters=self._crossover_parameters(
                        source.parameters,
                        other.parameters if other else None
                    ),
                    weight=self._crossover_weight(
                        source.weight,
                        other.weight if other else None
                    ),
                    is_active=source.is_active
                )
                
                child_genes.append(new_gene)
                
        return child_genes
        
    def _crossover_parameters(self, params1: str, params2: str = None) -> str:
        """
        Esegue il crossover dei parametri.
        
        Args:
            params1: Parametri primo genitore
            params2: Parametri secondo genitore (opzionale)
            
        Returns:
            str: Nuovi parametri in formato JSON
        """
        p1 = json.loads(params1)
        p2 = json.loads(params2) if params2 else p1
        
        # Crossover parametro per parametro
        result = {}
        for key in set(p1.keys()) | set(p2.keys()):
            if key in p1 and key in p2:
                # Media pesata random
                w = random.random()
                if isinstance(p1[key], (int, float)) and isinstance(p2[key], (int, float)):
                    result[key] = w * p1[key] + (1-w) * p2[key]
                else:
                    result[key] = p1[key] if random.random() < 0.5 else p2[key]
            else:
                # Usa il parametro disponibile
                result[key] = p1.get(key, p2.get(key))
                
        return json.dumps(result)
        
    def _crossover_weight(self, w1: float, w2: float = None) -> float:
        """
        Esegue il crossover dei pesi.
        
        Args:
            w1: Peso primo genitore
            w2: Peso secondo genitore (opzionale)
            
        Returns:
            float: Nuovo peso
        """
        if w2 is None:
            return w1
            
        # Media pesata random
        r = random.random()
        return r * w1 + (1-r) * w2
        
    def _generate_fingerprint(self, genes: List[ChromosomeGene]) -> str:
        """
        Genera un fingerprint unico per il nuovo cromosoma.
        
        Args:
            genes: Lista dei geni
            
        Returns:
            str: Fingerprint hash
        """
        # Crea stringa rappresentativa
        gene_str = "+".join(
            f"{g.gene_type}:{g.parameters}:{g.weight}"
            for g in sorted(genes, key=lambda x: x.gene_type)
        )
        
        # Aggiungi timestamp per unicità
        timestamp = datetime.now().isoformat()
        
        # Genera hash
        return hashlib.sha256(f"{gene_str}:{timestamp}".encode()).hexdigest()
