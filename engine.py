import pandas as pd
import pandas_ta as ta
from backtesting import Strategy, Backtest
import numpy as np

class BotStrategy(Strategy):
    # Paramètres équilibrés pour la réactivité
    atr_mult = 2.0
    tp_mult = 2.6

    def init(self):
        # 1. Tendance & Momentum
        self.ema_fast = self.I(lambda x: ta.ema(pd.Series(x), length=9).to_numpy(), self.data.Close)
        self.ema_slow = self.I(lambda x: ta.ema(pd.Series(x), length=21).to_numpy(), self.data.Close)
        self.rsi = self.I(lambda x: ta.rsi(pd.Series(x), length=14).to_numpy(), self.data.Close)
        
        # 2. ATR pour le Trailing Stop
        self.atr = self.I(lambda: ta.atr(pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14).to_numpy())

    def next(self):
        price = self.data.Close[-1]
        atr_val = self.atr[-1]

        # --- GESTION DU TRAILING STOP ---
        # Si on est en position, on remonte le Stop Loss pour protéger le profit
        for trade in self.trades:
            if trade.is_long:
                # Le nouveau stop est le prix actuel moins 2x ATR
                new_sl = max(trade.sl or 0, price - (1.5 * atr_val))
                trade.sl = new_sl
            else:
                # Pour un short, le stop descend
                new_sl = min(trade.sl or float('inf'), price + (1.5 * atr_val))
                trade.sl = new_sl

        # --- LOGIQUE D'ENTRÉE ---
        if not self.position:
            # On simplifie : Croisement EMA + RSI directionnel
            # LONG
            if self.ema_fast[-1] > self.ema_slow[-1] and self.rsi[-1] > 50:
                sl = price - (self.atr_mult * atr_val)
                tp = price + (self.tp_mult * atr_val)
                self.buy(size=0.95, sl=sl, tp=tp)

            # SHORT
            elif self.ema_fast[-1] < self.ema_slow[-1] and self.rsi[-1] < 50:
                sl = price + (self.atr_mult * atr_val)
                tp = price - (self.tp_mult * atr_val)
                self.sell(size=0.95, sl=sl, tp=tp)

class TradingEngine:
    def __init__(self, symbol):
        self.symbol = symbol

    def run_backtest(self, df):
        df = df.rename(columns={'Open':'Open','High':'High','Low':'Low','Close':'Close','Volume':'Volume'})
        df = df.dropna()
        # Commission réaliste
        bt = Backtest(df, BotStrategy, cash=1000000, commission=.0003)
        return bt.run(), bt