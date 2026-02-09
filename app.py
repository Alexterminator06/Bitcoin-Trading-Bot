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
    st.header("Simulation Réelle (Objectif 5 Jours / 1H)")
    st.warning("⚠️ Mode Sniper : Analyse sur 120 bougies horaires.")
    
    # On fixe les paramètres pour correspondre à ton objectif réel
    symbol = st.selectbox("Actif", ["BTC-USD", "ETH-USD", "NVDA", "AAPL"], index=0)
    days = 5  # Fixé à 5 jours
    timeframe = "1h" # Fixé à 1h
    
    if st.button("Lancer la Simulation"):
        try:
            with st.spinner("Analyse en cours..."):
                # 1. On télécharge PLUS de jours (ex: 20j) pour que les indicateurs (EMA/ADX) soient prêts
                # même si on ne veut regarder que les 5 derniers jours.
                lookback = days + 10 
                hist = yf.download(symbol, period=f"{lookback}d", interval=timeframe)
                
                if not hist.empty:
                    # 2. Nettoyage STRICT du MultiIndex de Yahoo Finance
                    if isinstance(hist.columns, pd.MultiIndex):
                        hist.columns = hist.columns.get_level_values(0)
                    
                    # On s'assure que les colonnes sont bien nommées pour Backtesting.py
                    hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                    hist = hist.dropna()

                    # 3. Exécution
                    eng = TradingEngine(symbol)
                    stats, bt = eng.run_backtest(hist)
                    
                    # Vérification : si stats['# Trades'] est 0, c'est un problème de données
                    if stats['# Trades'] == 0:
                        st.warning("⚠️ Aucun trade détecté. Essayez d'augmenter la période ou de vérifier l'actif.")
                    
                    # ... (Affichage des metrics et du tableau des trades)
                    
                    # 1. RÉSUMÉ DES PERFORMANCES
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Rendement Net", f"{stats['Return [%]']:.2f}%")
                    c2.metric("Win Rate", f"{stats['Win Rate [%]']:.1f}%")
                    c3.metric("Profit Factor", f"{stats['Profit Factor']:.2f}")
                    c4.metric("Nombre de Trades", int(stats['# Trades']))

                    # 2. GRAPHIQUE D'ÉQUITÉ
                    st.subheader("📈 Évolution du Capital")
                    st.line_chart(stats['_equity_curve']['Equity'])

                    # 3. DÉTAIL DES TRADES (LA NOUVEAUTÉ)
                    st.subheader("📜 Journal des Transactions")
                    trades = stats['_trades']

                    if not trades.empty:
                        df_trades = trades.copy()
                        
                        df_trades['PnL Net ($)'] = df_trades['PnL'].round(2)
                        df_trades['Retour (%)'] = (df_trades['ReturnPct'] * 100).round(2)
                        df_trades['Type'] = df_trades['Size'].apply(lambda x: "🟢 LONG" if x > 0 else "🔴 SHORT")

                        # Sélection et réorganisation des colonnes
                        cols = ['Type', 'EntryPrice', 'ExitPrice', 'PnL Net ($)', 'Retour (%)']
                        df_trades = df_trades[cols]

                        # Fonction de coloration mise à jour pour Pandas 2.x
                        def highlight_pnl(val):
                            try:
                                num = float(val)
                                color = 'green' if num > 0 else 'red'
                                return f'color: {color}'
                            except:
                                return None

                        # Utilisation de .map() au lieu de .applymap()
                        st.dataframe(
                            df_trades.style.map(highlight_pnl, subset=['PnL Net ($)', 'Retour (%)']),
                            use_container_width=True
                        )
                    else:
                        st.info("Aucun trade n'a été ouvert sur cette période avec les paramètres actuels.")

        except Exception as e:
            st.error(f"Erreur d'affichage : {e}")