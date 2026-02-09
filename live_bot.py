import time
import pandas_ta as ta
from datetime import datetime
import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame # Import nécessaire pour les actions
from pathlib import Path
import argparse
import sys

# --- GESTION DES ARGUMENTS ---
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="BTC/USD", help="Symbole à trader")
args = parser.parse_args()
SYMBOL = args.symbol 

# --- CHARGEMENT .ENV ---
current_dir = Path(__file__).parent
env_path = current_dir / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# --- CONFIGURATION STRATÉGIE ---
TIMEFRAME_STR = "1Hour" # Pour Crypto
TIMEFRAME_ENUM = TimeFrame.Hour # Pour Actions
QTY = 1 # Attention : 0.01 fonctionne pour BTC, mais pour NVDA il faut souvent au moins 1 action (ou des fractions)

# Paramètres Stratégie
EMA_FAST_LEN = 9
EMA_SLOW_LEN = 21
RSI_LEN = 14
ATR_LEN = 14
ATR_MULT_SL = 2.0
ATR_MULT_TP = 2.6
RSI_THRESHOLD = 50

# --- CONNEXION ---
try:
    api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
    print(f"✅ Bot connecté sur {SYMBOL}. Prêt à sniper.")
except Exception as e:
    print(f"❌ Erreur connexion : {e}")
    sys.exit()

def get_data():
    try:
        bars = None
        
        # --- DÉTECTION AUTOMATIQUE CRYPTO vs ACTION ---
        if "/" in SYMBOL:
            # C'est une Crypto (ex: BTC/USD)
            bars = api.get_crypto_bars(SYMBOL, TIMEFRAME_STR, limit=200).df
        else:
            # C'est une Action (ex: NVDA, TSLA)
            # Les actions ont besoin de l'objet TimeFrame
            bars = api.get_bars(SYMBOL, TIMEFRAME_ENUM, limit=200).df

        # Vérification vide
        if bars is None or bars.empty:
            return None

        # Nettoyage des colonnes (Alpaca renvoie parfois des majuscules ou minuscules)
        bars.columns = [c.lower() for c in bars.columns]
        
        # Standardisation (rename si nécessaire)
        # Si on trade des actions, Alpaca renvoie parfois 'c', 'h', 'l', 'o'
        rename_map = {'c': 'close', 'h': 'high', 'l': 'low', 'o': 'open', 'v': 'volume'}
        bars.rename(columns=rename_map, inplace=True)

        # Calculs Indicateurs
        bars['EMA_Fast'] = ta.ema(bars['close'], length=EMA_FAST_LEN)
        bars['EMA_Slow'] = ta.ema(bars['close'], length=EMA_SLOW_LEN)
        bars['RSI'] = ta.rsi(bars['close'], length=RSI_LEN)
        bars['ATR'] = ta.atr(bars['high'], bars['low'], bars['close'], length=ATR_LEN)
        
        # Supprime les lignes vides (NaN) dues aux calculs
        bars.dropna(inplace=True)
        
        return bars
    except Exception as e:
        print(f"⚠️ Erreur récupération données : {e}")
        return None

def check_position():
    try:
        positions = api.list_positions()
        # Nettoyage du symbole pour comparaison (BTC/USD -> BTCUSD)
        symbol_clean = SYMBOL.replace("/", "")
        
        for p in positions:
            if p.symbol == symbol_clean:
                return float(p.qty)
        return 0
    except:
        return 0

def close_all():
    try:
        # On ne ferme que la position du symbole en cours pour ne pas tout vendre
        symbol_clean = SYMBOL.replace("/", "")
        try:
            api.close_position(symbol_clean)
            print(f"🛑 Position fermée sur {SYMBOL}.")
        except:
            pass # Pas de position à fermer
    except Exception as e:
        print(f"Erreur fermeture : {e}")

# --- BOUCLE PRINCIPALE ---
print("🤖 Lancement de la boucle... (CTRL+C pour arrêter)")

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

            print(f"[{datetime.now().strftime('%H:%M')}] {SYMBOL} | Prix: {price:.2f} | EMA9: {ema_f:.2f} | RSI: {rsi:.1f}")

            current_qty = check_position()

            # --- LOGIQUE TRADING ---
            
            # ACHAT
            if ema_f > ema_s and rsi > RSI_THRESHOLD:
                if current_qty <= 0:
                    print("🚀 SIGNAL LONG !")
                    if current_qty < 0: close_all()
                    
                    sl_price = price - (ATR_MULT_SL * atr)
                    tp_price = price + (ATR_MULT_TP * atr)
                    
                    try:
                        api.submit_order(
                            symbol=SYMBOL, qty=QTY, side='buy', type='market', time_in_force='gtc',
                            order_class='bracket',
                            stop_loss={'stop_price': round(sl_price, 2)},
                            take_profit={'limit_price': round(tp_price, 2)}
                        )
                        print(f"✅ Ordre LONG envoyé (SL: {sl_price:.2f})")
                    except Exception as e:
                        print(f"❌ Erreur ordre : {e}")

            # VENTE
            elif ema_f < ema_s and rsi < RSI_THRESHOLD:
                if current_qty >= 0:
                    print("📉 SIGNAL SHORT !")
                    if current_qty > 0: close_all()
                    
                    sl_price = price + (ATR_MULT_SL * atr)
                    tp_price = price - (ATR_MULT_TP * atr)
                    
                    try:
                        api.submit_order(
                            symbol=SYMBOL, qty=QTY, side='sell', type='market', time_in_force='gtc',
                            order_class='bracket',
                            stop_loss={'stop_price': round(sl_price, 2)},
                            take_profit={'limit_price': round(tp_price, 2)}
                        )
                        print(f"✅ Ordre SHORT envoyé (SL: {sl_price:.2f})")
                    except Exception as e:
                        print(f"❌ Erreur ordre : {e}")
            else:
                print("⏳ Zone neutre.")

        else:
            print("💤 Pas de données (Marché fermé ou erreur API)...")

    except Exception as e:
        print(f"⚠️ Erreur boucle : {e}")

    time.sleep(60)