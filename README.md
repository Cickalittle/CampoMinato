# Campo Minato

Un classico gioco del Campo Minato implementato in Python con interfaccia grafica Tkinter, sistema di login e statistiche dei giocatori.

## Indice

- [Funzionalità](#funzionalità)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Come giocare](#come-giocare)
- [Database](#database)
- [Personalizzazione](#personalizzazione)
- [Autore](#autore)
- [Licenza](#licenza)

## Funzionalità

✅ **Sistema di autenticazione** con:
- Registrazione utente con domanda di sicurezza
- Login/Logout sicuro
- Recupero password tramite domanda personale

🎮 **Modalità di gioco**:
- Facile (9×9, 10 mine)
- Medio (16×16, 40 mine)
- Difficile (16×30, 99 mine)
- Personalizzato (dimensione e mine configurabili)

📊 **Statistiche avanzate**:
- Storico completo di tutte le partite
- Migliori tempi per ogni difficoltà
- Classifica globale vittorie
- Statistiche personali con percentuali
- Leaderboard per tempi e vittorie

🎨 **Personalizzazione**:
- 5 temi grafici selezionabili
- Interfaccia responsive e moderna
- Animazioni e feedback visivi

## Requisiti

- Python 3.6 o superiore
- Librerie incluse in Python:
  - `tkinter` per l'interfaccia grafica
  - `sqlite3` per il database
  - `hashlib` per la sicurezza
  - `random` e `time` per la logica di gioco

## Installazione

1. Scarica il file `gioco.py`
2. Assicurati di avere Python 3 installato
3. Esegui il gioco con:

```bash
python gioco.py
```

Il database (`campo_minato.db`) verrà creato automaticamente al primo avvio.

## Come giocare

1. **Registrati** con username e password
2. **Accedi** con le tue credenziali
3. Scegli la difficoltà dal menu
4. **Controlli**:
   - Clic sinistro: scopri una cella
   - Clic destro: posiziona/rimuovi bandierina
5. **Obiettivo**: scopri tutte le celle senza mine!

💡 **Suggerimento**: I numeri rivelano quante mine ci sono nelle 8 celle adiacenti.

## Database

Il gioco utilizza un database SQLite che contiene:

| Tabella          | Contenuto |
|---------------|-----------|
| `utenti`       | Credenziali, statistiche e preferenze |
| `partite`     | Storico completo di tutte le partite |
| `record`      | Migliori tempi per le classifiche |

I dati sono protetti con hash SHA-256 per le password e risposte di sicurezza.

## Personalizzazione

Puoi modificare:

- **Temi grafici**: Modifica il dizionario `temi` nella classe `VistaCampoMinato`
- **Dimensioni massime**: Impostazioni nella funzione `mostra_dialogo_difficolta_personalizzata`
- **Livelli difficoltà**: Modifica i parametri in `ModelloCampoMinato.imposta_difficolta()`

## Autore

Creato da **Cristian Agostini**

## Licenza

Questo progetto è rilasciato sotto licenza MIT. Per i dettagli completi, vedi [choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/). 
