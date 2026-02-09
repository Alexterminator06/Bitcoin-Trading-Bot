import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta

# Chargement des variables du fichier .env
load_dotenv()

class AlpacaBroker:
    def __init__(self):
        # Récupération des clés
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

        if not self.api_key or not self.secret_key:
            raise ValueError("❌ Erreur : Clés API introuvables dans le fichier .env")

        # Connexion à l'API
        try:
            self.api = tradeapi.REST(self.api_key, self.secret_key, self.base_url, api_version='v2')
            account = self.api.get_account()
            print(f"✅ Broker Connecté ! Cash disponible : {account.cash}$")
        except Exception as e:
            print(f"❌ Erreur de connexion Alpaca : {e}")

    def get_candles(self, symbol, timeframe="1Hour", limit=200):
        """Récupère les données historiques pour les calculs"""
        try:
            # Pour les cryptos sur Alpaca
            bars = self.api.get_crypto_bars(symbol, timeframe, limit=limit).df
            if bars.empty:
                return pd.DataFrame()
            
            # Nettoyage
            bars = bars.reset_index()
            # Alpaca renvoie parfois 'close', parfois 'c', on normalise
            bars = bars.rename(columns={
                'close': 'Close', 'high': 'High', 'low': 'Low', 
                'open': 'Open', 'volume': 'Volume'
            })
            return bars
        except Exception as e:
            print(f"⚠️ Erreur récupération bougies : {e}")
            return pd.DataFrame()

    def get_position(self, symbol):
        """Vérifie si on a une position (Retourne la quantité, + ou -)"""
        try:
            # Nettoyage du symbole (BTC/USD -> BTCUSD pour la vérif position)
            clean_symbol = symbol.replace("/", "")
            pos = self.api.get_position(clean_symbol)
            return float(pos.qty)
        except:
            # Si pas de position, l'API renvoie une erreur, donc on retourne 0
            return 0.0

    def submit_order(self, symbol, qty, side):
        """Envoie un ordre (achat ou vente)"""
        try:
            # On ferme d'abord les positions inverses si nécessaire
            current_pos = self.get_position(symbol)
            if (side == 'buy' and current_pos < 0) or (side == 'sell' and current_pos > 0):
                self.api.close_position(symbol.replace("/", ""))
                print("🔄 Position inverse fermée.")

            # Envoi de l'ordre
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            print(f"✅ Ordre {side.upper()} exécuté pour {qty} {symbol}")
            return order
        except Exception as e:
            print(f"❌ Erreur ordre : {e}")
            return None