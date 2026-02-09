import time
import pandas_ta as ta
from datetime import datetime
import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from pathlib import Path
import argparse
import sys
import requests
import pandas as pd
import yfinance as yf # <--- La clé pour les données gratuites

# --- GESTION ARGUMENTS ---
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="BTC/USD", help="Symbole à surveiller")
args = parser.parse_args()
SYMBOL = args.symbol 

# --- CONFIG ---
current_dir = Path(__file__).parent
env_path = current_dir / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Paramètres Stratégie
EMA_FAST = 9
EMA_SLOW = 21
RSI_LEN = 14
ATR_LEN = 14
ATR_MULT_SL = 2.0
TP_MULT = 2.6

# --- FONCTIONS ---
def send_telegram(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data)
            print(f"📩 Notification envoyée !")
        except:
            print(f"❌ Erreur envoi Telegram")

# Connexion Alpaca (juste pour vérifier les clés, on utilise Yahoo pour la data Stocks)
try:
    api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
    print(f"✅ Bot initialisé sur {SYMBOL}")
    send_telegram(f"🤖 **Bot Démarré**\nActif : {SYMBOL}\nSource : {'Yahoo' if '/' not in SYMBOL else 'Alpaca'}")
except Exception as e:
    print(f"❌ Erreur Clés : {e}")
    sys.exit()

def get_data():
    try:
        df = None
        
        # CAS 1 : CRYPTO (Alpaca est parfait)
        if "/" in SYMBOL:
            df = api.get_crypto_bars(SYMBOL, "1Hour", limit=200).df
            df.columns = [c.lower() for c in df.columns]
            rename_map = {'c': 'close', 'h': 'high', 'l': 'low', 'o': 'open', 'v': 'volume'}
            df.rename(columns=rename_map, inplace=True)
            
        # CAS 2 : ACTIONS (Yahoo Finance pour éviter le délai)
        else:
            # On télécharge les 5 derniers jours en H1
            ticker = yf.Ticker(SYMBOL)
            df = ticker.history(period="5d", interval="1h")
            
            if df.empty: return None
            
            # Nettoyage Yahoo
            df.columns = [c.lower() for c in df.columns] # open, high, low, close...
            # Yahoo n'a pas besoin de rename, les noms sont déjà bons (juste en minuscules)

        # Calculs Indicateurs
        df['EMA_Fast'] = ta.ema(df['close'], length=EMA_FAST)
        df['EMA_Slow'] = ta.ema(df['close'], length=EMA_SLOW)
        df['RSI'] = ta.rsi(df['close'], length=RSI_LEN)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=ATR_LEN)
        
        df.dropna(inplace=True)
        return df

    except Exception as e:
        print(f"⚠️ Erreur Data : {e}")
        return None

# --- BOUCLE PRINCIPALE ---
last_signal = "NEUTRE"

print("📡 Recherche de signaux en cours...")

while True:
    try:
        df = get_data()
        
        if df is not None and not df.empty:
            last = df.iloc[-1]
            price = last['close']
            ema_f = last['EMA_Fast']
            ema_s = last['EMA_Slow']
            rsi = last['RSI']
            atr = last['ATR']

            # Affichage console (Pour te rassurer que ça tourne)
            now = datetime.now().strftime('%H:%M')
            print(f"[{now}] {SYMBOL} | Px: {price:.2f} | EMA9: {ema_f:.2f} | RSI: {rsi:.1f} | État: {last_signal}")

            # --- LOGIQUE DE SIGNAL ---
            
            # ACHAT
            if ema_f > ema_s and rsi > 50:
                if last_signal != "BUY":
                    sl = price - (ATR_MULT_SL * atr)
                    tp = price + (TP_MULT * atr)
                    msg = (f"🟢 **ACHAT (LONG) : {SYMBOL}**\n"
                           f"Prix : {price:.2f}\n"
                           f"Stop Loss : {sl:.2f}\n"
                           f"Take Profit : {tp:.2f}")
                    send_telegram(msg)
                    last_signal = "BUY"
            
            # VENTE
            elif ema_f < ema_s and rsi < 50:
                if last_signal != "SELL":
                    sl = price + (ATR_MULT_SL * atr)
                    tp = price - (TP_MULT * atr)
                    msg = (f"🔴 **VENTE (SHORT) : {SYMBOL}**\n"
                           f"Prix : {price:.2f}\n"
                           f"Stop Loss : {sl:.2f}\n"
                           f"Take Profit : {tp:.2f}")
                    send_telegram(msg)
                    last_signal = "SELL"
            
            # NEUTRE
            else:
                if last_signal != "NEUTRE":
                    last_signal = "NEUTRE"
                    # On ne notifie pas le retour au neutre pour ne pas spammer

        else:
            print("💤 Données vides ou marché fermé.")

    except Exception as e:
        print(f"⚠️ Erreur boucle : {e}")

    time.sleep(60)