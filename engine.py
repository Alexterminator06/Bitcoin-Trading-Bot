import pandas as pd
import pandas_ta as ta
from backtesting import Strategy, Backtest
import numpy as np

class BotStrategy(Strategy):
    st_period = 10
    st_multiplier = 3.0
    atr_period = 14

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # 1. SuperTrend
        st_data = ta.supertrend(high, low, close, length=self.st_period, multiplier=self.st_multiplier)
        self.st_dir = self.I(lambda: st_data['SUPERTd_10_3.0'].to_numpy())
        
        # 2. Stoch RSI
        stoch_rsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
        self.stoch_k = self.I(lambda: stoch_rsi['STOCHRSIk_14_14_3_3'].to_numpy())
        
        # 3. ATR (Indicateur de volatilité)
        self.atr = self.I(lambda: ta.atr(high, low, close, length=self.atr_period).to_numpy())
        
        # 4. EMA 50
        self.ema_50 = self.I(lambda x: ta.ema(pd.Series(x), length=50).to_numpy(), self.data.Close)

    def next(self):
        price = self.data.Close[-1]
        atr_val = self.atr[-1]
        
        # --- LOGIQUE LONG ---
        if self.st_dir[-1] == 1 and price > self.ema_50[-1]:
            if not self.position.is_long and self.stoch_k[-1] < 20:
                self.position.close()
                # On place le Stop Loss à 2 fois l'ATR (volatilité réelle)
                # On place le Take Profit à 4 fois l'ATR (Ratio 1:2)
                self.buy(size=0.95, sl=price - (2 * atr_val), tp=price + (4 * atr_val))

        # --- LOGIQUE SHORT ---
        elif self.st_dir[-1] == -1 and price < self.ema_50[-1]:
            if not self.position.is_short and self.stoch_k[-1] > 80:
                self.position.close()
                self.sell(size=0.95, sl=price + (2 * atr_val), tp=price - (4 * atr_val))

        # --- SORTIE DE SÉCURITÉ (Changement de tendance) ---
        if (self.position.is_long and self.st_dir[-1] == -1) or \
           (self.position.is_short and self.st_dir[-1] == 1):
            self.position.close()

class TradingEngine:
    def __init__(self, symbol):
        self.symbol = symbol

    def run_backtest(self, df):
        df = df.rename(columns={'Open':'Open','High':'High','Low':'Low','Close':'Close','Volume':'Volume'})
        df = df.dropna()
        bt = Backtest(df, BotStrategy, cash=1000000, commission=.0004)
        return bt.run(), bt