"""
Database Utilities
----------------
Utilità condivise per il database.
"""

import logging
import sys
from typing import Optional

def get_db_logger(name: str) -> logging.Logger:
    """
    Crea un logger per il database.
    
    Args:
        name: Nome del logger
        
    Returns:
        logging.Logger: Logger configurato
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Handler per console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Handler per file
        file_handler = logging.FileHandler('logs/database.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
    return logger
