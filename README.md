# Flask Web App MPHDM

## Installazione e Configurazione
Per lanciare i sito web in locale seguire i seguenti passaggi.
Assicurati di avere installata l'ultima versione di Python.


Clona il repository ed entra nella cartella progetto
```bash
git clone <repo-url>
```
Installa le dipendenze
```bash
pip install -r requirements.txt
```
Crea manualmente un file vuoto e chiamalo ESATTAMENTE ".env"

Questo file deve essere posizionato nella cartella principale (root) del progetto, esattamente allo stesso livello in cui si trovano i file "main.py" e "requirements.txt"

Apri il file .env appena creato e incollaci dentro le credenziali (MAIL_USERNAME, MAIL_PASSWORD, SECRET_KEY) fornite privatamente

Avvvia l'app eseguendo il file principale
```bash
python main.py
```
Visualizza l'app
```bash
vai alla porta http://127.0.0.1:5000
```

