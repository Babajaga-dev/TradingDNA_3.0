# Descrizione Dettagliata Componenti MarketDNA

## Core Framework

### Config Module (`core/config/`)

**config_loader.py**
- Classe principale: `ConfigLoader`
- Responsabilità:
  - Caricamento gerarchico delle configurazioni (default → file → env → override)
  - Gestione hot-reload delle configurazioni
  - Caching configurazioni con TTL
  - Merge intelligente di configurazioni multiple
- Funzionalità chiave:
  - `load_config()`: Carica configurazione con fallback automatico
  - `reload_config()`: Ricarica configurazione preservando override
  - `get_config_value()`: Recupera valore con supporto dot notation
  - `override_config()`: Applica override temporanei
- Dipendenze:
  - config_validator.py per validazione
  - default_config.py per valori default
  - PyYAML per parsing YAML

**config_validator.py**
- Classe principale: `ConfigValidator`
- Responsabilità:
  - Validazione strutturale delle configurazioni
  - Type checking avanzato
  - Validazione relazioni tra configurazioni
  - Generazione errori dettagliati
- Schema di validazione per:
  - Configurazioni exchange
  - Parametri training
  - Setup sistema immunitario
  - Configurazioni database
- Validazioni specifiche:
  - Range valori numerici
  - Format stringhe (es. timeframes)
  - Strutture dati complesse
  - Dipendenze circolari

**default_config.py**
- Struttura:
  - Configurazioni base sistema
  - Default per ogni modulo
  - Costanti di sistema
  - Parametri operativi default
- Sezioni principali:
  - `SYSTEM_DEFAULTS`: Configurazioni core
  - `EXCHANGE_DEFAULTS`: Setup base exchange
  - `TRAINING_DEFAULTS`: Parametri training
  - `IMMUNE_DEFAULTS`: Config sistema immunitario
- Include:
  - Timeframes supportati
  - Limiti operativi
  - Valori threshold
  - Pattern di default

### Logging Module (`core/logging/`)

**log_manager.py**
- Classe principale: `LogManager`
- Sistema di logging:
  - Configurazione per modulo
  - Livelli dinamici
  - Rotazione automatica
  - Compressione log storici
- Features:
  - Context logging
  - Structured logging
  - Performance logging
  - Error tracking
- Integrazioni:
  - Sistema di metriche
  - Alert system
  - Monitoring esterno
  - Analytics

**formatters.py**
- Classi formatter:
  - `JsonFormatter`: Output strutturato
  - `DetailedFormatter`: Log dettagliati
  - `MetricFormatter`: Dati performance
  - `AlertFormatter`: Messaggi alert
- Formati supportati:
  - JSON structured
  - Human readable
  - CSV export
  - Metric format
- Personalizzazioni per:
  - Stack traces
  - Context data
  - Performance metrics
  - System state

### Database Module (`core/database/`)

**models/market_data.py**
- Classe principale: `MarketData`
- Schema dati:
  - OHLCV base
  - Technical indicators
  - Market stats
  - Derived metrics
- Ottimizzazioni:
  - Indici per query comuni
  - Partitioning temporale
  - Compression strategy
  - Cache layers
- Relazioni:
  - Pattern riconosciuti
  - Segnali generati
  - Performance metrics
  - System state

**models/patterns.py**
- Classe principale: `Pattern`
- Attributi pattern:
  - Struttura temporale
  - Indicatori chiave
  - Score confidence
  - Meta informazioni
- Sistema scoring:
  - Performance storica
  - Affidabilità
  - Contesto validità
  - Risk rating
- Pattern tracking:
  - Evoluzione temporale
  - Mutazioni rilevate
  - Performance changes
  - Context validity

## DNA Analysis System (`dna/`)

### Sequencer Module (`dna/sequencer/`)

**sequence_analyzer.py**
- Classe principale: `SequenceAnalyzer`
- Analisi sequenziale:
  - Pattern recognition
  - Trend analysis
  - Breakout detection
  - Support/Resistance
- Metriche calcolate:
  - Pattern strength
  - Market phase
  - Volatility metrics
  - Momentum indicators
- Features:
  - Real-time analysis
  - Historical patterns
  - Multi-timeframe
  - Adaptive thresholds

**pattern_extractor.py**
- Classe principale: `PatternExtractor`
- Metodi estrazione:
  - Time series analysis
  - Statistical patterns
  - Geometric shapes
  - Behavioral patterns
- Pattern types:
  - Price patterns
  - Volume patterns
  - Volatility patterns
  - Composite patterns
- Validation:
  - Statistical significance
  - Historical accuracy
  - Context validity
  - Risk assessment

## Training System (`training/`)

### Data Module (`training/data/`)

**collector.py**
- Classe principale: `DataCollector`
- Funzionalità:
  - Multi-exchange support
  - Data synchronization
  - Gap detection
  - Quality checks
- Data types:
  - OHLCV data
  - Order book data
  - Trade data
  - Market events
- Features:
  - Rate limiting
  - Error recovery
  - Data validation
  - Real-time streaming

**preprocessor.py**
- Classe principale: `DataPreprocessor`
- Preprocessing steps:
  - Normalization
  - Feature engineering
  - Missing data handling
  - Outlier detection
- Feature generation:
  - Technical indicators
  - Statistical features
  - Custom indicators
  - Market context
- Optimization:
  - Parallel processing
  - Caching
  - Batch processing
  - Memory optimization

## Immune System (`immune/`)

### Detection Module (`immune/detection/`)

**pattern_detector.py**
- Classe principale: `PatternDetector`
- Detection methods:
  - Statistical analysis
  - Machine learning
  - Rule-based
  - Hybrid approach
- Pattern categories:
  - Market manipulation
  - Abnormal behavior
  - Risk patterns
  - Performance anomalies
- Features:
  - Real-time detection
  - Historical comparison
  - Risk scoring
  - Alert generation

**risk_classifier.py**
- Classe principale: `RiskClassifier`
- Risk categories:
  - Market risk
  - Pattern risk
  - Execution risk
  - System risk
- Classification methods:
  - Statistical models
  - Machine learning
  - Rule-based
  - Ensemble approach
- Features:
  - Risk scoring
  - Trend analysis
  - Context awareness
  - Adaptive thresholds

### Quarantine Module (`immune/quarantine/`)

**isolation_manager.py**
- Classe principale: `IsolationManager`
- Quarantine process:
  - Pattern isolation
  - Risk assessment
  - Validation tests
  - Release criteria
- Monitoring:
  - Pattern behavior
  - Market impact
  - Risk evolution
  - Performance tracking

## Market Data System (`market/`)

### Connectors Module (`market/connectors/`)

**base_connector.py**
- Classe base: `BaseConnector`
- Interface definition:
  - Connection management
  - Data streaming
  - Error handling
  - Rate limiting
- Common features:
  - Authentication
  - Heartbeat
  - Reconnection
  - State management
- Utilities:
  - Request formatting
  - Response parsing
  - Error mapping
  - Data validation