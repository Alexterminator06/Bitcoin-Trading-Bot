import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

load_dotenv()

class AlpacaBroker:
    def __init__(self):
        # Récupération sécurisée des clés
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL")
        
        self.api = tradeapi.REST(api_key, secret_key, base_url, api_version='v2')

    def get_account_info(self):
        acc = self.api.get_account()
        return {
            "cash": round(float(acc.cash), 2),
            "equity": round(float(acc.equity), 2),
            "pnl": round(float(acc.equity) - float(acc.last_equity), 2)
        }

    def get_positions(self):
        return self.api.list_positions()

    def liquidate_all(self):
        self.api.close_all_positions()
        self.api.cancel_all_orders()