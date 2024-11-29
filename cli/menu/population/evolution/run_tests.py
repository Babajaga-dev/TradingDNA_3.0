"""
Evolution System Tests
-------------------
Test automatizzati del sistema di evoluzione.
"""

from typing import Dict, List
import json
from datetime import datetime
from pathlib import Path
import yaml
import time
import random

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from cli.logger.log_manager import get_logger
from cli.progress.indicators import ProgressBar
from data.database.session_manager import DBSessionManager
from data.database.models.population_models import Population

# Importazioni dirette invece che dal package
from .test_population_creator import TestPopulationCreator
from .init_test_db import TestDatabaseInitializer
from .evolution_test import EvolutionTester

# Setup logger
logger = get_logger('evolution_tests')

class EvolutionSystemTester:
    """Esegue test automatizzati del sistema di evoluzione."""
    
    def __init__(self):
        """Inizializza il system tester."""
        print("[DEBUG] Inizializzazione EvolutionSystemTester")
        super().__init__()
        self.db_init = TestDatabaseInitializer()
        self.pop_creator = TestPopulationCreator()
        self.tester = EvolutionTester()
        self.test_config = self._load_test_config()
        self.db = DBSessionManager()
        print("[DEBUG] EvolutionSystemTester inizializzato")
        
    def _load_test_config(self) -> Dict:
        """Carica la configurazione dei test."""
        try:
            print("[DEBUG] Caricamento configurazione test")
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            print("[DEBUG] Configurazione test caricata")
            return config['evolution_test']
        except Exception as e:
            print(f"[DEBUG] ERRORE caricamento config: {str(e)}")
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    def _init_components(self):
        """Inizializza i componenti."""
        try:
            print("[DEBUG] Inizializzazione componenti test")
            self.db_init = TestDatabaseInitializer()
            self.pop_creator = TestPopulationCreator()
            self.tester = EvolutionTester()
            print("[DEBUG] Componenti test inizializzati")
        except Exception as e:
            print(f"[DEBUG] ERRORE inizializzazione componenti: {str(e)}")
            logger.error(f"Errore inizializzazione componenti: {str(e)}")
            raise
            
    def run_all_tests(self) -> str:
        """Esegue tutti i test del sistema."""
        start_time = time.time()
        timeout = 300  # 5 minuti timeout
        
        try:
            print("\n[DEBUG] === INIZIO TEST SISTEMA EVOLUZIONE ===")
            logger.info("Inizio test sistema evoluzione")
            
            # Lista test da eseguire
            tests = [
                self._test_database_init,
                self._test_population_creation,
                self._test_short_evolution,
                self._test_long_evolution,
                self._test_stress
            ]
            
            results = []
            
            # Progress bar
            if self.test_config['logging']['show_progress']:
                progress = ProgressBar(total=len(tests))
            
            print("[DEBUG] Apertura sessione database principale")
            # Esegui test uno alla volta con una singola sessione
            with self.db.session() as session:
                for test in tests:
                    # Verifica timeout
                    if time.time() - start_time > timeout:
                        print("[DEBUG] TIMEOUT raggiunto!")
                        raise TimeoutError("Test execution exceeded timeout limit")
                        
                    try:
                        print(f"\n[DEBUG] === INIZIO TEST: {test.__name__} ===")
                        # Inizializza componenti per ogni test
                        self._init_components()
                        
                        logger.info(f"Esecuzione test: {test.__name__}")
                        
                        # Esegui test con la sessione corrente
                        print(f"[DEBUG] Esecuzione {test.__name__}")
                        result = test(session)
                        
                        print("[DEBUG] Commit della sessione")
                        session.commit()
                        print(f"[DEBUG] Test {test.__name__} completato con successo")
                        
                        # Aggiungi un piccolo ritardo tra i test
                        time.sleep(0.5)
                        
                        results.append({
                            'name': test.__name__,
                            'status': 'PASS',
                            'result': result
                        })
                            
                    except Exception as e:
                        print(f"[DEBUG] ERRORE in {test.__name__}: {str(e)}")
                        logger.error(f"Test {test.__name__} fallito: {str(e)}")
                        print("[DEBUG] Rollback della sessione")
                        session.rollback()
                        results.append({
                            'name': test.__name__,
                            'status': 'FAIL',
                            'error': str(e)
                        })
                    finally:
                        if self.test_config['logging']['show_progress']:
                            progress.update(1)
                        print(f"[DEBUG] === FINE TEST: {test.__name__} ===\n")
            
            print("[DEBUG] Generazione report")
            # Genera report
            report = self._generate_test_report(results)
            
            # Salva report
            if self.test_config['logging']['save_report']:
                print("[DEBUG] Salvataggio report")
                self._save_report(report)
            
            print("[DEBUG] === FINE TEST SISTEMA EVOLUZIONE ===\n")
            logger.info("Test sistema completati")
            return report
            
        except TimeoutError as e:
            error_msg = f"Timeout durante l'esecuzione dei test: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Errore esecuzione test: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            logger.error(error_msg)
            return error_msg
            
    def _test_database_init(self, session: Session) -> Dict:
        """Test inizializzazione database."""
        print("[DEBUG] Test inizializzazione database")
        result = self.db_init.initialize()
        
        if "errore" in result.lower():
            print(f"[DEBUG] ERRORE inizializzazione DB: {result}")
            raise ValueError(result)
            
        print("[DEBUG] Inizializzazione database completata")
        return {
            'description': 'Inizializzazione database test',
            'result': result
        }

    def _test_population_creation(self, session: Session) -> Dict:
        print("[DEBUG] Test creazione popolazione")
        # Create population passing the current session
        population = self.pop_creator.create_test_population("test_pop_1", session)
        if not population:
            print("[DEBUG] ERRORE: Creazione popolazione fallita")
            raise ValueError("Failed to create population")
        
        # Get fresh instance from the same session
        print(f"[DEBUG] Ricarico popolazione {population.population_id}")
        population = session.get(Population, population.population_id)
        
        print(f"[DEBUG] Popolazione creata: {population.name}")
        return {
            'description': 'Test population creation',
            'population_id': population.population_id,
            'name': population.name,
            'size': population.max_size
        }

    def _test_short_evolution(self, session: Session) -> Dict:
        print("[DEBUG] Test evoluzione breve")
        # Create population passing the current session
        population = self.pop_creator.create_test_population("test_pop_2", session)
        print(f"[DEBUG] Ricarico popolazione {population.population_id}")
        population = session.get(Population, population.population_id)
        
        print(f"[DEBUG] Avvio test evoluzione per {population.name}")
        result = self.tester.run_test(population.population_id, 5, session)
        print("[DEBUG] Test evoluzione breve completato")
        return {
            'description': 'Short evolution test (5 generations)',
            'population_id': population.population_id,
            'result': result
        }

    def _test_long_evolution(self, session: Session) -> Dict:
        print("[DEBUG] Test evoluzione lunga")
        # Create population passing the current session
        population = self.pop_creator.create_test_population("test_pop_3", session)
        print(f"[DEBUG] Ricarico popolazione {population.population_id}")
        population = session.get(Population, population.population_id)
        
        print(f"[DEBUG] Avvio test evoluzione per {population.name}")
        result = self.tester.run_test(population.population_id, 20, session)
        print("[DEBUG] Test evoluzione lunga completato")
        return {
            'description': 'Long evolution test (20 generations)',
            'population_id': population.population_id,
            'result': result
        }

    def _test_stress(self, session: Session) -> Dict:
        print("[DEBUG] Test stress")
        results = []
        for i in range(3):
            print(f"[DEBUG] Creazione popolazione stress {i+1}/3")
            # Create population passing the current session
            population = self.pop_creator.create_test_population(f"stress_pop_{i}", session)
            print(f"[DEBUG] Ricarico popolazione {population.population_id}")
            population = session.get(Population, population.population_id)
            
            print(f"[DEBUG] Avvio test evoluzione per {population.name}")
            result = self.tester.run_test(population.population_id, 10, session)
            results.append({
                'population_id': population.population_id,
                'result': result
            })
            print(f"[DEBUG] Test stress {i+1}/3 completato")
        
        print("[DEBUG] Test stress completato")
        return {
            'description': 'Stress test (3 populations x 10 generations)',
            'results': results
        }
        
    def _generate_test_report(self, results: List[Dict]) -> str:
        """Genera report dei test."""
        print("[DEBUG] Generazione report test")
        total = len(results)
        passed = sum(1 for r in results if r['status'] == 'PASS')
        failed = total - passed
        
        lines = [
            "\n=== Report Test Sistema Evoluzione ===\n",
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Test Eseguiti: {total}",
            f"Passati: {passed}",
            f"Falliti: {failed}\n",
            "Dettaglio Test:"
        ]
        
        for result in results:
            lines.extend([
                f"\n{result['name']}:",
                f"Status: {result['status']}"
            ])
            
            if result['status'] == 'PASS':
                if isinstance(result['result'], dict):
                    lines.extend([
                        "Risultato:",
                        *[f"- {k}: {v}" for k, v in result['result'].items()]
                    ])
                else:
                    lines.append(f"Risultato: {result['result']}")
            else:
                lines.append(f"Errore: {result['error']}")
        
        print("[DEBUG] Report generato")
        return "\n".join(lines)
        
    def _save_report(self, report: str) -> None:
        """Salva il report su file."""
        try:
            print("[DEBUG] Salvataggio report")
            report_dir = Path(self.test_config['logging']['report_path'])
            report_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evolution_system_test_{timestamp}.txt"
            
            with open(report_dir / filename, 'w') as f:
                f.write(report)
                
            print(f"[DEBUG] Report salvato in {filename}")
            logger.info(f"Report salvato in {filename}")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE salvataggio report: {str(e)}")
            logger.error(f"Errore salvataggio report: {str(e)}")

def main():
    """Punto di ingresso principale per l'esecuzione dei test."""
    try:
        print("[DEBUG] Avvio test sistema")
        tester = EvolutionSystemTester()
        report = tester.run_all_tests()
        print(report)
    except Exception as e:
        print(f"[DEBUG] ERRORE esecuzione test: {str(e)}")
        logger.error(f"Errore esecuzione test: {str(e)}")
        print(f"Errore esecuzione test: {str(e)}")

if __name__ == '__main__':
    main()
