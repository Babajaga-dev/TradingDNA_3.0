"""
Database Utilities
----------------
Utilità per la gestione delle operazioni database.
"""

import time
import random
from functools import wraps
from sqlalchemy.exc import OperationalError
from cli.logger.log_manager import get_logger

logger = get_logger('db_utils')

def retry_on_db_lock(func):
    """
    Decoratore che gestisce i retry per le operazioni database in caso di lock.
    
    Args:
        func: Funzione da decorare
        
    Returns:
        wrapper: Funzione decorata con logica di retry
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        instance = args[0]  # Il primo argomento è l'istanza della classe
        max_retries = getattr(instance, 'MAX_RETRIES', 5)
        initial_delay = getattr(instance, 'INITIAL_RETRY_DELAY', 0.1)
        max_delay = getattr(instance, 'MAX_RETRY_DELAY', 2.0)
        
        attempt = 0
        while attempt < max_retries:
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" not in str(e).lower():
                    raise
                    
                attempt += 1
                if attempt == max_retries:
                    logger.error(f"Max tentativi raggiunti per operazione DB: {str(e)}")
                    raise
                
                # Calcola delay con exponential backoff e jitter
                delay = min(initial_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
                logger.warning(f"DB locked, retry {attempt}/{max_retries} dopo {delay:.2f}s")
                time.sleep(delay)
                
    return wrapper
