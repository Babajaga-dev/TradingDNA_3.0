"""
Population Creator
----------------
Gestione della creazione di nuove popolazioni di trading.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
import hashlib
import json
import random
import yaml

from data.database.models.population_models import Population, Chromosome, ChromosomeGene
from .population_base import PopulationBaseManager
from cli.menu.menu_utils import get_user_input
from cli.logger.log_manager import get_logger
from cli.genes.rsi_gene import RSIGene
from cli.genes.macd_gene import MACDGene
from cli.genes.moving_average_gene import MovingAverageGene
from cli.genes.bollinger_gene import BollingerGene
from cli.genes.stochastic_gene import StochasticGene
from cli.genes.atr_gene import ATRGene

# Setup logger
logger = get_logger('population_creator')

class PopulationCreator(PopulationBaseManager):
    """Gestisce la creazione di nuove popolazioni."""
    
    def create_population(self) -> str:
        """
        Crea una nuova popolazione con configurazione base.
        
        Returns:
            str: Messaggio di conferma o errore
        """
        try:
            # Input nome popolazione
            name = get_user_input("Nome popolazione: ")
            if not name:
                return "Nome popolazione richiesto"
                
            # Input dimensione popolazione
            size_config = self.config['population']['population_size']
            size = get_user_input(
                f"Dimensione popolazione ({size_config['min']}-{size_config['max']}): ",
                validator=lambda x: size_config['min'] <= int(x) <= size_config['max'],
                error_msg="Dimensione non valida"
            )
            if not size:
                return "Dimensione popolazione richiesta"
                
            # Selezione timeframe
            timeframes = self.config['portfolio']['timeframes']
            print("\nTimeframes disponibili:")
            for i, tf in enumerate(timeframes, 1):
                print(f"{i}. {tf}")
            
            tf_choice = get_user_input(
                f"Seleziona timeframe (1-{len(timeframes)}): ",
                validator=lambda x: 1 <= int(x) <= len(timeframes),
                error_msg="Scelta non valida"
            )
            if not tf_choice:
                return "Timeframe richiesto"
                
            timeframe = timeframes[int(tf_choice)-1]
            
            # Selezione symbol
            symbols = self.config['portfolio']['symbols']
            print("\nSymbols disponibili:")
            for i, symbol in enumerate(symbols, 1):
                print(f"{i}. {symbol}")
                
            symbol_choice = get_user_input(
                f"Seleziona symbol (1-{len(symbols)}): ",
                validator=lambda x: 1 <= int(x) <= len(symbols),
                error_msg="Scelta non valida"
            )
            if not symbol_choice:
                return "Symbol richiesto"
                
            symbol = symbols[int(symbol_choice)-1]
            
            # Parametri evolutivi
            evo_config = self.config['population']['evolution']
            params = {
                'mutation_rate': evo_config['mutation_rate']['default'],
                'selection_pressure': evo_config['selection_pressure']['default'],
                'generation_interval': evo_config['generation_interval']['default'],
                'diversity_threshold': evo_config['diversity_threshold']['default']
            }
            
            # Creazione popolazione
            population = Population(
                name=name,
                max_size=int(size),
                timeframe=timeframe,
                symbol_id=self._get_symbol_id(symbol),
                **params
            )
            
            self.session.add(population)
            self.session.commit()
            
            # Log creazione
            logger.info(f"Popolazione '{name}' creata con successo")
            
            # Crea popolazione iniziale
            self._initialize_population(population)
            
            return f"Popolazione '{name}' creata e inizializzata con successo"
            
        except Exception as e:
            logger.error(f"Errore creazione popolazione: {str(e)}")
            self.session.rollback()
            return f"Errore creazione popolazione: {str(e)}"
            
    def _get_symbol_id(self, symbol_name: str) -> int:
        """
        Ottiene l'ID di un symbol dal database.
        
        Args:
            symbol_name: Nome del symbol
            
        Returns:
            int: ID del symbol
        """
        from data.database.models.models import Symbol
        symbol = self.session.query(Symbol).filter_by(name=symbol_name).first()
        if not symbol:
            raise ValueError(f"Symbol {symbol_name} non trovato")
        return symbol.id
        
    def _initialize_population(self, population: Population) -> None:
        """
        Inizializza una popolazione con cromosomi casuali.
        
        Args:
            population: Popolazione da inizializzare
        """
        try:
            for _ in range(population.max_size):
                # Crea nuovo cromosoma
                chromosome = self._create_chromosome(population)
                self.session.add(chromosome)
                
            self.session.commit()
            logger.info(f"Popolazione {population.name} inizializzata con {population.max_size} cromosomi")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione popolazione: {str(e)}")
            self.session.rollback()
            raise
            
    def _create_chromosome(self, population: Population) -> Chromosome:
        """
        Crea un nuovo cromosoma con geni casuali.
        
        Args:
            population: Popolazione di appartenenza
            
        Returns:
            Chromosome: Nuovo cromosoma
        """
        # Crea cromosoma base
        chromosome = Chromosome(
            population_id=population.population_id,
            generation=0,
            fingerprint=self._generate_fingerprint(),
            status='active'
        )
        
        # Aggiungi geni con pesi casuali
        self._add_random_genes(chromosome)
        
        return chromosome
        
    def _generate_fingerprint(self) -> str:
        """
        Genera un fingerprint unico per un cromosoma.
        
        Returns:
            str: Fingerprint hash
        """
        timestamp = datetime.now().isoformat()
        random_seed = str(hash(timestamp))
        return hashlib.sha256(f"{timestamp}{random_seed}".encode()).hexdigest()
        
    def _add_random_genes(self, chromosome: Chromosome) -> None:
        """
        Aggiunge geni casuali al cromosoma.
        
        Args:
            chromosome: Cromosoma a cui aggiungere i geni
        """
        try:
            # Carica configurazione geni
            with open('config/gene.yaml', 'r') as f:
                gene_config = yaml.safe_load(f)['gene']
            
            # Lista dei geni disponibili
            gene_classes = {
                'rsi': RSIGene,
                'macd': MACDGene,
                'moving_average': MovingAverageGene,
                'bollinger': BollingerGene,
                'stochastic': StochasticGene,
                'atr': ATRGene
            }
            
            # Seleziona un numero casuale di geni (da 2 a 5)
            num_genes = random.randint(2, 5)
            selected_genes = random.sample(list(gene_classes.items()), num_genes)
            
            for gene_name, gene_class in selected_genes:
                try:
                    # Crea istanza del gene con parametri di default
                    gene = gene_class()
                    
                    # Ottieni configurazione specifica del gene
                    gene_specific_config = gene_config.get(gene_name, {})
                    default_config = gene_specific_config.get('default', {})
                    
                    # Crea ChromosomeGene e aggiungilo alla lista dei geni del cromosoma
                    chromosome_gene = ChromosomeGene(
                        gene_type=gene_name,
                        parameters=json.dumps(gene.params),
                        weight=gene.weight,
                        is_active=True,
                        validation_rules=json.dumps(gene.constraints),
                        risk_factor=default_config.get('risk_factor', gene_config['base']['risk_factor'])
                    )
                    
                    # Usa la relazione invece dell'ID
                    chromosome.genes.append(chromosome_gene)
                    
                except Exception as e:
                    logger.error(f"Errore creazione gene {gene_name}: {str(e)}")
                    raise
                    
            logger.debug(f"Aggiunti {num_genes} geni al cromosoma {chromosome.fingerprint}")
            
        except Exception as e:
            logger.error(f"Errore aggiunta geni al cromosoma: {str(e)}")
            raise
