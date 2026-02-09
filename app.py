import streamlit as st
import yfinance as yf
import pandas as pd
from engine import TradingEngine
import os
import sys
import subprocess
import time
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Crypto Bot Dashboard", layout="wide")
load_dotenv()

st.title("🤖 Bitcoin Trading Bot - Centre de Contrôle")

# --- GESTION DE L'ÉTAT DU BOT (MÉMOIRE) ---
# On utilise session_state pour se souvenir si le bot tourne ou pas
if 'bot_process' not in st.session_state:
    st.session_state.bot_process = None

# Fonction pour vérifier si le processus est toujours vivant
def is_bot_running():
    if st.session_state.bot_process is None:
        return False
    if st.session_state.bot_process.poll() is not None:
        # Le processus s'est terminé tout seul (erreur ou fin)
        st.session_state.bot_process = None
        return False
    return True

# --- CONNEXION ALPACA (Pour l'affichage) ---
api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
base_url = os.getenv("ALPACA_BASE_URL")

connected = False
account = None
try:
    if api_key:
        api = tradeapi.REST(api_key, secret_key, base_url, api_version='v2')
        account = api.get_account()
        connected = True
except:
    pass

# --- TABS ---
tab_live, tab_simu = st.tabs(["🔴 PILOTAGE LIVE", "⚡ Simulation"])

# ==========================================
# ONGLET 1 : PILOTAGE LIVE (START/STOP)
# ==========================================
with tab_live:
    st.markdown("### 🕹️ Commandes du Bot")
    
    # --- SÉLECTION DE L'ACTIF ---
    # On définit la liste des actifs tradables
    # Note : Alpaca Paper supporte bien les cryptos majeures et les actions US
    choix_symbol = st.selectbox(
        "Sur quel actif le bot doit-il travailler ?",
        ["BTC/USD", "ETH/USD", "LTC/USD", "BCH/USD", "NVDA", "TSLA", "AAPL"],
        index=0, # Par défaut BTC/USD
        disabled=is_bot_running() # On ne peut pas changer si le bot tourne déjà !
    )
    
    st.divider()

    col_state, col_btn_start, col_btn_stop = st.columns([2, 1, 1])
    
    # 1. Indicateur d'état
    with col_state:
        if is_bot_running():
            st.success(f"✅ STATUT : BOT EN LIGNE sur {st.session_state.get('active_symbol', 'Inconnu')}")
            st.caption(f"Process ID : {st.session_state.bot_process.pid}")
        else:
            st.error("🛑 STATUT : BOT ARRÊTÉ (Offline)")
    
    # 2. Bouton Démarrer
    with col_btn_start:
        if st.button("▶️ DÉMARRER LE BOT", disabled=is_bot_running(), use_container_width=True):
            try:
                # C'EST ICI QUE LA MAGIE OPÈRE :
                # On lance : python live_bot.py --symbol CHOIX_UTILISATEUR
                #cmd = [sys.executable, "live_bot.py", "--symbol", choix_symbol]
                cmd = [sys.executable, "signal_bot.py", "--symbol", choix_symbol]                
                process = subprocess.Popen(cmd)
                
                st.session_state.bot_process = process
                st.session_state.active_symbol = choix_symbol # On mémorise l'actif en cours
                st.rerun()
            except Exception as e:
                st.error(f"Erreur au démarrage : {e}")

    # 3. Bouton Arrêter
    with col_btn_stop:
        if st.button("⏹️ ARRÊTER LE BOT", disabled=not is_bot_running(), use_container_width=True):
            try:
                st.session_state.bot_process.terminate()
                st.session_state.bot_process = None
                if 'active_symbol' in st.session_state:
                    del st.session_state.active_symbol
                st.warning("Bot arrêté avec succès.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erreur à l'arrêt : {e}")

    st.divider()

    # --- ZONE DE SURVEILLANCE COMPTE (Reste inchangée) ---
    st.header("📊 Suivi du Compte Alpaca")
    
    if connected:
        c1, c2, c3, c4 = st.columns(4)
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        change = equity - last_equity
        
        c1.metric("Valeur Portefeuille", f"{equity:.2f} $", f"{change:.2f} $")
        c2.metric("Cash", f"{float(account.cash):.2f} $")
        c3.metric("Buying Power", f"{float(account.buying_power):.2f} $")
        c4.metric("Mode", "PAPER TRADING")
        
        st.subheader("Positions Actuelles")
        try:
            positions = api.list_positions()
            if positions:
                pos_data = []
                for p in positions:
                    pos_data.append({
                        "Symbole": p.symbol,
                        "Qty": p.qty,
                        "Prix Entrée": round(float(p.avg_entry_price), 2),
                        "Prix Actuel": round(float(p.current_price), 2),
                        "P/L ($)": round(float(p.unrealized_pl), 2),
                        "% Gain": f"{float(p.unrealized_plpc)*100:.2f}%"
                    })
                st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
            else:
                st.info("Aucune position ouverte actuellement.")
        except Exception as e:
            st.error(f"Erreur lecture positions : {e}")
    else:
        st.warning("⚠️ Alpaca non connecté. Vérifiez le fichier .env")

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