import ccxt
import pandas_ta as ta
import pandas as pd
import time
import argparse
import sys
from datetime import datetime

# --- CONFIGURATION ---
parser = argparse.ArgumentParser()
parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Paire (ex: BTC/USDT)")
parser.add_argument("--amount", type=float, default=0.001, help="Quantité fictive à trader")
args = parser.parse_args()

SYMBOL = args.symbol
AMOUNT = args.amount
TIMEFRAME = '1h'

# --- PORTEFEUILLE VIRTUEL ---
# C'est ici que l'argent existe. Si tu relances le bot, ça repart à 1000.
wallet = {
    'USDT': 1000.0, 
    'CRYPTO': 0.0   
}

# --- CONNEXION PUBLIQUE (Lecture Seule) ---
try:
    # On initialise sans clé API => Mode Public
    exchange = ccxt.binance({'enableRateLimit': True})
    print(f"✅ Connecté au flux public Binance ({SYMBOL})")
except Exception as e:
    print(f"❌ Erreur connexion : {e}")
    sys.exit()

# Stratégie ENGINE (EMA 9/21 + RSI 14)
EMA_FAST = 9
EMA_SLOW = 21
RSI_LEN = 14

def get_data():
    try:
        # fetch_ohlcv est public
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        
        # Calculs Indicateurs
        df['EMA_Fast'] = ta.ema(df['close'], length=EMA_FAST)
        df['EMA_Slow'] = ta.ema(df['close'], length=EMA_SLOW)
        df['RSI'] = ta.rsi(df['close'], length=RSI_LEN)
        
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Erreur Data : {e}")
        return None

# --- BOUCLE DE SIMULATION ---
print(f"🤖 Simulation Locale Démarrée | Solde : {wallet['USDT']} USDT")
print("⏳ Analyse du marché en cours...")

while True:
    try:
        df = get_data()
        
        if df is not None:
            last = df.iloc[-1]
            price = last['close']
            ema_f = last['EMA_Fast']
            ema_s = last['EMA_Slow']
            rsi = last['RSI']

            # Calcul de la valeur totale du portefeuille (Cash + Crypto)
            valeur_totale = wallet['USDT'] + (wallet['CRYPTO'] * price)
            
            # État
            in_pos = wallet['CRYPTO'] > 0.000001 # On vérifie si on a de la crypto (avec une petite marge d'erreur)
            
            now = datetime.now().strftime('%H:%M')
            state_icon = "🟢 POS" if in_pos else "⚪ CASH"
            
            # Affichage clean pour le terminal
            print(f"[{now}] {SYMBOL}:{price:.2f}$ | EMA9:{ema_f:.1f} | RSI:{rsi:.1f} | Wallet:{valeur_totale:.2f}$ {state_icon}")

            # --- LOGIQUE ACHAT ---
            if ema_f > ema_s and rsi > 50:
                if not in_pos:
                    cout = price * AMOUNT
                    # On vérifie qu'on a assez d'USDT fictifs
                    if wallet['USDT'] >= cout:
                        print("🚀 SIGNAL D'ACHAT DÉTECTÉ !")
                        wallet['USDT'] -= cout
                        wallet['CRYPTO'] += AMOUNT
                        print(f"✅ ACHAT VALIDÉ : +{AMOUNT} {SYMBOL} à {price}$")
                        print(f"   Nouveau Solde : {wallet['USDT']:.2f} USDT")
                    else:
                        print(f"❌ Fonds insuffisants ({wallet['USDT']:.2f} USDT) pour acheter {cout:.2f}$")

            # --- LOGIQUE VENTE ---
            elif ema_f < ema_s and rsi < 50:
                if in_pos:
                    print("📉 SIGNAL DE VENTE DÉTECTÉ !")
                    gain = price * wallet['CRYPTO']
                    wallet['USDT'] += gain
                    print(f"✅ VENTE VALIDÉE : -{wallet['CRYPTO']} {SYMBOL} à {price}$")
                    wallet['CRYPTO'] = 0 # On remet à zéro
                    print(f"   Nouveau Solde : {wallet['USDT']:.2f} USDT")
                    print(f"💰 PROFIT/PERTE TOTAL : {wallet['USDT'] - 1000:.2f}$")

    except Exception as e:
        print(f"⚠️ Erreur Boucle : {e}")

    # Pause de 60 secondes pour ne pas spammer
    time.sleep(60)