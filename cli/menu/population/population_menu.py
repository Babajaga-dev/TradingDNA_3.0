"""
Population Menu Manager
--------------------
Gestione del menu per le operazioni sulle popolazioni.
"""

from typing import List, Dict
from cli.menu.menu_core import create_command, create_submenu, create_separator
from cli.menu.menu_utils import get_user_input, print_table, confirm_action
from cli.logger.log_manager import setup_logging, get_logger
from .population_creator import PopulationCreator
from .population_monitor import PopulationMonitor
from .evolution.evolution_manager import EvolutionManager
from .evolution.evolution_test import EvolutionTester
from .evolution.test_population_creator import TestPopulationCreator
from .evolution.init_test_db import TestDatabaseInitializer
from .evolution.run_tests import EvolutionSystemTester

# Setup logger
logger = get_logger('population_menu')

class PopulationMenuManager:
    """Gestisce il menu delle popolazioni."""
    
    def __init__(self):
        """Inizializza il menu manager."""
        self.creator = PopulationCreator()
        self.monitor = PopulationMonitor()
        self.evolution = EvolutionManager()
        self.tester = EvolutionTester()
        self.test_creator = TestPopulationCreator()
        self.test_db = TestDatabaseInitializer()
        self.system_tester = EvolutionSystemTester()

    def _create_population(self) -> str:
        """Callback per creazione popolazione."""
        return self.creator.create_population()
        
    def _list_populations(self) -> str:
        """Callback per lista popolazioni."""
        populations = self.monitor.list_populations()
        return self.monitor.format_table(populations)
        
    def _view_population_status(self) -> str:
        """Callback per visualizzazione stato popolazione."""
        pop_id = get_user_input(
            "ID Popolazione: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not pop_id:
            return "ID popolazione richiesto"
            
        status = self.monitor.get_population_status(int(pop_id))
        if "error" in status:
            return status["error"]
            
        # Formatta output
        output = [
            f"\n=== Status Popolazione {status['info']['nome']} ===\n",
            f"ID: {status['info']['id']}",
            f"Generazione: {status['info']['generazione']}",
            f"Età: {status['info']['età']}",
            f"Stato: {status['info']['stato']}\n",
            "Dimensione:",
            f"- Attuale: {status['dimensione']['attuale']}/{status['dimensione']['massima']}",
            f"- Attivi: {status['dimensione']['attivi']}",
            f"- In Test: {status['dimensione']['in_test']}",
            f"- Archiviati: {status['dimensione']['archiviati']}\n",
            "Performance:",
            f"- Miglior Fitness: {status['performance']['miglior_fitness']:.2f}",
            f"- Media Fitness: {status['performance']['media_fitness']:.2f}",
            f"- Trend: {status['performance']['trend']}\n",
            "Diversità:",
            f"- Indice: {status['diversità']['indice']:.2f}",
            f"- Soglia: {status['diversità']['soglia']:.2f}",
            f"- Cluster: {status['diversità']['cluster']}\n",
            "Parametri Evolutivi:",
            f"- Tasso Mutazione: {status['evoluzione']['tasso_mutazione']:.3f}",
            f"- Pressione Selezione: {status['evoluzione']['pressione_selezione']}",
            f"- Intervallo: {status['evoluzione']['intervallo']} ore"
        ]
        
        return "\n".join(output)

    def _run_system_tests(self) -> str:
        """Callback per test completo del sistema."""
        if confirm_action("Questo eseguirà una serie completa di test che potrebbero durare alcuni minuti. Continuare?"):
            return self.system_tester.run_all_tests()
        return "Test sistema annullato"
    
    def _view_chromosome_details(self) -> str:
        """Callback per visualizzazione dettagli cromosoma."""
        chr_id = get_user_input(
            "ID Cromosoma: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not chr_id:
            return "ID cromosoma richiesto"
            
        details = self.monitor.get_chromosome_details(int(chr_id))
        if "error" in details:
            return details["error"]
            
        # Formatta output
        output = [
            f"\n=== Dettagli Cromosoma {details['info']['id']} ===\n",
            f"Popolazione: {details['info']['popolazione']}",
            f"Generazione: {details['info']['generazione']}",
            f"Età: {details['info']['età']}",
            f"Stato: {details['info']['stato']}\n"
        ]
        
        # Aggiungi distribuzione geni
        if details['geni']['distribuzione']:
            output.extend([
                "Distribuzione Pesi:",
                *[f"- {gene}: {weight:.2f}" 
                  for gene, weight in details['geni']['distribuzione'].items()]
            ])
            
        # Aggiungi performance
        if details['performance']:
            output.extend([
                "\nPerformance:",
                *[f"- {metric}: {value}" 
                  for metric, value in details['performance'].items()]
            ])
            
        # Aggiungi risultati test
        if details['test']['ultimo']:
            output.extend([
                f"\nUltimo Test: {details['test']['ultimo']}",
                *[f"- {metric}: {value}" 
                  for metric, value in details['test']['risultati'].items()]
            ])
            
        return "\n".join(output)
        
    def _start_evolution(self) -> str:
        """Callback per avvio evoluzione."""
        pop_id = get_user_input(
            "ID Popolazione: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not pop_id:
            return "ID popolazione richiesto"
            
        return self.evolution.start_evolution(int(pop_id))
        
    def _stop_evolution(self) -> str:
        """Callback per stop evoluzione."""
        pop_id = get_user_input(
            "ID Popolazione: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not pop_id:
            return "ID popolazione richiesto"
            
        return self.evolution.stop_evolution(int(pop_id))
        
    def _view_evolution_status(self) -> str:
        """Callback per stato evoluzione."""
        pop_id = get_user_input(
            "ID Popolazione: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not pop_id:
            return "ID popolazione richiesto"
            
        status = self.evolution.get_evolution_status(int(pop_id))
        if "error" in status:
            return status["error"]
            
        # Formatta output
        output = [
            "\n=== Status Evoluzione ===\n",
            f"In Evoluzione: {'Sì' if status['is_evolving'] else 'No'}",
            f"Generazione: {status['generation']}",
            f"Tasso Mutazione: {status['mutation_rate']:.3f}",
            f"Pressione Selezione: {status['selection_pressure']}",
            f"Diversità: {status['diversity']:.2f}"
        ]
        
        if "best_fitness" in status:
            output.extend([
                f"\nMiglior Fitness: {status['best_fitness']:.2f}",
                f"Media Fitness: {status['avg_fitness']:.2f}"
            ])
            
        if "stats" in status:
            if status["stats"]["generation"]:
                output.extend([
                    "\nStatistiche Generazione:",
                    *[f"- {k}: {v}" 
                      for k, v in status["stats"]["generation"].items()]
                ])
                
            if status["stats"]["mutation"]:
                output.extend([
                    "\nStatistiche Mutazione:",
                    *[f"- {k}: {v}" 
                      for k, v in status["stats"]["mutation"].items()]
                ])
                
            if status["stats"]["selection"]:
                output.extend([
                    "\nStatistiche Selezione:",
                    *[f"- {k}: {v}" 
                      for k, v in status["stats"]["selection"].items()]
                ])
                
        return "\n".join(output)
        
    def _init_test_db(self) -> str:
        """Callback per inizializzazione database test."""
        if confirm_action("Questo reinizializzerà il database. Continuare?"):
            return self.test_db.initialize()
        return "Operazione annullata"
        
    def _create_test_population(self) -> str:
        """Callback per creazione popolazione test."""
        name = get_user_input(
            "Nome popolazione test (opzionale): ",
            required=False
        )
        
        try:
            population = self.test_creator.create_test_population(name)
            return f"Popolazione test '{population.name}' creata con successo (ID: {population.population_id})"
        except Exception as e:
            return f"Errore creazione popolazione test: {str(e)}"
            
    def _run_evolution_test(self) -> str:
        """Callback per test evoluzione."""
        pop_id = get_user_input(
            "ID Popolazione: ",
            validator=lambda x: x.isdigit(),
            error_msg="ID non valido"
        )
        if not pop_id:
            return "ID popolazione richiesto"
            
        generations = get_user_input(
            "Numero generazioni da testare (default 5): ",
            validator=lambda x: x.isdigit() and int(x) > 0,
            error_msg="Deve essere un numero positivo",
            default="5"
        )
        
        return self.tester.run_test(int(pop_id), int(generations))
        
    def get_menu_items(self) -> List[Dict]:
        """
        Ottiene gli elementi del menu popolazioni.
        
        Returns:
            List[Dict]: Elementi del menu
        """
        return [
            create_command(
                name="Crea Popolazione",
                callback=self._create_population,
                description="Crea una nuova popolazione"
            ),
            create_command(
                name="Lista Popolazioni",
                callback=self._list_populations,
                description="Visualizza tutte le popolazioni"
            ),
            create_separator(),
            create_command(
                name="Status Popolazione",
                callback=self._view_population_status,
                description="Visualizza stato dettagliato popolazione"
            ),
            create_command(
                name="Dettagli Cromosoma",
                callback=self._view_chromosome_details,
                description="Visualizza dettagli cromosoma"
            ),
            create_separator(),
            create_command(
                name="Avvia Evoluzione",
                callback=self._start_evolution,
                description="Avvia evoluzione popolazione"
            ),
            create_command(
                name="Ferma Evoluzione",
                callback=self._stop_evolution,
                description="Ferma evoluzione popolazione"
            ),
            create_command(
                name="Status Evoluzione",
                callback=self._view_evolution_status,
                description="Visualizza stato evoluzione"
            ),
            create_separator(),
            create_submenu(
                name="Test",
                items=[
                    create_command(
                        name="Test Sistema Completo",
                        callback=self._run_system_tests,
                        description="Esegue test completo del sistema"
                    ),
                    create_separator(),
                    create_command(
                        name="Inizializza Database Test",
                        callback=self._init_test_db,
                        description="Inizializza database per testing"
                    ),
                    create_command(
                        name="Crea Popolazione Test",
                        callback=self._create_test_population,
                        description="Crea una popolazione per testing"
                    ),
                    create_command(
                        name="Test Evoluzione",
                        callback=self._run_evolution_test,
                        description="Esegue test evoluzione su N generazioni"
                    )
                ],
                description="Funzionalità di test"
            )
        ]
