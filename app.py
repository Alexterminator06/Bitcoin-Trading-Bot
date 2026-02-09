import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from broker import AlpacaBroker
from engine import TradingEngine

st.set_page_config(page_title="Gemini Bot Pro", layout="wide")

# Initialisation Session State pour éviter les crashs au démarrage
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "BTC-USD"
if "bot_active" not in st.session_state:
    st.session_state.bot_active = False

broker = AlpacaBroker()

tab_dashboard, tab_config, tab_simu = st.tabs(["📊 Dashboard", "⚙️ Paramètres", "🧪 Simulation"])

# --- DASHBOARD ---
with tab_dashboard:
    st.header("État du Portefeuille")
    try:
        acc = broker.get_account_info()
        c1, c2, c3 = st.columns(3)
        c1.metric("Equity", f"{acc['equity']}$")
        c2.metric("Cash", f"{acc['cash']}$")
        c3.metric("PnL", f"{acc['pnl']}$")
    except:
        st.warning("En attente de connexion Alpaca (Vérifiez votre .env)")

# --- PARAMÈTRES ---
with tab_config:
    st.header("Configuration Live")
    st.session_state.selected_symbol = st.selectbox("Actif", ["BTC-USD", "ETH-USD", "SOL-USD", "AAPL", "NVDA"])
    if st.button("ALLUMER / ÉTEINDRE LE BOT"):
        st.session_state.bot_active = not st.session_state.bot_active
        st.rerun()
    
    color = "green" if st.session_state.bot_active else "red"
    st.markdown(f"Statut du Bot : :{color}[{'OPÉRATIONNEL' if st.session_state.bot_active else 'À L ARRÊT'}]")

# --- SIMULATION ---
with tab_simu:
    st.header("Simulation Sniper Mode")
    st.info("💡 Conseil : Pour un Win Rate élevé, testez en 1h ou 4h sur 30 jours.")
    
    symbol = st.selectbox("Actif", ["BTC-USD", "ETH-USD", "NVDA"], index=0)
    timeframe = st.selectbox("Unité de temps", ["1h", "4h", "1d"], index=0)
    days = st.slider("Jours de simulation", 10, 60, 45)
    
    if st.button("Lancer la Simulation"):
        try:
            hist = yf.download(symbol, period=f"{days}d", interval=timeframe)
            if not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
                
                eng = TradingEngine(symbol)
                stats, bt = eng.run_backtest(hist)
    
                c1, c2, c3 = st.columns(3)
                c1.metric("Rendement Global", f"{stats['Return [%]']:.2f}%")
                c2.metric("Win Rate", f"{stats['Win Rate [%]']:.1f}%")
                c3.metric("Max Drawdown", f"{stats['Max. Drawdown [%]']:.1f}%")

                # Nouveau : Afficher la répartition Long vs Short
                trades = stats['_trades']
                if not trades.empty:
                    longs = trades[trades['Size'] > 0]
                    shorts = trades[trades['Size'] < 0]
                    st.write(f"📈 Nombre de Longs : {len(longs)} | 📉 Nombre de Shorts : {len(shorts)}")
                
                st.line_chart(stats['_equity_curve']['Equity'])
            else:
                st.error("Données introuvables sur Yahoo Finance.")
        except Exception as e:
            st.error(f"Erreur : {e}")