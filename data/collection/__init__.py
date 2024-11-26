"""
TradingDNA Data System - Collection Module
---------------------------------------
Sistema di raccolta e processing dati di mercato.
"""

from typing import Dict, Any, Optional, List

from .downloader import (
    DownloadConfig,
    DownloadStats,
    DataDownloader
)

from .validator import (
    ValidationRule,
    ValidationResult,
    ValidationStats,
    ValidationSeverity,
    DataValidator
)

from .synchronizer import (
    TimeframeConfig,
    SyncStats,
    DataSynchronizer
)

from .processor import (
    ProcessingStage,
    ProcessingStep,
    ProcessingStats,
    DataProcessor
)

__all__ = [
    # Downloader
    'DownloadConfig',
    'DownloadStats',
    'DataDownloader',
    
    # Validator
    'ValidationRule',
    'ValidationResult',
    'ValidationStats',
    'ValidationSeverity',
    'DataValidator',
    
    # Synchronizer
    'TimeframeConfig',
    'SyncStats',
    'DataSynchronizer',
    
    # Processor
    'ProcessingStage',
    'ProcessingStep',
    'ProcessingStats',
    'DataProcessor',
    
    # Factory functions
    'create_downloader',
    'create_validator',
    'create_synchronizer',
    'create_processor'
]

def create_downloader(
    config: Dict[str, Any]
) -> DataDownloader:
    """
    Crea un nuovo downloader.
    
    Args:
        config: Configurazione downloader
        
    Returns:
        Istanza configurata di DataDownloader
    """
    download_config = DownloadConfig(**config)
    return DataDownloader(download_config)

def create_validator(
    rules: Optional[List[ValidationRule]] = None
) -> DataValidator:
    """
    Crea un nuovo validator.
    
    Args:
        rules: Regole di validazione
        
    Returns:
        Istanza configurata di DataValidator
    """
    validator = DataValidator()
    if rules:
        validator.rules = rules
    return validator

def create_synchronizer(
    timeframes: Optional[Dict[str, TimeframeConfig]] = None
) -> DataSynchronizer:
    """
    Crea un nuovo synchronizer.
    
    Args:
        timeframes: Configurazioni timeframe
        
    Returns:
        Istanza configurata di DataSynchronizer
    """
    synchronizer = DataSynchronizer()
    if timeframes:
        synchronizer.timeframes = timeframes
    return synchronizer

def create_processor(
    steps: Optional[List[ProcessingStep]] = None
) -> DataProcessor:
    """
    Crea un nuovo processor.
    
    Args:
        steps: Step di processing
        
    Returns:
        Istanza configurata di DataProcessor
    """
    processor = DataProcessor()
    if steps:
        processor.steps = steps
    return processor

# Pipeline di collection dati
class DataCollectionPipeline:
    """Pipeline completa di collection dati."""
    
    def __init__(
        self,
        config: Dict[str, Any]
    ):
        """
        Inizializza la pipeline.
        
        Args:
            config: Configurazione pipeline
        """
        self.config = config
        
        # Crea componenti
        self.downloader = create_downloader(
            config.get('downloader', {})
        )
        self.validator = create_validator(
            config.get('validator_rules')
        )
        self.synchronizer = create_synchronizer(
            config.get('timeframes')
        )
        self.processor = create_processor(
            config.get('processing_steps')
        )
        
    async def run(self) -> Dict[str, Any]:
        """
        Esegue pipeline completa.
        
        Returns:
            Statistiche esecuzione
        """
        # Download dati
        download_stats = await self.downloader.download_data()
        
        # Validazione
        validation_stats = self.validator.validate_data(
            self.downloader.data
        )
        
        # Sincronizzazione
        sync_stats = self.synchronizer.sync_timeframes(
            self.downloader.data
        )
        
        # Processing
        processing_stats = self.processor.process_data(
            self.synchronizer.data
        )
        
        return {
            'download': download_stats,
            'validation': validation_stats,
            'sync': sync_stats,
            'processing': processing_stats
        }