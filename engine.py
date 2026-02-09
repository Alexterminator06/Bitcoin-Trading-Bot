import pandas as pd
import pandas_ta as ta
from backtesting import Strategy, Backtest
import numpy as np

class BotStrategy(Strategy):
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # 1. Tendance & Momentum
        self.ema_fast = self.I(lambda x: ta.ema(pd.Series(x), length=12).to_numpy(), self.data.Close)
        self.ema_slow = self.I(lambda x: ta.ema(pd.Series(x), length=26).to_numpy(), self.data.Close)
        self.rsi = self.I(lambda x: ta.rsi(pd.Series(x), length=14).to_numpy(), self.data.Close)

        # 2. Filtre de Force (ADX) - Crucial pour ETH et NVDA
        adx_df = ta.adx(high, low, close, length=14)
        self.adx = self.I(lambda: adx_df['ADX_14'].to_numpy())

        # 3. Filtre de Volume Relatif
        self.vol_sma = self.I(lambda x: ta.sma(pd.Series(x), length=20).to_numpy(), self.data.Volume)

    def next(self):
        price = self.data.Close[-1]
        
        # Sécurité : On attend d'avoir assez de données
        if len(self.data) < 30:
            return

        # --- LOGIQUE D'ENTRÉE ---
        if not self.position:
            # Conditions communes : EMA Cross + RSI correct + Volume > Moyenne
            if (self.ema_fast[-1] > self.ema_slow[-1] and 
                self.rsi[-1] > 50 and 
                self.data.Volume[-1] > self.vol_sma[-1]):
                
                # Le filtre ADX : On veut de la force mais pas de l'épuisement
                if 20 < self.adx[-1] < 50:
                    # SL à 2% et TP à 4% (Ratio 1:2)
                    self.buy(size=0.95, sl=price * 0.98, tp=price * 1.04)

            # --- LOGIQUE SHORT ---
            elif (self.ema_fast[-1] < self.ema_slow[-1] and 
                  self.rsi[-1] < 50 and 
                  self.data.Volume[-1] > self.vol_sma[-1]):
                
                if 20 < self.adx[-1] < 50:
                    self.sell(size=0.95, sl=price * 1.02, tp=price * 0.96)

        # --- SORTIE ANTICIPÉE ---
        # On coupe si la tendance s'essouffle avant de toucher le SL ou le TP
        elif self.position.is_long and self.ema_fast[-1] < self.ema_slow[-1]:
            self.position.close()
        elif self.position.is_short and self.ema_fast[-1] > self.ema_slow[-1]:
            self.position.close()

class TradingEngine:
    def __init__(self, symbol):
        self.symbol = symbol

    def run_backtest(self, df):
        df = df.rename(columns={'Open':'Open','High':'High','Low':'Low','Close':'Close','Volume':'Volume'})
        df = df.dropna()
        # Commission ajustée pour H1
        bt = Backtest(df, BotStrategy, cash=1000000, commission=.0005)
        return bt.run(), bt