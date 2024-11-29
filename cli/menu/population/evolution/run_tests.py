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
from contextlib import contextmanager
import time

from cli.logger.log_manager import get_logger
from cli.progress.indicators import ProgressBar
from .init_test_db import TestDatabaseInitializer
from .test_population_creator import TestPopulationCreator
from .evolution_test import EvolutionTester
from data.database.models.models import get_session

# Setup logger
logger = get_logger('evolution_tests')

class EvolutionSystemTester:
    """Esegue test automatizzati del sistema di evoluzione."""
    
    def __init__(self):
        """Inizializza il system tester."""
        self.test_config = self._load_test_config()
        self._init_components()
        
    def _init_components(self):
        """Inizializza i componenti con una nuova sessione."""
        try:
            self.session = get_session()
            
            # Inizializza componenti condividendo la sessione
            self.db_init = TestDatabaseInitializer()
            self.db_init.session = self.session
            
            self.pop_creator = TestPopulationCreator()
            self.pop_creator.session = self.session
            
            self.tester = EvolutionTester()
            self.tester.session = self.session
            
        except Exception as e:
            logger.error(f"Errore inizializzazione componenti: {str(e)}")
            if hasattr(self, 'session'):
                self.session.close()
            raise
            
    def _load_test_config(self) -> Dict:
        """
        Carica la configurazione dei test.
        
        Returns:
            Dict: Configurazione test
        """
        try:
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            return config['evolution_test']
        except Exception as e:
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    @contextmanager
    def _session_scope(self):
        """Context manager per gestire il ciclo di vita della sessione."""
        session = None
        try:
            session = get_session()
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
                
    def run_all_tests(self) -> str:
        """
        Esegue tutti i test del sistema.
        
        Returns:
            str: Report completo dei test
        """
        start_time = time.time()
        timeout = 300  # 5 minuti timeout
        
        try:
            logger.info("Inizio test sistema evoluzione")
            
            # Lista test da eseguire
            tests = [
                self._test_database_init,
                self._test_population_creation,
                self._test_short_evolution,
                self._test_long_evolution,
                self._test_stress
            ]
            
            # Risultati test
            results = []
            
            # Progress bar
            if self.test_config['logging']['show_progress']:
                progress = ProgressBar(total=len(tests))
            
            # Esegui test
            for test in tests:
                # Verifica timeout
                if time.time() - start_time > timeout:
                    raise TimeoutError("Test execution exceeded timeout limit")
                    
                try:
                    logger.info(f"Esecuzione test: {test.__name__}")
                    with self._session_scope() as session:
                        # Aggiorna sessione nei componenti
                        self._update_component_sessions(session)
                        
                        # Esegui test
                        result = test()
                        results.append({
                            'name': test.__name__,
                            'status': 'PASS',
                            'result': result
                        })
                        
                except Exception as e:
                    logger.error(f"Test {test.__name__} fallito: {str(e)}")
                    results.append({
                        'name': test.__name__,
                        'status': 'FAIL',
                        'error': str(e)
                    })
                finally:
                    if self.test_config['logging']['show_progress']:
                        progress.update(1)
                    
            # Genera report
            report = self._generate_test_report(results)
            
            # Salva report
            if self.test_config['logging']['save_report']:
                self._save_report(report)
            
            logger.info("Test sistema completati")
            return report
            
        except TimeoutError as e:
            error_msg = f"Timeout durante l'esecuzione dei test: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Errore esecuzione test: {str(e)}"
            logger.error(error_msg)
            return error_msg
        finally:
            # Chiudi tutte le sessioni
            self._cleanup_sessions()
            
    def _update_component_sessions(self, session):
        """Aggiorna la sessione in tutti i componenti."""
        self.db_init.session = session
        self.pop_creator.session = session
        self.tester.session = session
        
    def _cleanup_sessions(self):
        """Chiude tutte le sessioni attive."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self.db_init, 'session'):
            self.db_init.session.close()
        if hasattr(self.pop_creator, 'session'):
            self.pop_creator.session.close()
        if hasattr(self.tester, 'session'):
            self.tester.session.close()
            
    def _test_database_init(self) -> Dict:
        """
        Test inizializzazione database.
        
        Returns:
            Dict: Risultati test
        """
        result = self.db_init.initialize()
        
        if "errore" in result.lower():
            raise ValueError(result)
            
        return {
            'description': 'Inizializzazione database test',
            'result': result
        }
        
    def _test_population_creation(self) -> Dict:
        """
        Test creazione popolazione.
        
        Returns:
            Dict: Risultati test
        """
        population = self.pop_creator.create_test_population("test_pop_1")
        
        if not population:
            raise ValueError("Errore creazione popolazione")
            
        return {
            'description': 'Creazione popolazione test',
            'population_id': population.population_id,
            'name': population.name,
            'size': population.max_size
        }
        
    def _test_short_evolution(self) -> Dict:
        """
        Test evoluzione breve (5 generazioni).
        
        Returns:
            Dict: Risultati test
        """
        population = self.pop_creator.create_test_population("test_pop_2")
        result = self.tester.run_test(population.population_id, 5)
        
        if "errore" in result.lower():
            raise ValueError(result)
            
        return {
            'description': 'Test evoluzione breve (5 generazioni)',
            'population_id': population.population_id,
            'result': result
        }
        
    def _test_long_evolution(self) -> Dict:
        """
        Test evoluzione lunga (20 generazioni).
        
        Returns:
            Dict: Risultati test
        """
        population = self.pop_creator.create_test_population("test_pop_3")
        result = self.tester.run_test(population.population_id, 20)
        
        if "errore" in result.lower():
            raise ValueError(result)
            
        return {
            'description': 'Test evoluzione lunga (20 generazioni)',
            'population_id': population.population_id,
            'result': result
        }
        
    def _test_stress(self) -> Dict:
        """
        Test stress del sistema.
        
        Returns:
            Dict: Risultati test
        """
        results = []
        
        for i in range(3):
            population = self.pop_creator.create_test_population(f"stress_pop_{i}")
            result = self.tester.run_test(population.population_id, 10)
            
            results.append({
                'population_id': population.population_id,
                'result': result
            })
            
        return {
            'description': 'Test stress (3 popolazioni x 10 generazioni)',
            'results': results
        }
        
    def _generate_test_report(self, results: List[Dict]) -> str:
        """
        Genera report dei test.
        
        Args:
            results: Risultati test
            
        Returns:
            str: Report formattato
        """
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
                
        return "\n".join(lines)
        
    def _save_report(self, report: str) -> None:
        """
        Salva il report su file.
        
        Args:
            report: Report da salvare
        """
        try:
            report_dir = Path(self.test_config['logging']['report_path'])
            report_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evolution_system_test_{timestamp}.txt"
            
            with open(report_dir / filename, 'w') as f:
                f.write(report)
                
            logger.info(f"Report salvato in {filename}")
            
        except Exception as e:
            logger.error(f"Errore salvataggio report: {str(e)}")
