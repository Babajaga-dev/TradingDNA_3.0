# Guida Iniziale TradingDNA 3.0 🚀

## Setup Ambiente

### 1. Requisiti
- Python 3.8+
- SQLite 3
- Git

### 2. Installazione
```bash
# Clone repository
git clone [repository-url]

# Installa dipendenze
pip install -r requirements.txt

# Setup database
python check_db.py
```

### 3. Configurazione
Il sistema usa file YAML per la configurazione, localizzati in `/config`:

- `system.yaml`: Configurazione generale
- `logging.yaml`: Setup logging
- `portfolio.yaml`: Config portfolio
- `networks.yaml`: Setup connessioni

## Struttura Progetto

```
TradingDNA_3.0/
├── cli/                # Framework CLI ✅
├── data/              # Sistema dati 🚧
├── config/            # Configurazioni ✅
└── logs/              # Log files ✅
```

## Componenti Principali

### 1. CLI Framework ⚡
- Menu interattivo
- Sistema logging
- Progress tracking
- Config management

```bash
# Avvia CLI
python cli/main.py
```

### 2. Data System 📊
- Database SQLite
- CCXT integration
- Download manager
- Data validation

```bash
# Test database
python check_db.py

# Test exchange
python check_exchanges.py
```

## Workflow Sviluppo

1. Setup Iniziale
```bash
# Crea branch feature
git checkout -b feature/nome-feature

# Attiva ambiente
pip install -r requirements.txt
```

2. Sviluppo
```bash
# Test database
python check_db.py

# Avvia CLI
python cli/main.py
```

3. Testing
```bash
# TODO: Implementare test suite
```

## Funzionalità Disponibili

### 1. CLI Menu ✅
- Navigazione interattiva
- Gestione configurazione
- Download manager
- Status sistema

### 2. Database ✅
- Schema base implementato
- Modelli SQLAlchemy
- Migrazioni automatiche
- Query base

### 3. Exchange ✅
- Connettore CCXT
- Rate limiting
- Auto retry
- Error handling

### 4. Data Collection 🚧
- Download batch
- Validazione
- Sincronizzazione
- Processing

## Best Practices

### 1. Codice
- Type hints
- Docstrings
- Error handling
- Logging appropriato

### 2. Git
- Branch per feature
- Commit descrittivi
- Pull request
- Code review

### 3. Database
- Usa migrazioni
- Valida dati
- Gestisci connessioni
- Ottimizza query

## Troubleshooting

### Database
```bash
# Reset database
rm data/tradingdna.db
python check_db.py
```

### Exchange
```bash
# Test connessione
python check_exchanges.py
```

### Logging
- Log in `/logs`
- Configurazione in `config/logging.yaml`
- Livelli: DEBUG, INFO, WARNING, ERROR

## Prossimi Passi

1. Testing Framework 📋
   - Unit test
   - Integration test
   - Coverage report

2. Documentation 📚
   - API docs
   - User guide
   - Developer guide

3. Features 🚀
   - Multi-exchange
   - Analytics
   - Pattern detection
   - Real-time data

## Risorse

- [CCXT Documentation](https://docs.ccxt.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## Note

- In sviluppo attivo
- Breaking changes possibili
- Backup regolare consigliato
- Testare in ambiente dev
