import tkinter as tk
from tkinter import messagebox, ttk
import random
import os
import time
from functools import partial
import sqlite3
import hashlib
from datetime import datetime


# Cambia la directory
os.chdir(os.path.realpath(__file__)[:-len(os.path.basename(__file__))])


class GestoreDatabase:
    """Gestisce tutte le operazioni del database SQLite"""
    def __init__(self, nome_db='campo_minato.db'):
        self.connessione = sqlite3.connect(nome_db)
        self.cursore = self.connessione.cursor()
        self.crea_tabelle()
    
    def crea_tabelle(self):
        """Crea le tabelle necessarie se non esistono"""
        # Tabella utenti
        self.cursore.execute('''
            CREATE TABLE IF NOT EXISTS utenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                domanda_sicurezza TEXT NOT NULL,
                risposta_sicurezza TEXT NOT NULL,
                tema_preferito TEXT DEFAULT 'Classic',
                partite_giocate INTEGER DEFAULT 0,
                partite_vinte INTEGER DEFAULT 0,
                miglior_tempo_facile INTEGER DEFAULT 0,
                miglior_tempo_medio INTEGER DEFAULT 0,
                miglior_tempo_difficile INTEGER DEFAULT 0,
                miglior_tempo_personalizzata INTEGER DEFAULT 0,            
                data_registrazione TEXT DEFAULT CURRENT_TIMESTAMP    
            )
        ''')
        
        # Tabella partite (storico completo)
        self.cursore.execute('''
            CREATE TABLE IF NOT EXISTS partite (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_utente INTEGER NOT NULL,
                difficolta TEXT NOT NULL,
                esito TEXT NOT NULL,
                tempo INTEGER NOT NULL,
                mine INTEGER NOT NULL,
                dimensione TEXT NOT NULL,
                data_partita TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_utente) REFERENCES utenti(id)
            )
        ''')
        
        # Tabella record (per la leaderboard)
        self.cursore.execute('''
            CREATE TABLE IF NOT EXISTS record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_utente INTEGER NOT NULL,
                difficolta TEXT NOT NULL,
                tempo INTEGER NOT NULL,
                data_record TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_utente) REFERENCES utenti(id),
                UNIQUE(id_utente, difficolta)
            )
        ''')
        
        self.connessione.commit()
    
    def aggiungi_utente(self, username, password, domanda, risposta):
        """Aggiunge un nuovo utente al database"""
        password_hash = self._hash_password(password)
        risposta_hash = self._hash_password(risposta.lower())  # Case insensitive
        try:
            self.cursore.execute('''
                INSERT INTO utenti (username, password, domanda_sicurezza, risposta_sicurezza) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, domanda, risposta_hash))
            self.connessione.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verifica_risposta_sicurezza(self, username, risposta):
        """Verifica se la risposta di sicurezza è corretta"""
        self.cursore.execute('''
            SELECT risposta_sicurezza FROM utenti 
            WHERE username = ?
        ''', (username,))
        risultato = self.cursore.fetchone()
        if risultato:
            return self._hash_password(risposta.lower()) == risultato[0]
        return False

    def ottieni_domanda_sicurezza(self, username):
        """Ottiene la domanda di sicurezza per un utente"""
        self.cursore.execute('''
            SELECT domanda_sicurezza FROM utenti 
            WHERE username = ?
        ''', (username,))
        risultato = self.cursore.fetchone()
        return risultato[0] if risultato else None

    def verifica_utente(self, username, password):
        """Verifica le credenziali dell'utente"""
        password_hash = self._hash_password(password)
        self.cursore.execute('''
            SELECT id, password FROM utenti 
            WHERE username = ?
        ''', (username,))
        risultato = self.cursore.fetchone()
        return (risultato[0], risultato[1] == password_hash) if risultato else (None, False)
    
    def utente_esiste(self, username):
        """Controlla se un utente esiste"""
        self.cursore.execute('''
            SELECT 1 FROM utenti 
            WHERE username = ?
        ''', (username,))
        return self.cursore.fetchone() is not None
    
    def ottieni_tema_preferito(self, username):
        """Ottiene il tema preferito dell'utente"""
        self.cursore.execute('''
            SELECT tema_preferito FROM utenti 
            WHERE username = ?
        ''', (username,))
        risultato = self.cursore.fetchone()
        return risultato[0] if risultato else 'Classic'
    
    def imposta_tema_preferito(self, username, tema):
        """Imposta il tema preferito per l'utente"""
        self.cursore.execute('''
            UPDATE utenti 
            SET tema_preferito = ? 
            WHERE username = ?
        ''', (tema, username))
        self.connessione.commit()
    
    def aggiorna_statistiche(self, id_utente, username, vinto=False, tempo_impiegato=0, difficolta='facile', mine=10, dimensione='9x9'):
        """Aggiorna le statistiche del giocatore e lo storico partite"""
        # Aggiorna statistiche generali
        self.cursore.execute('''
            UPDATE utenti 
            SET partite_giocate = partite_giocate + 1 
            WHERE id = ?
        ''', (id_utente,))
        
        if vinto:
            self.cursore.execute('''
                UPDATE utenti 
                SET partite_vinte = partite_vinte + 1 
                WHERE id = ?
            ''', (id_utente,))

            if difficolta in ['facile', 'medio', 'difficile']:
                colonna_tempo = f'miglior_tempo_{difficolta}'
                self.cursore.execute(f'''
                    UPDATE utenti 
                    SET {colonna_tempo} = CASE 
                        WHEN {colonna_tempo} = 0 OR ? < {colonna_tempo} THEN ? 
                        ELSE {colonna_tempo} 
                    END 
                    WHERE id = ?
                ''', (tempo_impiegato, tempo_impiegato, id_utente))
                
                self.cursore.execute('''
                    INSERT OR REPLACE INTO record (id_utente, difficolta, tempo)
                    VALUES (?, ?, ?)
                ''', (id_utente, difficolta, tempo_impiegato))

            else:
                self.cursore.execute('''
                UPDATE utenti 
                SET miglior_tempo_personalizzata = CASE 
                    WHEN miglior_tempo_personalizzata = 0 OR ? < miglior_tempo_personalizzata THEN ? 
                    ELSE miglior_tempo_personalizzata 
                END 
                WHERE id = ?
            ''', (tempo_impiegato, tempo_impiegato, id_utente))
        
        # Aggiungi partita allo storico
        esito = 'vittoria' if vinto else 'sconfitta'
        self.cursore.execute('''
            INSERT INTO partite (id_utente, difficolta, esito, tempo, mine, dimensione)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id_utente, difficolta, esito, tempo_impiegato, mine, dimensione))
        
        self.connessione.commit()

    def ottieni_statistiche(self, username):
        """Ottiene le statistiche dell'utente"""
        self.cursore.execute('''
        SELECT partite_giocate, partite_vinte, 
               miglior_tempo_facile, miglior_tempo_medio, miglior_tempo_difficile,
               miglior_tempo_personalizzata 
            FROM utenti 
            WHERE username = ?
        ''', (username,))
        return self.cursore.fetchone()
        
    def ottieni_leaderboard(self, tipo='tempo', difficolta='facile', limite=10):
        """Ottiene la classifica in base al tipo e difficoltà"""
        if tipo == 'tempo':
            query = '''
                SELECT u.username, r.tempo, r.data_record 
                FROM record r
                JOIN utenti u ON r.id_utente = u.id
                WHERE r.difficolta = ?
                ORDER BY r.tempo ASC
                LIMIT ?
            '''
            return self.cursore.execute(query, (difficolta, limite)).fetchall()
        elif tipo == 'vittorie':
            query = '''
                SELECT username, partite_vinte 
                FROM utenti
                ORDER BY partite_vinte DESC
                LIMIT ?
            '''
            return self.cursore.execute(query, (limite,)).fetchall()
        elif tipo == 'partite':
            query = '''
                SELECT username, partite_giocate 
                FROM utenti
                ORDER BY partite_giocate DESC
                LIMIT ?
            '''
            return self.cursore.execute(query, (limite,)).fetchall()
        elif tipo == 'recente':
            query = '''
                SELECT u.username, p.difficolta, p.esito, p.tempo, p.data_partita
                FROM partite p
                JOIN utenti u ON p.id_utente = u.id
                ORDER BY p.data_partita DESC
                LIMIT ?
            '''
            return self.cursore.execute(query, (limite,)).fetchall()
    
    def ottieni_storico_utente(self, username, limite=10):
        """Ottiene lo storico delle partite di un utente"""
        query = '''
            SELECT difficolta, esito, tempo, mine, dimensione, data_partita 
            FROM partite p
            JOIN utenti u ON p.id_utente = u.id
            WHERE u.username = ?
            ORDER BY p.data_partita DESC
            LIMIT ?
        '''
        return self.cursore.execute(query, (username, limite)).fetchall()
    
    def reimposta_password(self, username, nuova_password):
        """Reimposta la password per un utente"""
        password_hash = self._hash_password(nuova_password)
        try:
            self.cursore.execute('''
                UPDATE utenti 
                SET password = ? 
                WHERE username = ?
            ''', (password_hash, username))
            self.connessione.commit()
            return self.cursore.rowcount > 0
        except sqlite3.Error:
            return False

    def _hash_password(self, password):
        """Crea un hash della password per la sicurezza"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def chiudi(self):
        """Chiude la connessione al database"""
        self.connessione.close()

class FinestraLogin:
    """Finestra di login/registrazione"""
    def __init__(self, gestore_db):
        self.db = gestore_db
        self.utente_corrente = None
        
        self.root = tk.Tk()
        self.root.title("Campo Minato - Login")
        self.root.geometry("350x250")
        self.root.resizable(False, False)
        
        # Stile moderno
        self.root.configure(bg='#f0f0f0')
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TButton', font=('Arial', 10), padding=5)
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        
        self.centra_finestra()
        
        self.frame = ttk.Frame(self.root, padding=20)
        self.frame.pack(expand=True, fill=tk.BOTH)
        
        # Widgets
        self.etichetta_titolo = ttk.Label(self.frame, text="Login", font=("Arial", 14, "bold"))
        self.etichetta_utente = ttk.Label(self.frame, text="Username:")
        self.campo_utente = ttk.Entry(self.frame)
        self.etichetta_password = ttk.Label(self.frame, text="Password:")
        self.campo_password = ttk.Entry(self.frame, show="*")
        self.pulsante_login = ttk.Button(self.frame, text="Login", command=self.login)
        self.pulsante_registrati = ttk.Button(self.frame, text="Registrati", command=self.mostra_registrazione)
        self.pulsante_recupero = ttk.Button(self.frame, text="Recupera password", command=self.mostra_recupero_password)
        
        # Posizionamento
        self.etichetta_titolo.grid(row=0, column=0, columnspan=2, pady=(0,15))
        self.etichetta_utente.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.campo_utente.grid(row=1, column=1, sticky="we", pady=5, ipady=3)
        self.etichetta_password.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.campo_password.grid(row=2, column=1, sticky="we", pady=5, ipady=3)
        
        self.pulsante_login.grid(row=3, column=0, padx=5, pady=10, sticky="ew")
        self.pulsante_registrati.grid(row=3, column=1, padx=5, pady=10, sticky="ew")
        self.pulsante_recupero.grid(row=4, column=0, columnspan=2, pady=(10,0), sticky="ew")


        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # Bind per Enter
        self.campo_password.bind("<Return>", lambda e: self.login())
        
        # Campi per registrazione/recupero (nascosti inizialmente)
        self.etichetta_domanda = ttk.Label(self.frame, text="Domanda sicurezza:")
        self.campo_domanda = ttk.Entry(self.frame)
        self.etichetta_risposta = ttk.Label(self.frame, text="Risposta sicurezza:")
        self.campo_risposta = ttk.Entry(self.frame, show="*")
        
        self.root.mainloop()

    def centra_finestra(self):
        self.root.update_idletasks()
        larghezza = self.root.winfo_width()
        altezza = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (larghezza // 2)
        y = (self.root.winfo_screenheight() // 2) - (altezza // 2)
        self.root.geometry(f'+{x}+{y}')
    
    def login(self):
        username = self.campo_utente.get().strip()
        password = self.campo_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Errore", "Inserisci username e password!")
            return
        
        id_utente, credenziali_valide = self.db.verifica_utente(username, password)
        if credenziali_valide:
            self.utente_corrente = username
            self.root.destroy()
        else:
            messagebox.showerror("Errore", "Username o password errati!")
    
    def mostra_registrazione(self):
        """Mostra il form di registrazione"""
        self.etichetta_titolo.config(text="Registrazione")
        self.pulsante_login.config(text="Registrati", command=self.registra)
        self.pulsante_registrati.config(text="Annulla", command=self.mostra_login)
        self.pulsante_recupero.config(state=tk.DISABLED)
        
        self.etichetta_domanda.grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.campo_domanda.grid(row=3, column=1, sticky="we", pady=5, ipady=3)
        self.etichetta_risposta.grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.campo_risposta.grid(row=4, column=1, sticky="we", pady=5, ipady=3)
        
        self.pulsante_login.grid(row=5, column=0, pady=10, sticky="e", padx=5)
        self.pulsante_registrati.grid(row=5, column=1, pady=10, sticky="w", padx=5)
        self.pulsante_recupero.grid(row=6, column=0, columnspan=2, pady=(10,0))
        
        self.campo_password.bind("<Return>", lambda e: self.registra())
        self.root.geometry("350x350")
        self.centra_finestra()
    
    def mostra_login(self):
        """Ripristina la vista login standard"""
        self.etichetta_titolo.config(text="Login")
        self.pulsante_login.config(text="Login", command=self.login)
        self.pulsante_registrati.config(text="Registrati", command=self.mostra_registrazione)
        self.pulsante_recupero.config(state=tk.NORMAL)
        
        # Ripristina i campi password e mostra il campo password
        self.etichetta_password.config(text="Password:")
        self.campo_password.config(show="*")
        self.etichetta_password.grid()
        self.campo_password.grid()
        
        # Nascondi campi aggiuntivi
        self.etichetta_domanda.grid_remove()
        self.campo_domanda.grid_remove()
        self.etichetta_risposta.grid_remove()
        self.campo_risposta.grid_remove()
        
        # Riposiziona pulsanti
        self.pulsante_login.grid(row=3, column=0, padx=5, pady=10, sticky="ew")
        self.pulsante_registrati.grid(row=3, column=1, padx=5, pady=10, sticky="ew")
        self.pulsante_recupero.grid(row=4, column=0, columnspan=2, pady=(10,0), sticky="ew")
        
        self.campo_password.bind("<Return>", lambda e: self.login())
        self.root.geometry("350x250")
        self.centra_finestra()
    
    def mostra_recupero_password(self):
        """Mostra il form per il recupero password"""
        self.etichetta_titolo.config(text="Recupero Password")
        self.pulsante_login.config(text="Continua", command=self.verifica_utente_per_recupero)
        self.pulsante_registrati.config(text="Annulla", command=self.mostra_login)
        self.pulsante_recupero.config(state=tk.DISABLED)
        
        self.etichetta_password.grid_remove()
        self.campo_password.grid_remove()
        
        self.pulsante_login.grid(row=2, column=0, pady=10, sticky="e", padx=5)
        self.pulsante_registrati.grid(row=2, column=1, pady=10, sticky="w", padx=5)
        
        self.root.geometry("350x250")
        self.centra_finestra()

    def verifica_utente_per_recupero(self):
        """Verifica l'esistenza dell'utente e mostra la domanda di sicurezza"""
        username = self.campo_utente.get().strip()
        
        if not username:
            messagebox.showerror("Errore", "Inserisci il tuo username!")
            return
        
        if not self.db.utente_esiste(username):
            messagebox.showerror("Errore", "Username non trovato!")
            return
        
        domanda = self.db.ottieni_domanda_sicurezza(username)
        if not domanda:
            messagebox.showerror("Errore", "Nessuna domanda di sicurezza trovata!")
            return
        
        # Mostra la domanda di sicurezza
        self.etichetta_titolo.config(text="Domanda di Sicurezza")
        self.etichetta_password.config(text=f"Domanda: {domanda}")
        self.campo_password.config(show="")  # Mostra il testo per la risposta
        self.etichetta_password.grid()
        self.campo_password.grid()
        
        self.pulsante_login.config(text="Verifica", command=lambda: self.verifica_risposta_e_reimposta(username))
        
        # Riposiziona pulsanti
        self.pulsante_login.grid(row=3, column=0, pady=10, sticky="e", padx=5)
        self.pulsante_registrati.grid(row=3, column=1, pady=10, sticky="w", padx=5)
        
        self.root.geometry("350x300")
        self.centra_finestra()
    
    def verifica_risposta_e_reimposta(self, username):
        """Verifica la risposta e mostra il form per reimpostare la password"""
        risposta = self.campo_password.get().strip()
        
        if not risposta:
            messagebox.showerror("Errore", "Inserisci la risposta alla domanda!")
            return
        
        if self.db.verifica_risposta_sicurezza(username, risposta):
            self.mostra_finestra_nuova_password(username)
        else:
            messagebox.showerror("Errore", "Risposta errata!")
            self.campo_password.delete(0, tk.END)

    def mostra_finestra_nuova_password(self, username):
        """Mostra la finestra per impostare una nuova password"""
        finestra = tk.Toplevel(self.root)
        finestra.title("Reimposta Password")
        finestra.resizable(False, False)
        finestra.geometry("350x250")
        
        # Stile
        finestra.configure(bg='#f0f0f0')
        frame = ttk.Frame(finestra, padding=20)
        frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(frame, text=f"Nuova password per {username}", 
                 font=("Arial", 12, "bold")).pack(pady=(0,15))
        
        # Campi password
        ttk.Label(frame, text="Nuova password:").pack(pady=5)
        nuova_password = ttk.Entry(frame, show="*")
        nuova_password.pack(fill=tk.X, pady=5, ipady=3)
        
        ttk.Label(frame, text="Conferma password:").pack(pady=5)
        conferma_password = ttk.Entry(frame, show="*")
        conferma_password.pack(fill=tk.X, pady=5, ipady=3)
        
        def applica_cambi():
            pwd = nuova_password.get().strip()
            conf = conferma_password.get().strip()
            
            if not pwd or not conf:
                messagebox.showerror("Errore", "Inserisci e conferma la password!")
                return
            
            if pwd != conf:
                messagebox.showerror("Errore", "Le password non coincidono!")
                return
            
            if len(pwd) < 4:
                messagebox.showerror("Errore", "La password deve avere almeno 4 caratteri!")
                return
            
            if self.db.reimposta_password(username, pwd):
                messagebox.showinfo("Successo", 
                    "Password reimpostata con successo!\n\n" +
                    "Ora puoi accedere con la tua nuova password.")
                finestra.destroy()
                self.mostra_login()
            else:
                messagebox.showerror("Errore", "Errore durante il reset della password!")
        
        ttk.Button(frame, text="Reimposta Password", 
                  command=applica_cambi).pack(pady=15)
        
        # Centra la finestra
        self.centra_finestra_finestra(finestra)
    
    def registra(self):
        username = self.campo_utente.get().strip()
        password = self.campo_password.get().strip()
        domanda = self.campo_domanda.get().strip()
        risposta = self.campo_risposta.get().strip()

        # Validazione
        if not all([username, password, domanda, risposta]):
            messagebox.showerror("Errore", "Compila tutti i campi!")
            return

        if len(username) < 3:
            messagebox.showerror("Errore", "L'username deve avere almeno 3 caratteri!")
            return
        
        if len(password) < 4:
            messagebox.showerror("Errore", "La password deve avere almeno 4 caratteri!")
            return
        
        if len(domanda) < 5:
            messagebox.showerror("Errore", "La domanda deve avere almeno 5 caratteri!")
            return
        
        if len(risposta) < 2:
            messagebox.showerror("Errore", "La risposta deve avere almeno 2 caratteri!")
            return
        
        if self.db.utente_esiste(username):
            messagebox.showerror("Errore", "Username già esistente!")
            return
        
        if self.db.aggiungi_utente(username, password, domanda, risposta):
            messagebox.showinfo("Successo", "Registrazione completata!\nRicorda la tua domanda e risposta di sicurezza.")
            self.mostra_login()
        else:
            messagebox.showerror("Errore", "Errore durante la registrazione!")

    def conferma_recupero(self):
        username = self.campo_utente.get().strip()

        if not username:
            messagebox.showerror("Errore", "Inserisci il tuo username!")
            return
        
        if not self.db.utente_esiste(username):
            messagebox.showerror("Errore", "Username non trovato!")
            return
        
        finestra_recupero = tk.Toplevel(self.root)
        finestra_recupero.title("Reimposta Password")
        finestra_recupero.resizable(False, False)
        
        tk.Label(finestra_recupero, text="Nuova password:").pack(padx=10, pady=5)
        nuova_password = tk.Entry(finestra_recupero, show="*")
        nuova_password.pack(padx=10, pady=5)
        
        tk.Label(finestra_recupero, text="Conferma password:").pack(padx=10, pady=5)
        conferma_password = tk.Entry(finestra_recupero, show="*")
        conferma_password.pack(padx=10, pady=5)
        
        def applica_cambi():
            pwd = nuova_password.get().strip()
            conf = conferma_password.get().strip()
            
            if not pwd or not conf:
                messagebox.showerror("Errore", "Inserisci e conferma la password!")
                return
            
            if pwd != conf:
                messagebox.showerror("Errore", "Le password non coincidono!")
                return
            
            if len(pwd) < 4:
                messagebox.showerror("Errore", "La password deve avere almeno 4 caratteri!")
                return
            
            if self.db.reimposta_password(username, pwd):
                messagebox.showinfo("Successo", "Password reimpostata con successo!")
                finestra_recupero.destroy()
                self.mostra_login()
            else:
                messagebox.showerror("Errore", "Errore durante il reset della password!")
    
        tk.Button(finestra_recupero, text="Reimposta", command=applica_cambi).pack(pady=10)
        self.centra_finestra(finestra_recupero)

class ModelloCampoMinato:
    """Gestisce la logica del gioco"""
    def __init__(self):
        self.righe = 9
        self.colonne = 9
        self.mine = 10
        self.difficolta = 'facile'
        self.reset_gioco()
    
    def reset_gioco(self):
        self.gioco_iniziato = False
        self.gioco_finito = False
        self.primo_click = True
        self.bandierine_piazzate = 0
        self.tempo_inizio = 0
        self.posizioni_mine = set()
        self.mine_adiacenti = {}
        self.celle_scoperte = set()
        self.celle_segnate = set()
    
    def imposta_difficolta(self, difficolta):
        self.difficolta = difficolta
        if difficolta == 'facile':
            self.righe, self.colonne, self.mine = 9, 9, 10
        elif difficolta == 'medio':
            self.righe, self.colonne, self.mine = 16, 16, 40
        elif difficolta == 'difficile':
            self.righe, self.colonne, self.mine = 16, 30, 99
    
    def piazza_mine(self, riga_sicura, colonna_sicura):
        zona_sicura = set()
        
        for r in range(max(0, riga_sicura-1), min(self.righe, riga_sicura+2)):
            for c in range(max(0, colonna_sicura-1), min(self.colonne, colonna_sicura+2)):
                zona_sicura.add((r, c))
        
        posizioni_possibili = [
            (r, c) for r in range(self.righe) 
            for c in range(self.colonne) 
            if (r, c) not in zona_sicura
        ]
        
        self.posizioni_mine = set(random.sample(posizioni_possibili, self.mine))
        self.calcola_mine_adiacenti()
    
    def calcola_mine_adiacenti(self):
        self.mine_adiacenti = {}
        
        for riga in range(self.righe):
            for colonna in range(self.colonne):
                if (riga, colonna) in self.posizioni_mine:
                    self.mine_adiacenti[(riga, colonna)] = -1
                    continue
                
                conteggio = 0
                for r in range(max(0, riga-1), min(self.righe, riga+2)):
                    for c in range(max(0, colonna-1), min(self.colonne, colonna+2)):
                        if (r, c) in self.posizioni_mine:
                            conteggio += 1
                self.mine_adiacenti[(riga, colonna)] = conteggio
    
    def scopri_cella(self, riga, colonna):
        if (riga, colonna) in self.celle_scoperte or (riga, colonna) in self.celle_segnate:
            return None
        
        if self.primo_click:
            self.primo_click = False
            self.gioco_iniziato = True
            self.tempo_inizio = time.time()
            self.piazza_mine(riga, colonna)
        
        self.celle_scoperte.add((riga, colonna))
        
        if (riga, colonna) in self.posizioni_mine:
            self.gioco_finito = True
            return 'mina'
        
        conteggio_mine = self.mine_adiacenti[(riga, colonna)]
        
        if conteggio_mine == 0:
            return 'vuota'
        return conteggio_mine
    
    def scopri_adiacenti(self, riga, colonna):
        celle_da_scoprire = set()
        self.scopri_adiacenti_ricorsivo(riga, colonna, celle_da_scoprire)
        return celle_da_scoprire
    
    def scopri_adiacenti_ricorsivo(self, riga, colonna, insieme_scoperte):
        for r in range(max(0, riga-1), min(self.righe, riga+2)):
            for c in range(max(0, colonna-1), min(self.colonne, colonna+2)):
                if (r, c) != (riga, colonna) and (r, c) not in self.celle_scoperte and (r, c) not in self.celle_segnate:
                    insieme_scoperte.add((r, c))
                    self.celle_scoperte.add((r, c))
                    if self.mine_adiacenti[(r, c)] == 0:
                        self.scopri_adiacenti_ricorsivo(r, c, insieme_scoperte)
    
    def toggle_bandierina(self, riga, colonna):
        if (riga, colonna) in self.celle_scoperte:
            return False
        
        if (riga, colonna) in self.celle_segnate:
            self.celle_segnate.remove((riga, colonna))
            self.bandierine_piazzate -= 1
            return 'rimossa'
        else:
            self.celle_segnate.add((riga, colonna))
            self.bandierine_piazzate += 1
            return 'aggiunta'
    
    def controlla_vittoria(self):
        for riga in range(self.righe):
            for colonna in range(self.colonne):
                if (riga, colonna) not in self.posizioni_mine and (riga, colonna) not in self.celle_scoperte:
                    return False
        self.gioco_finito = True
        return True
    
    def ottieni_tempo_gioco(self):
        if not self.gioco_iniziato:
            return 0
        if self.gioco_finito:
            return self.tempo_fine - self.tempo_inizio
        return time.time() - self.tempo_inizio
    
    def gioco_perso(self):
        self.gioco_finito = True
        self.tempo_fine = time.time()
    
    def gioco_vinto(self):
        self.gioco_finito = True
        self.tempo_fine = time.time()

class VistaCampoMinato:
    """Gestisce l'interfaccia grafica con leaderboard"""
    def __init__(self, root, controller, username):
        self.root = root
        self.controller = controller
        self.username = username
        self.root.title(f"Campo Minato - {username}")
        
        self.temi = {
            "Classic": {
                'sfondo': '#f0f0f0',
                'cella_sfondo': '#e0e0e0',
                'scoperta_sfondo': '#d0d0d0',
                'bandierina_sfondo': '#ffcccc',
                'bandierina_corretta_sfondo': '#99ff99',
                'mina_sfondo': '#ff9999',
                'testo_colore': 'black',
                'colori_numeri': {
                    1: 'blue',
                    2: 'green',
                    3: 'red',
                    4: 'navy',
                    5: 'brown',
                    6: 'teal',
                    7: 'black',
                    8: 'gray'
                },
                'pulsante_sfondo': '#e0e0e0',
                'controlli_sfondo': '#f0f0f0'
            },
            "Dark": {
                'sfondo': '#2d2d2d',
                'cella_sfondo': '#3d3d3d',
                'scoperta_sfondo': '#4d4d4d',
                'bandierina_sfondo': '#5c2a2a',
                'bandierina_corretta_sfondo': '#2a5c2a',
                'mina_sfondo': '#5c2a2a',
                'testo_colore': 'white',
                'colori_numeri': {
                    1: '#4a8fe7',
                    2: '#4ae74a',
                    3: '#e74a4a',
                    4: '#8f4ae7',
                    5: '#e7a84a',
                    6: '#4ae7e7',
                    7: '#ffffff',
                    8: '#a8a8a8'
                },
                'pulsante_sfondo': '#3d3d3d',
                'controlli_sfondo': '#2d2d2d'
            },
            "Fresh Mint": {
                'sfondo': '#F8F4EA',
                'cella_sfondo': '#D4E2D4',
                'scoperta_sfondo': '#A2B29F',
                'bandierina_sfondo': '#F5F0BB',
                'bandierina_corretta_sfondo': '#A2B29F',
                'mina_sfondo': '#FF9B9B',
                'testo_colore': '#3A3A3A',
                'colori_numeri': {
                    1: '#3A7BDA',  
                    2: '#2AA876',  
                    3: '#E74C3C',  
                    4: '#8E44AD',  
                    5: '#A8433E',  
                    6: '#16A085',  
                    7: '#2C3E50',  
                    8: '#7F8C8D'   
                },
                'pulsante_sfondo': '#D4E2D4',
                'controlli_sfondo': '#F8F4EA'
            },
            "Ocean Breeze": {
                'sfondo': '#E1F0DA',
                'cella_sfondo': '#B8D5CD',
                'scoperta_sfondo': '#99A98C',
                'bandierina_sfondo': '#D1E7DD',
                'bandierina_corretta_sfondo': '#99A98C',
                'mina_sfondo': '#FF8787',
                'testo_colore': '#2C3333',
                'colori_numeri': {
                    1: '#2980B9',
                    2: '#27AE60',
                    3: '#E74C3C',
                    4: '#9B59B6',
                    5: '#D35400',
                    6: '#3498DB',
                    7: '#34495E',
                    8: '#7F8C8D'
                },
                'pulsante_sfondo': '#B8D5CD',
                'controlli_sfondo': '#E1F0DA'
            },
            "Vintage Rose": {
                'sfondo': '#F8ECD1',
                'cella_sfondo': '#AC7D88',
                'scoperta_sfondo': '#855F56',
                'bandierina_sfondo': '#DEB6AB',
                'bandierina_corretta_sfondo': '#855F56',
                'mina_sfondo': '#FF8787',
                'testo_colore': '#3A3A3A',
                'colori_numeri': {
                    1: '#6A8CAF',
                    2: '#58D68D',
                    3: '#D4B483',
                    4: '#A67C52',
                    5: '#BD8E83',
                    6: '#7A9CC6',
                    7: '#5D535E',
                    8: '#9E8B8E'
                },
                'pulsante_sfondo': '#AC7D88',
                'controlli_sfondo': '#F8ECD1'
            }
        }
        
        self.tema_corrente = controller.db.ottieni_tema_preferito(username)
        self.pulsanti = {}
        self.setup_interfaccia()
    
    def setup_interfaccia(self):
        self.crea_menu_con_leaderboard()
        self.crea_pannello_controllo()
        self.crea_pannello_statistiche()
        self.crea_griglia()
        self.centra_finestra(self.root)
        self.applica_tema()
    
    def crea_menu_con_leaderboard(self):
        menubar = tk.Menu(self.root)
        
        # Menu Difficoltà
        menu_difficolta = tk.Menu(menubar, tearoff=0)
        menu_difficolta.add_command(label="Facile (9×9, 10 mine)", 
                                 command=lambda: self.controller.imposta_difficolta('facile'))
        menu_difficolta.add_command(label="Medio (16×16, 40 mine)", 
                                 command=lambda: self.controller.imposta_difficolta('medio'))
        menu_difficolta.add_command(label="Difficile (16×30, 99 mine)", 
                                 command=lambda: self.controller.imposta_difficolta('difficile'))
        menu_difficolta.add_command(label="Personalizzato...", 
                                 command=self.controller.difficolta_personalizzata)
        menubar.add_cascade(label="Difficoltà", menu=menu_difficolta)
        
        # Menu Tema
        menu_tema = tk.Menu(menubar, tearoff=0)
        for nome_tema in self.temi.keys():
            menu_tema.add_command(label=nome_tema, 
                                 command=lambda t=nome_tema: self.cambia_tema(t))
        menubar.add_cascade(label="Tema", menu=menu_tema)
        
        # Menu Leaderboard
        menu_leaderboard = tk.Menu(menubar, tearoff=0)
        
        # Sottomenu per la classifica tempi
        menu_tempi = tk.Menu(menu_leaderboard, tearoff=0)
        menu_tempi.add_command(label="Facile", command=lambda: self.mostra_leaderboard('tempo', 'facile'))
        menu_tempi.add_command(label="Intermedio", command=lambda: self.mostra_leaderboard('tempo', 'medio'))
        menu_tempi.add_command(label="Difficile", command=lambda: self.mostra_leaderboard('tempo', 'difficile'))
        menu_leaderboard.add_cascade(label="Migliori tempi", menu=menu_tempi)
        
        # Altre classifiche
        menu_leaderboard.add_command(label="Più vittorie", command=lambda: self.mostra_leaderboard('vittorie'))
        menu_leaderboard.add_command(label="Più partite giocate", command=lambda: self.mostra_leaderboard('partite'))
        menu_leaderboard.add_command(label="Ultime partite", command=lambda: self.mostra_leaderboard('recente'))
        menu_leaderboard.add_command(label="Mio storico", command=self.mostra_storico_personale)
        
        menubar.add_cascade(label="Leaderboard", menu=menu_leaderboard)
        
        # Menu Statistiche
        menu_statistiche = tk.Menu(menubar, tearoff=0)
        menu_statistiche.add_command(label="Le mie statistiche", command=self.controller.mostra_statistiche)
        menubar.add_cascade(label="Statistiche", menu=menu_statistiche)
        
        # Menu Aiuto
        menu_aiuto = tk.Menu(menubar, tearoff=0)
        menu_aiuto.add_command(label="Come giocare", command=self.controller.mostra_istruzioni)
        menu_aiuto.add_command(label="Informazioni", command=self.controller.mostra_info)
        menubar.add_cascade(label="Aiuto", menu=menu_aiuto)
        
        # Menu Account
        menu_account = tk.Menu(menubar, tearoff=0)
        menu_account.add_command(label="Logout", command=self.controller.logout)
        menu_account.add_command(label="Esci", command=self.root.quit)
        menubar.add_cascade(label="Account", menu=menu_account)
        
        self.root.config(menu=menubar)
    
    def crea_pannello_controllo(self):
        self.frame_controllo = tk.Frame(self.root, padx=10, pady=5)
        self.frame_controllo.pack(fill=tk.X)
        
        self.var_mine = tk.StringVar(value='Bandierine: 10')
        self.etichetta_mine = tk.Label(self.frame_controllo, textvariable=self.var_mine, font=('Arial', 12, 'bold'))
        self.etichetta_mine.pack(side=tk.LEFT, padx=10)
        
        self.pulsante_reset = tk.Button(self.frame_controllo, text='😊', font=('Arial', 14), command=self.controller.reset_gioco, bd=2, relief=tk.RAISED)
        self.pulsante_reset.pack(side=tk.LEFT, expand=True)
        
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip_label = tk.Label(self.tooltip, text="Ricomincia il gioco", bg="lightyellow", relief="solid", borderwidth=1)
        self.tooltip_label.pack()

        self.pulsante_reset.bind("<Enter>", self.mostra_tooltip)
        self.pulsante_reset.bind("<Leave>", self.nascondi_tooltip)

        self.var_tempo = tk.StringVar(value='Tempo: 0')
        self.etichetta_tempo = tk.Label(self.frame_controllo, textvariable=self.var_tempo,
                                  font=('Arial', 12, 'bold'))
        self.etichetta_tempo.pack(side=tk.RIGHT, padx=10)
        
        self.separatore = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        self.separatore.pack(fill=tk.X)
    
    def mostra_tooltip(self, event):
        x, y, _, _ = self.pulsante_reset.bbox("insert")
        x += self.pulsante_reset.winfo_rootx() + 25
        y += self.pulsante_reset.winfo_rooty() + 25
        
        self.tooltip.geometry(f"+{x}+{y}")
        self.tooltip.deiconify()

    def nascondi_tooltip(self, event):
        self.tooltip.withdraw()

    def crea_pannello_statistiche(self):
        self.frame_statistiche = tk.Frame(self.root, padx=10, pady=5)
        self.frame_statistiche.pack(fill=tk.X)
        
        self.var_statistiche = tk.StringVar(value=f"Giocatore: {self.username}")
        self.etichetta_statistiche = tk.Label(self.frame_statistiche, textvariable=self.var_statistiche,
                                  font=('Arial', 10))
        self.etichetta_statistiche.pack(side=tk.LEFT)
        
        self.separatore2 = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        self.separatore2.pack(fill=tk.X)
    
    def crea_griglia(self):
        if hasattr(self, 'frame_griglia'):
            self.frame_griglia.destroy()
        
        tema = self.temi[self.tema_corrente]
        self.frame_griglia = tk.Frame(self.root, bg=tema['sfondo'])
        self.frame_griglia.pack(padx=10, pady=10)
        
        self.pulsanti = {}
        modello = self.controller.modello
        tema = self.temi[self.tema_corrente]
        
        for riga in range(modello.righe):
            for colonna in range(modello.colonne):
                pulsante = tk.Button(self.frame_griglia, text='', width=2, height=1,
                              font=('Arial', 9, 'bold'), bd=1, relief=tk.RAISED,
                              bg=tema['cella_sfondo'], fg=tema['testo_colore'])
                pulsante.grid(row=riga, column=colonna)
                
                pulsante.bind('<Button-1>', partial(self.controller.click_sinistro, riga, colonna))
                pulsante.bind('<ButtonRelease-1>', partial(self.rilascio_pulsante, riga, colonna))
                pulsante.bind('<Button-3>', partial(self.controller.click_destro, riga, colonna))
                pulsante.bind('<B1-Motion>', partial(self.trascinamento_pulsante, riga, colonna))
                
                self.pulsanti[(riga, colonna)] = pulsante
    
    def cambia_tema(self, nome_tema):
        self.tema_corrente = nome_tema
        self.controller.db.imposta_tema_preferito(self.username, nome_tema)
        self.applica_tema()
    
    def applica_tema(self):
        tema = self.temi[self.tema_corrente]
        
        self.root.config(bg=tema['sfondo'])
        self.frame_controllo.config(bg=tema['controlli_sfondo'])
        self.frame_statistiche.config(bg=tema['controlli_sfondo'])
        self.etichetta_mine.config(bg=tema['controlli_sfondo'], fg=tema['testo_colore'])
        self.etichetta_tempo.config(bg=tema['controlli_sfondo'], fg=tema['testo_colore'])
        self.etichetta_statistiche.config(bg=tema['controlli_sfondo'], fg=tema['testo_colore'])
        self.pulsante_reset.config(bg=tema['pulsante_sfondo'], fg=tema['testo_colore'],
                            activebackground=tema['pulsante_sfondo'])
        
        stile = ttk.Style()
        stile.configure('Separator.TSeparator', background=tema['testo_colore'])
        
        for (riga, colonna), pulsante in self.pulsanti.items():
            pulsante.config(bg=tema['cella_sfondo'], fg=tema['testo_colore'],
                      activebackground=tema['cella_sfondo'],
                      highlightbackground=tema['pulsante_sfondo'])
        
        modello = self.controller.modello
        for (riga, colonna) in modello.celle_scoperte:
            if (riga, colonna) in modello.posizioni_mine:
                self.aggiorna_pulsante(riga, colonna, 'mina')
            else:
                conteggio_mine = modello.mine_adiacenti[(riga, colonna)]
                self.aggiorna_pulsante(riga, colonna, 'scoperta', conteggio_mine)
        
        for (riga, colonna) in modello.celle_segnate:
            self.aggiorna_pulsante(riga, colonna, 'bandierina')
    
    def aggiorna_pulsante(self, riga, colonna, stato, conteggio_mine=None):
        pulsante = self.pulsanti[(riga, colonna)]
        tema = self.temi[self.tema_corrente]
        
        if stato == 'scoperta':
            pulsante.config(
                state='disabled',
                relief=tk.SUNKEN,
                bg=tema['scoperta_sfondo'],
                text=str(conteggio_mine) if conteggio_mine > 0 else '',
                disabledforeground=tema['colori_numeri'][conteggio_mine] if conteggio_mine > 0 else tema['testo_colore']
            )
        elif stato == 'bandierina':
            pulsante.config(
                text='🚩',
                bg=tema['bandierina_sfondo'],
                fg=tema['testo_colore']
            )
        elif stato == 'rimuovi_bandierina':
            pulsante.config(
                text='',
                bg=tema['cella_sfondo'],
                fg=tema['testo_colore'],
                state='normal'
            )
        elif stato == 'mina':
            pulsante.config(
                text='💣',
                bg=tema['mina_sfondo'],
                fg=tema['testo_colore'],
                state='disabled'
            )
        elif stato == 'bandierina_errata':
            pulsante.config(
                text='🚩',
                bg=tema['bandierina_corretta_sfondo'],
                fg=tema['testo_colore'],
                state='disabled'
            )
    
    def rilascio_pulsante(self, riga, colonna, event):
        modello = self.controller.modello
        if not modello.gioco_finito and (riga, colonna) not in modello.celle_scoperte and (riga, colonna) not in modello.celle_segnate:
            self.pulsanti[(riga, colonna)].config(relief=tk.RAISED)
    
    def trascinamento_pulsante(self, riga, colonna, event):
        modello = self.controller.modello
        if not modello.gioco_finito and (riga, colonna) not in modello.celle_scoperte and (riga, colonna) not in modello.celle_segnate:
            self.pulsanti[(riga, colonna)].config(relief=tk.SUNKEN)
    
    def centra_finestra(self, finestra):
        finestra.update_idletasks()
        larghezza = finestra.winfo_width()
        altezza = finestra.winfo_height()
        x = (finestra.winfo_screenwidth() // 2) - (larghezza // 2)
        y = (finestra.winfo_screenheight() // 2) - (altezza // 2)
        finestra.geometry(f'+{x}+{y}')
    
    def aggiorna_contatore_bandierine(self, bandierine_rimanenti):
        self.var_mine.set(f"Bandierine: {bandierine_rimanenti}")
    
    def aggiorna_timer(self, tempo_trascorso):
        self.var_tempo.set(f"Tempo: {int(tempo_trascorso)}")
    
    def aggiorna_statistiche(self, statistiche, difficolta_corrente):
        testo = f" Giocatore: {self.username} | Partite: {statistiche[0]} | Vittorie: {statistiche[1]}"
        
        if statistiche[0] > 0:
            percentuale = (statistiche[1] / statistiche[0]) * 100
            testo += f" ({percentuale:.1f}%)"
        
        record_testo = []
        if statistiche[2] > 0 and difficolta_corrente == 'facile':
            record_testo.append(f"Facile, {statistiche[2]}s")
        elif statistiche[3] > 0 and difficolta_corrente == 'medio':
            record_testo.append(f"Medio, {statistiche[3]}s")
        elif statistiche[4] > 0 and difficolta_corrente == 'difficile':
            record_testo.append(f"Difficile, {statistiche[4]}s")
        elif statistiche[5] > 0 and difficolta_corrente == 'personalizzata':
            record_testo.append(f"Personalizzato, {statistiche[5]}s")
        
        if record_testo:
            testo += " | Record: " + ", ".join(record_testo)

        self.var_statistiche.set(testo)
    
    def aggiorna_pulsante_reset(self, stato):
        if stato == 'giocando':
            self.pulsante_reset.config(text='😊')
        elif stato == 'perso':
            self.pulsante_reset.config(text='😵')
        elif stato == 'vinto':
            self.pulsante_reset.config(text='😎')
    
    def rivela_tutte_mine(self, posizioni_mine, celle_segnate):
        for (riga, colonna) in posizioni_mine:
            if (riga, colonna) in celle_segnate:
                self.aggiorna_pulsante(riga, colonna, 'bandierina_errata')
            else:
                self.aggiorna_pulsante(riga, colonna, 'mina')
    
    def mostra_messaggio(self, titolo, messaggio):
        messagebox.showinfo(titolo, messaggio)
    
    def mostra_leaderboard(self, tipo, difficolta=None):
        leaderboard = self.controller.db.ottieni_leaderboard(tipo, difficolta, limite=20)
        
        finestra = tk.Toplevel(self.root)
        
        if tipo == 'tempo':
            finestra.title(f"Leaderboard - Migliori tempi ({difficolta.capitalize()})")
            colonne = ['Posizione', 'Username', 'Tempo (sec)', 'Data']
            larghezze = [80, 120, 100, 150]
        elif tipo == 'vittorie':
            finestra.title("Leaderboard - Più vittorie")
            colonne = ['Posizione', 'Username', 'Vittorie']
            larghezze = [80, 200, 100]
        elif tipo == 'partite':
            finestra.title("Leaderboard - Più partite giocate")
            colonne = ['Posizione', 'Username', 'Partite']
            larghezze = [80, 200, 100]
        elif tipo == 'recente':
            finestra.title("Leaderboard - Ultime partite")
            colonne = ['Posizione', 'Username', 'Difficoltà', 'Esito', 'Tempo', 'Data']
            larghezze = [60, 120, 100, 80, 80, 150]
        
        finestra.resizable(False, False)
        
        # Stili
        tema = self.temi[self.tema_corrente]
        stile = ttk.Style()
        stile.configure("Leaderboard.Treeview", 
                    background=tema['controlli_sfondo'],
                    foreground=tema['testo_colore'],
                    fieldbackground=tema['controlli_sfondo'],
                    font=('Arial', 10))
        
        stile.configure("Leaderboard.Treeview.Heading", 
                   background=tema['pulsante_sfondo'],
                   foreground=tema['testo_colore'],
                   font=('Arial', 10, 'bold'))
        
        tk.Label(finestra, text=finestra.title(), font=('Arial', 12, 'bold')).pack(pady=10)
    
        container = ttk.Frame(finestra)
        container.pack(fill='both', expand=True, padx=10, pady=5)

        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill='both', expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=colonne, show='headings', style="Leaderboard.Treeview")

        for col, larghezza in zip(colonne, larghezze):
            tree.heading(col, text=col)
            tree.column(col, width=larghezza, anchor='center')

        for i, record in enumerate(leaderboard, 1):
            if tipo == 'tempo':
                data = datetime.strptime(record[2], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
                tree.insert('', 'end', values=(i, record[0], record[1], data))
            elif tipo == 'vittorie':
                tree.insert('', 'end', values=(i, record[0], record[1]))
            elif tipo == 'partite':
                tree.insert('', 'end', values=(i, record[0], record[1]))
            elif tipo == 'recente':
                esito = "✅ Vittoria" if record[2] == 'vittoria' else "❌ Sconfitta"
                data = datetime.strptime(record[4], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
                tree.insert('', 'end', values=(i, record[0], record[1].capitalize(), esito, record[3], data))
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Button(container, text="Chiudi", command=finestra.destroy).pack(pady=10)

        self.centra_finestra(finestra)

    def mostra_storico_personale(self):
        storico = self.controller.db.ottieni_storico_utente(self.username, limite=10000)
        
        finestra = tk.Toplevel(self.root)
        finestra.title(f"Storico partite - {self.username}")
        finestra.resizable(False, False)
        
        # Stili
        tema = self.temi[self.tema_corrente]
        stile = ttk.Style()
        stile.configure("Storico.Treeview", 
                    background=tema['controlli_sfondo'],
                    foreground=tema['testo_colore'],
                    fieldbackground=tema['controlli_sfondo'],
                    font=('Arial', 10))
        
        stile.configure("Storico.Treeview.Heading", 
                    background=tema['pulsante_sfondo'],
                    foreground=tema['testo_colore'],
                    font=('Arial', 10, 'bold'))
        
        colonne = ['Data', 'Difficoltà', 'Esito', 'Tempo (sec)', 'Mine', 'Dimensione']
        larghezze = [150, 100, 100, 100, 80, 100]
        
        tk.Label(finestra, text=f"Ultime partite di {self.username}", font=('Arial', 12, 'bold')).pack(pady=10)
    
        container = ttk.Frame(finestra)
        container.pack(fill='both', expand=True, padx=10, pady=5)
        
        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill='both', expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=colonne, show='headings', style="Storico.Treeview")

        for col, larghezza in zip(colonne, larghezze):
            tree.heading(col, text=col)
            tree.column(col, width=larghezza, anchor='center')
        
        for partita in storico:
            esito = "✅ Vittoria" if partita[1] == 'vittoria' else "❌ Sconfitta"
            try:
                data_partita = partita[5]
                if isinstance(data_partita, str):
                    data_obj = datetime.strptime(data_partita, '%Y-%m-%d %H:%M:%S')
                    data_formattata = data_obj.strftime('%d/%m/%Y %H:%M')
                else:
                    data_formattata = data_partita.strftime('%d/%m/%Y %H:%M')
            except (ValueError, TypeError, AttributeError):
                data_formattata = str(data_partita)
            
            tree.insert('', 'end', values=(
                data_formattata,
                partita[0].capitalize(),
                esito,
                partita[2],
                partita[3],
                partita[4]
            ))
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Button(container, text="Chiudi", command=finestra.destroy).pack(pady=10)
        
        self.centra_finestra(finestra)
    
    def mostra_finestra_statistiche(self, statistiche):
        finestra_statistiche = tk.Toplevel(self.root)
        finestra_statistiche.title("Statistiche Giocatore")
        finestra_statistiche.resizable(False, False)
        
        self.centra_finestra(finestra_statistiche)
        
        tk.Label(finestra_statistiche, text=f"Statistiche per {self.username}", 
                font=('Arial', 12, 'bold')).pack(pady=10)
        
        tk.Label(finestra_statistiche, text=f"Partite giocate: {statistiche[0]}").pack(pady=5)
        tk.Label(finestra_statistiche, text=f"Partite vinte: {statistiche[1]}").pack(pady=5)
        
        if statistiche[0] > 0:
            percentuale_vittorie = (statistiche[1] / statistiche[0]) * 100
            tk.Label(finestra_statistiche, text=f"Percentuale vittorie: {percentuale_vittorie:.1f}%").pack(pady=5)
        
        tk.Label(finestra_statistiche, text="\nMigliori tempi:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        if statistiche[2] > 0:
            tk.Label(finestra_statistiche, text=f"Facile: {statistiche[2]} secondi").pack(pady=2)
        else:
            tk.Label(finestra_statistiche, text="Facile: Nessun record").pack(pady=2)
        if statistiche[3] > 0:
            tk.Label(finestra_statistiche, text=f"Intermedio: {statistiche[3]} secondi").pack(pady=2)
        else:
            tk.Label(finestra_statistiche, text="Intermedio: Nessun record").pack(pady=2)
        if statistiche[4] > 0:
            tk.Label(finestra_statistiche, text=f"Difficile: {statistiche[4]} secondi").pack(pady=2)
        else:
            tk.Label(finestra_statistiche, text="Difficile: Nessun record").pack(pady=2)
        if statistiche[5] > 0:
            tk.Label(finestra_statistiche, text=f"Personalizzato: {statistiche[5]} secondi").pack(pady=2)
        else:
            tk.Label(finestra_statistiche, text="Personalizzato: Nessun record").pack(pady=2)
        
        tk.Button(finestra_statistiche, text="Chiudi", command=finestra_statistiche.destroy).pack(pady=10)
    
    def mostra_dialogo_difficolta_personalizzata(self, righe, colonne, mine):
        righe_correnti = righe
        colonne_correnti = colonne
        mine_correnti = mine
        
        finestra_personalizzata = tk.Toplevel(self.root)
        finestra_personalizzata.title("Difficoltà Personalizzata")
        finestra_personalizzata.resizable(False, False)
        
        self.centra_finestra(finestra_personalizzata)
        
        def valida(P):
            return P.isdigit() or P == ""
        
        comando_validazione = (finestra_personalizzata.register(valida), '%P')
        
        tk.Label(finestra_personalizzata, text="Righe (max 30):").grid(row=0, column=0, padx=5, pady=5)
        campo_righe = tk.Entry(finestra_personalizzata, validate='key', validatecommand=comando_validazione, width=5)
        campo_righe.grid(row=0, column=1, padx=5, pady=5)
        campo_righe.insert(0, str(righe_correnti))
        
        tk.Label(finestra_personalizzata, text="Colonne (max 40):").grid(row=1, column=0, padx=5, pady=5)
        campo_colonne = tk.Entry(finestra_personalizzata, validate='key', validatecommand=comando_validazione, width=5)
        campo_colonne.grid(row=1, column=1, padx=5, pady=5)
        campo_colonne.insert(0, str(colonne_correnti))
        
        tk.Label(finestra_personalizzata, text="Mine:").grid(row=2, column=0, padx=5, pady=5)
        campo_mine = tk.Entry(finestra_personalizzata, validate='key', validatecommand=comando_validazione, width=5)
        campo_mine.grid(row=2, column=1, padx=5, pady=5)
        campo_mine.insert(0, str(mine_correnti))
        
        risultato = {'righe': righe_correnti, 'colonne': colonne_correnti, 'mine': mine_correnti}
        
        def applica_impostazioni():
            try:
                righe = min(30, int(campo_righe.get() or righe_correnti))
                colonne = min(40, int(campo_colonne.get() or colonne_correnti))
                mine = int(campo_mine.get() or mine_correnti)
                
                if righe < 4 or colonne < 4:
                    messagebox.showerror("Errore", "Dimensione minima: 4×4")
                    return
                
                if mine < 1:
                    messagebox.showerror("Errore", "Deve esserci almeno 1 mina")
                    return
                
                mine_massime = (righe * colonne) - 10
                if mine > mine_massime:
                    messagebox.showerror("Errore", f"Troppe mine! Massimo consentito: {mine_massime}")
                    return
                
                risultato['righe'] = righe
                risultato['colonne'] = colonne
                risultato['mine'] = mine
                finestra_personalizzata.destroy()
            except ValueError:
                messagebox.showerror("Errore", "Valori non validi!")
        
        tk.Button(finestra_personalizzata, text="OK", command=applica_impostazioni).grid(row=3, columnspan=2, pady=10)
        
        finestra_personalizzata.wait_window()
        return risultato


class ControlloreCampoMinato:
    """Gestisce l'interazione tra Modello e Vista"""
    def __init__(self, root, gestore_db, username):
        self.root = root
        self.db = gestore_db
        self.username = username
        self.id_utente, _ = self.db.verifica_utente(username, '')
        self.modello = ModelloCampoMinato()
        self.vista = VistaCampoMinato(root, self, username)
        self.aggiorna_timer()
        self.aggiorna_statistiche()
        self.root.protocol("WM_DELETE_WINDOW", self.logout)
        
    def imposta_difficolta(self, difficolta):
        self.modello.imposta_difficolta(difficolta)
        self.reset_gioco()
        self.aggiorna_statistiche()

    def difficolta_personalizzata(self):
        impostazioni_correnti = {
            'righe': self.modello.righe,
            'colonne': self.modello.colonne,
            'mine': self.modello.mine
        }
        
        nuove_impostazioni = self.vista.mostra_dialogo_difficolta_personalizzata(**impostazioni_correnti)
        
        self.modello.righe = nuove_impostazioni['righe']
        self.modello.colonne = nuove_impostazioni['colonne']
        self.modello.mine = nuove_impostazioni['mine']
        self.modello.difficolta = 'personalizzata'
        self.reset_gioco()
    
    def reset_gioco(self):
        self.modello.reset_gioco()
        self.vista.crea_griglia()
        self.vista.aggiorna_contatore_bandierine(self.modello.mine)
        self.vista.aggiorna_timer(0)
        self.vista.aggiorna_pulsante_reset('giocando')
        self.vista.centra_finestra(self.root)
        self.vista.applica_tema()
    
    def click_sinistro(self, riga, colonna, event):
        if self.modello.gioco_finito:
            return
        
        if (riga, colonna) in self.modello.celle_scoperte or (riga, colonna) in self.modello.celle_segnate:
            return
        
        risultato = self.modello.scopri_cella(riga, colonna)
        
        if risultato is None:
            return
        
        if risultato == 'mina':
            self.modello.gioco_perso()
            self.vista.aggiorna_pulsante_reset('perso')
            self.vista.aggiorna_pulsante(riga, colonna, 'mina')
            self.vista.rivela_tutte_mine(self.modello.posizioni_mine, self.modello.celle_segnate)
            dimensione = f"{self.modello.righe}x{self.modello.colonne}"
            self.db.aggiorna_statistiche(
                self.id_utente,
                self.username,
                vinto=False,
                tempo_impiegato=int(self.modello.ottieni_tempo_gioco()),
                difficolta=self.modello.difficolta,
                mine=self.modello.mine,
                dimensione=dimensione
            )
            self.aggiorna_statistiche()
            self.vista.mostra_messaggio("Game Over", "Hai calpestato una mina!")
            return
        
        if risultato == 'vuota':
            self.vista.aggiorna_pulsante(riga, colonna, 'scoperta', 0)
            celle_da_scoprire = self.modello.scopri_adiacenti(riga, colonna)
            for r, c in celle_da_scoprire:
                conteggio_adiacenti = self.modello.mine_adiacenti[(r, c)]
                self.vista.aggiorna_pulsante(r, c, 'scoperta', conteggio_adiacenti)
        else:
            self.vista.aggiorna_pulsante(riga, colonna, 'scoperta', risultato)
        
        if self.modello.controlla_vittoria():
            self.modello.gioco_vinto()
            self.vista.aggiorna_pulsante_reset('vinto')
            self.vista.rivela_tutte_mine(self.modello.posizioni_mine, self.modello.celle_segnate)
            tempo_impiegato = int(self.modello.ottieni_tempo_gioco())
            dimensione = f"{self.modello.righe}x{self.modello.colonne}"
            self.db.aggiorna_statistiche(
                self.id_utente,
                self.username,
                vinto=True,
                tempo_impiegato=tempo_impiegato,
                difficolta=self.modello.difficolta,
                mine=self.modello.mine,
                dimensione=dimensione
            )
            self.aggiorna_statistiche()
            self.vista.mostra_messaggio("Vittoria!", f"Complimenti! Hai vinto in {tempo_impiegato} secondi!")
    
    def click_destro(self, riga, colonna, event):
        if self.modello.gioco_finito or not self.modello.gioco_iniziato:
            return
        
        if (riga, colonna) in self.modello.celle_scoperte:
            return
        
        risultato = self.modello.toggle_bandierina(riga, colonna)
        
        if risultato == 'aggiunta':
            self.vista.aggiorna_pulsante(riga, colonna, 'bandierina')
        elif risultato == 'rimossa':
            self.vista.aggiorna_pulsante(riga, colonna, 'rimuovi_bandierina')
        
        rimanenti = self.modello.mine - self.modello.bandierine_piazzate
        self.vista.aggiorna_contatore_bandierine(rimanenti)
    
    def aggiorna_timer(self):
        if not self.root.winfo_exists():  
            return
        if self.modello.gioco_iniziato and not self.modello.gioco_finito:
            tempo_trascorso = self.modello.ottieni_tempo_gioco()
            self.vista.aggiorna_timer(tempo_trascorso)
        self.timer_id = self.root.after(1000, self.aggiorna_timer)
    
    def aggiorna_statistiche(self):
        statistiche = self.db.ottieni_statistiche(self.username)
        if statistiche:
            self.vista.aggiorna_statistiche(statistiche, self.modello.difficolta)
    
    def mostra_statistiche(self):
        statistiche = self.db.ottieni_statistiche(self.username)
        if statistiche:
            self.vista.mostra_finestra_statistiche(statistiche)
    
    def mostra_istruzioni(self):
        istruzioni = """
        COME GIOCARE A CAMPO MINATO:
        
        • Clic sinistro: Rivela una cella
        • Clic destro: Posiziona/Rimuovi una bandierina
        • L'obiettivo è rivelare tutte le celle senza mine
        
        I numeri rivelati indicano quante mine ci sono nelle 
        8 celle adiacenti. Usa queste informazioni per 
        dedurre dove sono le mine!
        """
        self.vista.mostra_messaggio("Come giocare", istruzioni)
    
    def mostra_info(self):
        info = "Campo Minato \n\n" \
                    "Creato da Cristian Agostini"
        self.vista.mostra_messaggio("Informazioni", info)
    
    def logout(self):
        if hasattr(self, 'timer_id'):
            self.root.after_cancel(self.timer_id)
        if hasattr(self, 'tooltip') and self.tooltip.winfo_exists():
            self.tooltip.destroy()
        self.root.destroy()
        main()


def main():
    db = GestoreDatabase()
    while True: 
        finestra_login = FinestraLogin(db)
        
        if not finestra_login.utente_corrente: 
            break             
        root = tk.Tk()
        root.style = ttk.Style()
        root.style.theme_use('clam')
        root.minsize(300, 200)
        controllore = ControlloreCampoMinato(root, db, finestra_login.utente_corrente)
        root.mainloop()
    
    db.chiudi()

if __name__ == "__main__":
    main()