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

# --- PORTEFEUILLE VIRTUEL (C'est ici que l'argent existe) ---
wallet = {
    'USDT': 1000.0,  # On commence avec 1000$ fictifs
    'CRYPTO': 0.0    # 0 BTC
}

# --- CONNEXION PUBLIQUE (Pas de clés !) ---
try:
    # On initialise sans API Key ni Secret => Mode Lecture Seule Public
    exchange = ccxt.binance({'enableRateLimit': True})
    print(f"✅ Connecté au flux public Binance ({SYMBOL})")
except Exception as e:
    print(f"❌ Erreur connexion : {e}")
    sys.exit()

# Stratégie ENGINE
EMA_FAST = 9
EMA_SLOW = 21
RSI_LEN = 14

def get_data():
    try:
        # fetch_ohlcv est public, pas besoin de compte
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        
        # Indicateurs
        df['EMA_Fast'] = ta.ema(df['close'], length=EMA_FAST)
        df['EMA_Slow'] = ta.ema(df['close'], length=EMA_SLOW)
        df['RSI'] = ta.rsi(df['close'], length=RSI_LEN)
        
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Erreur Data : {e}")
        return None

# --- BOUCLE DE TRADING ---
print(f"🤖 Bot Simulation Démarré | Solde Initial : {wallet['USDT']} USDT")

while True:
    try:
        df = get_data()
        
        if df is not None:
            last = df.iloc[-1]
            price = last['close']
            ema_f = last['EMA_Fast']
            ema_s = last['EMA_Slow']
            rsi = last['RSI']

            # Calcul de la valeur totale (Cash + Crypto convertie au prix actuel)
            valeur_totale = wallet['USDT'] + (wallet['CRYPTO'] * price)
            
            in_pos = wallet['CRYPTO'] > 0
            state = "🟢 EN POS" if in_pos else "⚪ CASH"
            now = datetime.now().strftime('%H:%M')

            print(f"[{now}] {SYMBOL}:{price:.2f}$ | RSI:{rsi:.1f} | Wallet:{valeur_totale:.2f}$ ({state})")

            # --- LOGIQUE D'ACHAT (SIMULÉE) ---
            if ema_f > ema_s and rsi > 50:
                if not in_pos:
                    cout = price * AMOUNT
                    if wallet['USDT'] >= cout:
                        print("🚀 SIGNAL D'ACHAT !")
                        wallet['USDT'] -= cout
                        wallet['CRYPTO'] += AMOUNT
                        print(f"✅ Acheté {AMOUNT} {SYMBOL} à {price}$")
                    else:
                        print("❌ Fonds insuffisants (Virtuels).")

            # --- LOGIQUE DE VENTE (SIMULÉE) ---
            elif ema_f < ema_s and rsi < 50:
                if in_pos:
                    print("📉 SIGNAL DE VENTE !")
                    gain = price * wallet['CRYPTO']
                    wallet['USDT'] += gain
                    wallet['CRYPTO'] = 0
                    print(f"✅ Tout vendu à {price}$")
                    print(f"💰 Nouveau Solde : {wallet['USDT']:.2f} USDT")

    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    time.sleep(60)