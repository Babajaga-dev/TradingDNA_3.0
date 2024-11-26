# Guida Operativa MarketDNA

## 1. Setup Iniziale

### 1.1 Installazione
```bash
# Clona il repository
git clone git@github.com:tuouser/marketdna.git
cd marketdna

# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
.\venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt
```

### 1.2 Configurazione Base
```bash
# Copia i file di configurazione di esempio
cp config/examples/* config/

# Modifica le configurazioni principali
vim config/database.yaml    # Configurazione database
vim config/exchanges.yaml   # Configurazioni exchange
vim config/training.yaml    # Parametri training
```

## 2. Primi Passi con il CLI

### 2.1 Verifica Setup
```bash
# Verifica installazione
marketdna check-setup

# Testa connessione database
marketdna db:test

# Verifica accesso exchange
marketdna exchange:test
```

### 2.2 Comandi Base
```bash
# Mostra tutti i comandi disponibili
marketdna help

# Informazioni su un comando specifico
marketdna help [comando]

# Visualizza stato sistema
marketdna status
```

## 3. Raccolta Dati Iniziale

### 3.1 Setup Data Collection
```bash
# Configura sorgenti dati
marketdna data:configure

# Inizializza storage
marketdna data:init-storage

# Testa connessioni
marketdna data:test-sources
```

### 3.2 Download Dati Storici
```bash
# Scarica dati storici (esempio ultimo anno)
marketdna data:download --period=1y --pairs=BTC/USDT,ETH/USDT

# Verifica qualità dati
marketdna data:validate

# Visualizza statistiche dati
marketdna data:stats
```

## 4. Training del Sistema

### 4.1 Preparazione Training
```bash
# Prepara dataset
marketdna train:prepare-data

# Configura parametri training
marketdna train:configure

# Verifica setup training
marketdna train:verify-setup
```

### 4.2 Esecuzione Training
```bash
# Esegui training base
marketdna train:run

# Monitora progresso
marketdna train:status

# Valida risultati
marketdna train:validate
```

## 5. Setup Sistema Immunitario

### 5.1 Configurazione Immune
```bash
# Setup sistema immunitario
marketdna immune:setup

# Configura parametri di sicurezza
marketdna immune:configure

# Verifica configurazione
marketdna immune:test
```

### 5.2 Attivazione Protezioni
```bash
# Attiva monitoraggio base
marketdna immune:activate

# Configura alerts
marketdna immune:setup-alerts

# Test sistema protezione
marketdna immune:test-protection
```

## 6. Operatività Live

### 6.1 Setup Ambiente Live
```bash
# Attiva modalità live
marketdna mode:set-live

# Verifica prerequisiti
marketdna live:check

# Setup monitoring
marketdna monitor:setup
```

### 6.2 Gestione Operativa
```bash
# Avvia sistema
marketdna system:start

# Monitora operazioni
marketdna monitor:status

# Visualizza performance
marketdna stats:show
```

## 7. Monitoring e Manutenzione

### 7.1 Monitoraggio
```bash
# Dashboard status
marketdna dashboard

# Controlla logs
marketdna logs:view

# Metriche sistema
marketdna metrics:show
```

### 7.2 Manutenzione
```bash
# Backup configurazioni
marketdna backup:config

# Ottimizza database
marketdna db:optimize

# Aggiorna modelli
marketdna models:update
```

## 8. Analisi Performance

### 8.1 Reports Base
```bash
# Report giornaliero
marketdna report:daily

# Statistiche pattern
marketdna stats:patterns

# Performance trading
marketdna stats:trading
```

### 8.2 Analisi Avanzata
```bash
# Analisi DNA dettagliata
marketdna dna:analyze

# Report sistema immunitario
marketdna immune:report

# Export dati analisi
marketdna export:analysis
```

## 9. Backup e Sicurezza

### 9.1 Backup Routine
```bash
# Backup completo
marketdna backup:full

# Backup configurazioni
marketdna backup:config

# Backup modelli
marketdna backup:models
```

### 9.2 Verifiche Sicurezza
```bash
# Check sicurezza
marketdna security:check

# Verifica integrità
marketdna verify:integrity

# Test sistema
marketdna test:system
```

## Note Importanti

1. **Ordine operazioni**:
   - Seguire l'ordine dei passi per un setup corretto
   - Non saltare fasi di validazione
   - Documentare modifiche alle configurazioni

2. **Best Practices**:
   - Iniziare con piccoli dataset per test
   - Verificare ogni step prima di procedere
   - Mantenere backup regolari
   - Monitorare logs costantemente

3. **Troubleshooting**:
   - Usare `marketdna doctor` per diagnostica
   - Controllare logs per errori
   - Verificare configurazioni con `marketdna config:validate`
   - Testare connessioni con `marketdna test:connections`

4. **Supporto**:
   - Documentazione: `marketdna docs:show`
   - Help command: `marketdna help [comando]`
   - Log dettagliati: `marketdna logs:debug`
   - Status sistema: `marketdna status --verbose`
