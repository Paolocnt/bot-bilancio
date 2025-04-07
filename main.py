from flask import Flask
from threading import Thread
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import re

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot attivo! Paolo sei connesso."

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CRED_FILE = "glass-turbine-456110-d4-c970beef7a36.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
client = gspread.authorize(creds)

mese_corrente = datetime.now().strftime("%B %Y")
try:
    sheet = client.open_by_key(SHEET_ID).worksheet(mese_corrente)
except:
    sheet = client.open_by_key(SHEET_ID).sheet1

bot = telebot.TeleBot(TELEGRAM_TOKEN)

parole_uscita = ['speso', 'pagato', 'acquistato', 'comprato', 'ordinato', 'uscita', 'prelevato', 'spesa', 'investito', 'scommesso']
parole_entrata = ['guadagnato', 'ricevuto', 'accreditato', 'entrata', 'versato', 'incassato', 'pagato da', 'rimborso']

def parse_text(text):
    today = datetime.now().strftime("%d/%m/%Y")
    text_lower = text.lower()

    if any(word in text_lower for word in parole_uscita):
        tipo = "Uscita"
    elif any(word in text_lower for word in parole_entrata):
        tipo = "Entrata"
    else:
        tipo = "Non definito"

    prezzo_match = re.search(r"(\d+[,.]?\d*)\s?€?", text)
    prezzo = prezzo_match.group(1).replace(",", ".") if prezzo_match else "0"

    parole = text.split()
    oggetto = " ".join([
        w for w in parole
        if w.lower() not in parole_uscita + parole_entrata + ['ho', 'per', 'euro', 'di', 'da', 'mi', 'hanno', 'dato', 'preso']
        and not re.match(r"[\d€]", w)
    ])

    return [today, tipo, oggetto.strip(), prezzo, tipo]

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    try:
        dati = parse_text(message.text)
        sheet.append_row(dati)
        bot.reply_to(message, f"✅ Registrato: {dati}")
    except Exception as e:
        bot.reply_to(message, f"❌ Errore: {e}")

keep_alive()
bot.polling()
