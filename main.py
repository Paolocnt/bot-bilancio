from flask import Flask
from threading import Thread
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os

# Server Flask per tenere il bot attivo
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot attivo su Render"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

# Variabili d’ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CRED_FILE = "credentials.json"

# Connessione a Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
client = gspread.authorize(creds)

# Seleziona il foglio in base al mese
mese_corrente = datetime.now().strftime("%B %Y")
sheet = client.open_by_key(SHEET_ID).worksheet(mese_corrente)

# Bot Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

parole_uscita = ['speso', 'pagato', 'acquistato', 'comprato', 'ordinato', 'uscita', 'prelevato', 'spesa', 'investito', 'scommesso']
parole_entrata = ['guadagnato', 'ricevuto', 'accreditato', 'entrata', 'versato', 'incassato', 'pagato da', 'rimborso']

categorie = {
    "caffè": "Bar e ristoranti",
    "bar": "Bar e ristoranti",
    "ristorante": "Bar e ristoranti",
    "spesa": "Alimentari",
    "supermercato": "Alimentari",
    "bolletta": "Utenze",
    "affitto": "Casa",
    "abbonamento": "Servizi",
    "maglia": "Shopping",
    "vestiti": "Shopping",
    "stipendio": "Lavoro",
    "genitori": "Famiglia",
    "scommessa": "Scommesse",
}

def parse_text(text):
    today = datetime.now().strftime("%d/%m/%Y")
    text_lower = text.lower()

    # Tipo
    if any(word in text_lower for word in parole_uscita):
        tipo = "Uscita"
    elif any(word in text_lower for word in parole_entrata):
        tipo = "Entrata"
    else:
        tipo = "Non definito"

    # Prezzo
    prezzo_match = re.search(r"(\d+[,.]?\d*)\s?€?", text)
    prezzo = float(prezzo_match.group(1).replace(",", ".")) if prezzo_match else 0.0

    # Oggetto pulito
    parole = text.split()
    oggetto = next(
        (w for w in parole
         if w.lower() not in parole_uscita + parole_entrata + ['ho', 'per', 'euro', 'di', 'da', 'mi', 'hanno', 'dato', 'preso']
         and not re.match(r"[\d€]", w)), 
        "Altro"
    ).strip().lower()

    # Categoria
    categoria = categorie.get(oggetto, "Altro")

    return [today, tipo, oggetto.capitalize(), categoria, prezzo, tipo]

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        dati = parse_text(message.text)
        sheet.append_row(dati, table_range='A2:F2')
        bot.reply_to(message, f"✅ Registrato:\n{dati}")
    except Exception as e:
        bot.reply_to(message, f"❌ Errore: {e}")

# Avvio del bot
keep_alive()
bot.polling()
