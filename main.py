from flask import Flask
from threading import Thread
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os

# Avvio server Flask per tenerlo attivo su Render
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot attivo e funzionante!"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

# Variabili d’ambiente da Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CRED_FILE = "/etc/secrets/credentials.json"  # Percorso nel Secret File

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
client = gspread.authorize(creds)

# Ottieni il foglio del mese corrente
mese_corrente = datetime.now().strftime("%B %Y")
sheet = client.open_by_key(SHEET_ID).worksheet(mese_corrente)

# Setup bot Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Liste parole chiave
parole_uscita = ['speso', 'pagato', 'acquistato', 'comprato', 'ordinato', 'uscita', 'prelevato', 'spesa', 'investito', 'scommesso']
parole_entrata = ['guadagnato', 'ricevuto', 'accreditato', 'entrata', 'versato', 'incassato', 'pagato da', 'rimborso']

categorie = {
    "caffè": "Bar",
    "ristorante": "Ristorazione",
    "affitto": "Casa",
    "bolletta": "Utenze",
    "maglia": "Shopping",
    "stipendio": "Lavoro",
    "genitori": "Famiglia",
    "scommesse": "Scommesse",
}

def parse_text(text):
    today = datetime.now().strftime("%d/%m/%Y")
    text_lower = text.lower()

    if any(word in text_lower for word in parole_uscita):
        tipo = "Uscita"
    elif any(word in text_lower for word in parole_entrata):
        tipo = "Entrata"
    else:
        tipo = "Non definito"

    # Prezzo
    prezzo_match = re.search(r"(\d+[,.]?\d*)\s?€?", text)
    prezzo = prezzo_match.group(1).replace(",", ".") if prezzo_match else "0"

    # Oggetto (una parola chiave "pulita")
    parole = text.split()
    oggetto = ""
    for w in parole:
        parola_pulita = w.lower().strip("€.,")
        if (
            parola_pulita not in parole_uscita
            and parola_pulita not in parole_entrata
            and parola_pulita not in ['ho', 'per', 'euro', 'di', 'da', 'mi', 'hanno', 'dato', 'preso', 'una', 'un', 'al', 'il', 'la']
            and not re.match(r"[\d€]", parola_pulita)
        ):
            oggetto = parola_pulita
            break

    # Categoria (associata alla parola chiave, se trovata)
    categoria = categorie.get(oggetto, "Altro")

    return [today, tipo, oggetto.capitalize(), categoria, float(prezzo), tipo]

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        dati = parse_text(message.text)
        sheet.append_row(dati, value_input_option="USER_ENTERED")
        bot.reply_to(message, f"✅ Registrato: {dati}")
    except Exception as e:
        bot.reply_to(message, f"❌ Errore: {e}")

# Avvio bot e server Flask
keep_alive()
bot.polling()

