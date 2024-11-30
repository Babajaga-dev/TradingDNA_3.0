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
import time

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('reproduction_manager')

# Configurazione retry
MAX_RETRIES = 5
RETRY_DELAY = 2.0
MAX_BACKOFF = 10.0

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    delay = min(RETRY_DELAY * (2 ** attempt) + random.random(), MAX_BACKOFF)
                    logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    time.sleep(delay)
                    continue
                raise
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class ReproductionManager(PopulationBaseManager):
    """Gestisce la riproduzione tra cromosomi."""
    
    @retry_on_db_lock
    def reproduce(self, parent1: Chromosome, parent2: Chromosome, session: Session) -> Chromosome:
        """
        Crea un nuovo cromosoma attraverso il crossover di due genitori.
        
        Args:
            parent1: Primo genitore
            parent2: Secondo genitore
            session: Sessione database attiva
            
        Returns:
            Chromosome: Nuovo cromosoma
        """
        try:
            # Debug
            logger.debug(f"[DEBUG] Inizio riproduzione")
            logger.debug(f"[DEBUG] Parent1 ID: {parent1.chromosome_id}")
            logger.debug(f"[DEBUG] Parent2 ID: {parent2.chromosome_id}")
            
            # Ricarica genitori nella sessione corrente
            parent1 = session.merge(parent1)
            parent2 = session.merge(parent2)
            
            # Crea nuovo cromosoma
            child = Chromosome(
                population_id=parent1.population_id,
                generation=parent1.population.current_generation + 1,
                parent1_id=parent1.chromosome_id,
                parent2_id=parent2.chromosome_id,
                status='active'
            )
            
            # Debug
            logger.debug(f"[DEBUG] Nuovo cromosoma creato")
            logger.debug(f"[DEBUG] Population ID: {child.population_id}")
            logger.debug(f"[DEBUG] Generation: {child.generation}")
            
            # Esegui crossover dei geni
            child_genes = self._crossover_genes(parent1, parent2)
            
            # Debug
            logger.debug(f"[DEBUG] Crossover geni completato")
            logger.debug(f"[DEBUG] Numero geni: {len(child_genes)}")
            
            # Calcola distribuzione pesi e assicura che sia serializzabile
            weight_distribution = {
                str(gene.gene_type): float(gene.weight)
                for gene in child_genes
            }
            
            # Debug
            logger.debug(f"[DEBUG] Weight distribution creata")
            logger.debug(f"[DEBUG] Weight distribution: {weight_distribution}")
            
            # Genera fingerprint
            fingerprint = self._generate_fingerprint(child_genes)
            
            # Aggiorna cromosoma
            child.fingerprint = fingerprint
            try:
                child.weight_distribution = json.dumps(weight_distribution, ensure_ascii=True)
                logger.debug(f"[DEBUG] Weight distribution serializzata con successo")
            except TypeError as e:
                logger.error(f"Errore serializzazione weight_distribution: {str(e)}")
                logger.debug(f"weight_distribution content: {weight_distribution}")
                raise
            
            # Aggiungi geni
            child.genes = child_genes
            
            # Aggiungi alla sessione
            session.add(child)
            session.flush()
            
            # Log riproduzione
            logger.info(
                f"Creato nuovo cromosoma da genitori "
                f"{parent1.chromosome_id} e {parent2.chromosome_id}"
            )
            
            return child
            
        except Exception as e:
            logger.error(f"Errore riproduzione: {str(e)}")
            raise
            
    @retry_on_db_lock
    def reproduce_batch(self, pairs: List[Tuple[Chromosome, Chromosome]], session: Session) -> List[Chromosome]:
        """
        Crea nuovi cromosomi da una lista di coppie.
        
        Args:
            pairs: Lista di coppie di genitori
            session: Sessione database attiva
            
        Returns:
            List[Chromosome]: Nuovi cromosomi
        """
        try:
            offspring = []
            
            for parent1, parent2 in pairs:
                # Crea due figli per coppia
                child1 = self.reproduce(parent1, parent2, session)
                child2 = self.reproduce(parent2, parent1, session)
                
                offspring.extend([child1, child2])
                
                # Commit intermedio ogni 10 coppie
                if len(offspring) % 20 == 0:
                    session.commit()
                
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
        
        # Debug
        logger.debug(f"[DEBUG] Inizio crossover geni")
        logger.debug(f"[DEBUG] Parent1 geni: {len(parent1.genes)}")
        logger.debug(f"[DEBUG] Parent2 geni: {len(parent2.genes)}")
        
        # Mappa geni per tipo
        p1_genes = {g.gene_type: g for g in parent1.genes}
        p2_genes = {g.gene_type: g for g in parent2.genes}
        
        # Unisci tipi di geni
        gene_types = set(p1_genes.keys()) | set(p2_genes.keys())
        
        logger.debug(f"[DEBUG] Tipi di geni trovati: {gene_types}")
        
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
                logger.debug(f"[DEBUG] Processando gene tipo: {gene_type}")
                logger.debug(f"[DEBUG] Source parameters: {source.parameters}")
                if other:
                    logger.debug(f"[DEBUG] Other parameters: {other.parameters}")
                
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
                    is_active=source.is_active,
                    mutation_history=json.dumps({}),
                    validation_rules=source.validation_rules,
                    risk_factor=self._crossover_risk_factor(
                        source.risk_factor,
                        other.risk_factor if other else None
                    )
                )
                
                child_genes.append(new_gene)
                
        logger.debug(f"[DEBUG] Crossover geni completato. Totale geni: {len(child_genes)}")
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
        try:
            logger.debug(f"[DEBUG] Inizio crossover parametri")
            logger.debug(f"[DEBUG] Params1 type: {type(params1)}")
            logger.debug(f"[DEBUG] Params1: {params1}")
            if params2:
                logger.debug(f"[DEBUG] Params2 type: {type(params2)}")
                logger.debug(f"[DEBUG] Params2: {params2}")
            
            # Se params1 è già un dict, non serve json.loads
            if isinstance(params1, dict):
                p1 = params1
            else:
                p1 = json.loads(params1)
                
            # Se params2 è già un dict o None
            if params2 is None:
                p2 = p1
            elif isinstance(params2, dict):
                p2 = params2
            else:
                p2 = json.loads(params2)
            
            logger.debug(f"[DEBUG] P1 dopo parsing: {p1}")
            logger.debug(f"[DEBUG] P2 dopo parsing: {p2}")
            
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
            
            logger.debug(f"[DEBUG] Result prima di json.dumps: {result}")
            final_result = json.dumps(result, ensure_ascii=True)
            logger.debug(f"[DEBUG] Result dopo json.dumps: {final_result}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Errore nel crossover dei parametri: {str(e)}")
            logger.debug(f"params1: {params1}")
            logger.debug(f"params2: {params2}")
            raise
        
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
            return float(w1)
            
        # Media pesata random
        r = random.random()
        return float(r * w1 + (1-r) * w2)

    def _crossover_risk_factor(self, r1: float, r2: float = None) -> float:
        """
        Esegue il crossover dei fattori di rischio.
        
        Args:
            r1: Risk factor primo genitore
            r2: Risk factor secondo genitore (opzionale)
            
        Returns:
            float: Nuovo risk factor
        """
        if r2 is None:
            return float(r1) if r1 is not None else 0.5  # Valore di default se r1 è None
            
        # Media pesata random come per i pesi
        r = random.random()
        return float(r * r1 + (1-r) * r2)
        
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
